"""
Gemma 4 Analyzer Module for TeachCheck AI
Performs visual and cross-modal reasoning using Gemma 4 (gemma-4-26b-a4b-it)
via the Google Gen AI SDK (google-genai) and Gemini Files API.
"""

import os
import json
import re
from google import genai
from google.genai import types
from google.genai.errors import APIError

GEMMA_MODEL_ID = "gemma-4-26b-a4b-it"

VALID_CATEGORIES = [
    "Confirmed inconsistency",
    "Potential inconsistency",
    "No inconsistency observed",
    "Insufficient evidence"
]


class GemmaAPIError(Exception):
    """Custom exception for Gemma 4 API issues."""
    pass


class GemmaParseError(Exception):
    """Custom exception for response parsing issues."""
    pass


def get_gemini_client(api_key: str = None) -> genai.Client:
    """
    Instantiates the Google Gen AI client using the provided key
    or the GEMINI_API_KEY environment variable.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or not key.strip() or key == "your_gemini_api_key_here":
        raise GemmaAPIError(
            "GEMINI_API_KEY is missing or invalid. "
            "Please provide a valid API key in the sidebar or set it in your .env file."
        )
    return genai.Client(api_key=key.strip())


def clean_json_text(text: str) -> str:
    """
    Strips markdown code blocks and whitespace from JSON response.
    """
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_and_validate_gemma_response(raw_text: str) -> dict:
    """
    Parses and validates the JSON output returned by Gemma 4.
    If parsing fails, returns a graceful structured fallback with raw_text preserved.
    """
    cleaned = clean_json_text(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as err:
        # Attempt regex extraction of first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                return {
                    "is_parsed": False,
                    "parse_error": str(err),
                    "raw_response": raw_text,
                    "overall_summary": "Raw response could not be parsed as strict JSON. See raw output below.",
                    "findings": []
                }
        else:
            return {
                "is_parsed": False,
                "parse_error": str(err),
                "raw_response": raw_text,
                "overall_summary": "Raw response could not be parsed as strict JSON. See raw output below.",
                "findings": []
            }

    # Normalize structure
    overall_summary = data.get("overall_summary", "Analysis completed.")
    findings_raw = data.get("findings", [])
    if not isinstance(findings_raw, list):
        findings_raw = []

    normalized_findings = []
    for idx, item in enumerate(findings_raw):
        if not isinstance(item, dict):
            continue

        raw_cat = item.get("category", "").strip()
        matched_cat = "Potential inconsistency"
        for valid in VALID_CATEGORIES:
            if valid.lower() in raw_cat.lower() or raw_cat.lower() in valid.lower():
                matched_cat = valid
                break

        normalized_findings.append({
            "finding_id": idx + 1,
            "frame_index": item.get("frame_index", idx + 1),
            "timestamp": item.get("timestamp", f"Frame {idx+1}"),
            "spoken_statement": item.get("spoken_statement", "N/A"),
            "visible_evidence": item.get("visible_evidence", "N/A"),
            "explanation": item.get("explanation", "No detailed explanation provided."),
            "category": matched_cat,
            "suggested_correction": item.get("suggested_correction", "None")
        })

    return {
        "is_parsed": True,
        "parse_error": None,
        "raw_response": raw_text,
        "overall_summary": overall_summary,
        "findings": normalized_findings
    }


def analyze_lecture_with_gemma(
    frames: list[dict],
    transcript_segments: list[dict],
    api_key: str = None
) -> dict:
    """
    Submits extracted representative frames and timestamped transcript
    to Gemma 4 (gemma-4-26b-a4b-it) using Google Gen AI SDK & Files API.

    Enforces strict model selection: gemma-4-26b-a4b-it.
    Does NOT substitute proprietary models.
    """
    client = get_gemini_client(api_key)

    # Prepare transcript representation
    transcript_lines = []
    for seg in transcript_segments:
        ts = seg.get("timestamp", f"{seg.get('start', 0)}s - {seg.get('end', 0)}s")
        text = seg.get("text", "")
        transcript_lines.append(f"[{ts}] {text}")
    formatted_transcript = "\n".join(transcript_lines)

    # Upload frames via Gemini Files API
    uploaded_files = []
    contents = []

    try:
        contents.append(
            "You are TeachCheck AI, a world-class educational video consistency checker. "
            "Your task is to analyze an educational programming lecture for inconsistencies between:\n"
            "1. What the instructor says in the spoken audio.\n"
            "2. What visual code or slides appear on screen at each timestamp.\n"
            "3. What the visible programming code actually does when executed.\n\n"
            "### TIMESTAMPED AUDIO TRANSCRIPT:\n"
            f"{formatted_transcript}\n\n"
            "### EXTRACTED REPRESENTATIVE FRAMES:\n"
            "Examine each attached frame corresponding to its timestamp:"
        )

        for frame in frames:
            frame_path = frame["file_path"]
            ts_str = frame["timestamp_str"]
            f_idx = frame["frame_index"]

            # Upload using Gemini Files API
            uploaded_file = client.files.upload(file=frame_path)
            uploaded_files.append(uploaded_file)

            contents.append(f"--- FRAME {f_idx} (Timestamp: {ts_str}, File: {frame['filename']}) ---")
            contents.append(uploaded_file)

        # Append structured analysis instructions
        analysis_prompt = (
            "\n### ANALYSIS INSTRUCTIONS & GUIDELINES:\n"
            "Carefully cross-reference the spoken statements around each timestamp with the visible screen content:\n"
            "- Check whether spoken programming explanations contradict visible code (e.g. wrong method names like .add() vs .append(), off-by-one loop ranges, wrong return types, swapped parameters, syntax errors).\n"
            "- Check whether spoken instructions match what is displayed.\n"
            "- Check whether displayed code does what the instructor claims it does.\n"
            "- CRITICAL RULE: If a frame is blurry, partially occluded, or does NOT contain enough visual evidence to prove an error, classify it as 'Insufficient evidence'. DO NOT classify an issue as a confirmed error without unambiguous visual proof.\n\n"
            "### FINDING CATEGORIES (Use EXACTLY one of these four):\n"
            "1. 'Confirmed inconsistency' (Direct contradiction between audio and visible code/text)\n"
            "2. 'Potential inconsistency' (Plausible mismatch, ambiguity, or likely bug that depends on off-screen code)\n"
            "3. 'No inconsistency observed' (Instructor speech perfectly matches visible screen)\n"
            "4. 'Insufficient evidence' (Frame lacks sufficient code clarity or context to verify)\n\n"
            "### REQUIRED OUTPUT FORMAT:\n"
            "You MUST respond ONLY with valid JSON (no surrounding markdown commentary outside the json block):\n"
            "{\n"
            '  "overall_summary": "Concise 2-3 sentence evaluation of the consistency of the analyzed lecture frames.",\n'
            '  "findings": [\n'
            "    {\n"
            '      "frame_index": 1,\n'
            '      "timestamp": "00:05",\n'
            '      "spoken_statement": "Exact or summarized statement by instructor",\n'
            '      "visible_evidence": "Exact code or UI elements visible in this frame",\n'
            '      "explanation": "Detailed explanation of whether an inconsistency exists and why",\n'
            '      "category": "Confirmed inconsistency",\n'
            '      "suggested_correction": "What the instructor should say or how the code should be fixed"\n'
            "    }\n"
            "  ]\n"
            "}"
        )
        contents.append(analysis_prompt)

        # Call Gemma 4
        # Note: response_mime_type="application/json" (JSON mode) is NOT supported by Gemma models
        # and causes a 400 error. The prompt explicitly instructs JSON output and the parser
        # handles both raw JSON and markdown-wrapped ```json ... ``` responses.
        try:
            response = client.models.generate_content(
                model=GEMMA_MODEL_ID,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.2
                )
            )
        except APIError as api_err:
            error_msg = str(api_err)
            if "not found" in error_msg.lower() or "not supported" in error_msg.lower() or "404" in error_msg:
                raise GemmaAPIError(
                    f"Model '{GEMMA_MODEL_ID}' is currently not available on this API endpoint or key. "
                    f"API Error details: {error_msg}. "
                    "Note: As required by project rules, TeachCheck AI will not substitute a proprietary Gemini model."
                )
            raise GemmaAPIError(f"Google Gen AI API Error: {error_msg}")
        except Exception as gen_err:
            raise GemmaAPIError(f"Gemma 4 generation failed: {str(gen_err)}")

        if not response or not response.text:
            raise GemmaAPIError("Gemma 4 returned an empty response.")

        parsed_result = parse_and_validate_gemma_response(response.text)
        return parsed_result

    finally:
        # Clean up files from Gemini Files API to be good API citizens
        for uf in uploaded_files:
            try:
                client.files.delete(name=uf.name)
            except Exception:
                pass


def get_demo_analysis_data(frames: list[dict] = None) -> dict:
    """
    Returns curated, realistic demonstration analysis data for DEMO MODE.
    Explicitly labelled for demo purposes when users want to evaluate the UI
    or test without an active API key.
    """
    return {
        "is_parsed": True,
        "is_demo_mode": True,
        "parse_error": None,
        "overall_summary": (
            "[DEMO MODE] Analyzed 6 representative frames across the Python Data Structures lecture. "
            "Identified 1 confirmed code-audio contradiction (.append vs .add) and 1 potential off-by-one "
            "boundary mismatch in the loop explanation. The remaining sections were verified."
        ),
        "findings": [
            {
                "finding_id": 1,
                "frame_index": 1,
                "timestamp": "00:00",
                "spoken_statement": "Welcome back everyone, today we are continuing our Python fundamentals course looking at collection types.",
                "visible_evidence": "Slide title: 'Python Fundamentals: List Methods & Iteration' with intro bullet points.",
                "explanation": "Spoken introduction accurately matches the displayed lecture title and agenda.",
                "category": "No inconsistency observed",
                "suggested_correction": "None required."
            },
            {
                "finding_id": 2,
                "frame_index": 2,
                "timestamp": "00:05",
                "spoken_statement": "To add a new element to our Python list, we call the .add() method on the list object.",
                "visible_evidence": "Editor line 4: `scores.append(95)` is typed in the VS Code editor.",
                "explanation": "Direct contradiction. The instructor verbally instructs students to use `.add()`, which is a `set` method in Python and raises an AttributeError when called on a `list`. The screen correctly displays `scores.append(95)`.",
                "category": "Confirmed inconsistency",
                "suggested_correction": "Instructor should verbally state '.append()' instead of '.add()' when explaining Python lists."
            },
            {
                "finding_id": 3,
                "frame_index": 3,
                "timestamp": "00:10",
                "spoken_statement": "Now we are going to print all elements by looping from index 0 through index 5.",
                "visible_evidence": "Editor line 8: `for i in range(len(scores)): print(scores[i])` where `scores` currently has 4 elements.",
                "explanation": "Potential inconsistency. The spoken statement mentions looping through index 5, but the visible list only contains 4 items (indices 0 to 3), and `len(scores)` evaluates to 4.",
                "category": "Potential inconsistency",
                "suggested_correction": "Clarify that the loop will iterate over the current length of 4 elements (indices 0 to 3)."
            },
            {
                "finding_id": 4,
                "frame_index": 4,
                "timestamp": "00:15",
                "spoken_statement": "Let's check the terminal output after running our script.",
                "visible_evidence": "Terminal split panel showing partially scrolled text with obscure bottom prompt.",
                "explanation": "Terminal output is scrolled halfway off-screen. While output text is visible, the specific return code and final printed output are occluded.",
                "category": "Insufficient evidence",
                "suggested_correction": "Ensure terminal panel is enlarged and scrolled to top so learners can verify output."
            },
            {
                "finding_id": 5,
                "frame_index": 5,
                "timestamp": "00:20",
                "spoken_statement": "Here we calculate the average score by taking sum(scores) divided by len(scores).",
                "visible_evidence": "Line 12: `avg = sum(scores) / len(scores)` followed by `print(f'Average: {avg:.2f}')`.",
                "explanation": "The spoken mathematical explanation perfectly matches the visible Python arithmetic implementation.",
                "category": "No inconsistency observed",
                "suggested_correction": "None required."
            },
            {
                "finding_id": 6,
                "frame_index": 6,
                "timestamp": "00:25",
                "spoken_statement": "In the next video we will cover dictionary key-value lookups and hash maps.",
                "visible_evidence": "Summary slide: 'Next Lecture: Dictionaries & Key-Value Lookups'.",
                "explanation": "Closing remarks and preview match the concluding slide text.",
                "category": "No inconsistency observed",
                "suggested_correction": "None required."
            }
        ]
    }
