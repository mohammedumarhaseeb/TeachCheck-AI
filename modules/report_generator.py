"""
Report Generator Module for TeachCheck AI
Computes summary metrics and generates structured JSON export reports.
"""

import json
from datetime import datetime


def get_summary_metrics(findings: list[dict]) -> dict:
    """
    Computes summary statistics from the list of findings.
    """
    confirmed = sum(1 for f in findings if f.get("category") == "Confirmed inconsistency")
    potential = sum(1 for f in findings if f.get("category") == "Potential inconsistency")
    verified = sum(1 for f in findings if f.get("category") == "No inconsistency observed")
    insufficient = sum(1 for f in findings if f.get("category") == "Insufficient evidence")

    return {
        "total_issues": confirmed + potential,
        "confirmed_inconsistencies": confirmed,
        "potential_inconsistencies": potential,
        "verified_sections": verified,
        "insufficient_evidence": insufficient,
        "total_findings": len(findings)
    }


def generate_json_report(
    analysis_data: dict,
    video_meta: dict,
    transcript_segments: list[dict],
    frames: list[dict],
    is_demo: bool = False
) -> str:
    """
    Builds a comprehensive JSON report for export.
    """
    findings = analysis_data.get("findings", [])
    metrics = get_summary_metrics(findings)

    report = {
        "application": "TeachCheck AI",
        "tagline": "Don't just watch the lesson. Verify what it teaches.",
        "version": "1.0.0 (MVP)",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "is_demo_mode": is_demo,
        "model_used": "gemma-4-26b-a4b-it",
        "analysis_scope_disclaimer": (
            "This report is based on representative frames extracted at ~5-second intervals "
            "(maximum 6 frames for MVP). It verifies observed moments rather than exhaustive full-lecture footage."
        ),
        "video_metadata": {
            "duration_seconds": video_meta.get("duration_sec", 0),
            "duration_formatted": video_meta.get("duration_str", "00:00"),
            "resolution": f"{video_meta.get('width', 0)}x{video_meta.get('height', 0)}",
            "fps": round(video_meta.get("fps", 0), 2),
            "total_frames_extracted": len(frames)
        },
        "summary_metrics": metrics,
        "overall_summary": analysis_data.get("overall_summary", "No summary available."),
        "findings": findings,
        "transcript_segments": transcript_segments
    }

    return json.dumps(report, indent=2, ensure_ascii=False)
