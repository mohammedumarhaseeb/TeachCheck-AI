/**
 * TeachCheck AI — Cloudways Velocity Node.js Application Server
 * Serves the responsive dark-themed UI and provides secure backend orchestration
 * between the Python multimedia processor and Google Gemma 4 (gemma-4-26b-a4b-it).
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

// Load environment variables from .env
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_PROCESSOR_URL = process.env.PYTHON_PROCESSOR_URL || 'http://127.0.0.1:8000';
const INTERNAL_AUTH_SECRET = process.env.INTERNAL_AUTH_SECRET || 'tc_internal_secret_change_in_production_12345';
const GEMMA_MODEL_ID = 'gemma-4-26b-a4b-it';

// Security Headers via Helmet (with permissive resource loading for local media preview)
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        fontSrc: ["'self'", "https://fonts.gstatic.com"],
        imgSrc: ["'self'", "data:", "blob:"],
        mediaSrc: ["'self'", "data:", "blob:"]
      }
    },
    crossOriginEmbedderPolicy: false
  })
);

// CORS Policy
const allowedOrigins = (process.env.ALLOWED_ORIGINS || 'http://localhost:3000,http://127.0.0.1:3000')
  .split(',')
  .map(o => o.trim());

app.use(
  cors({
    origin: (origin, callback) => {
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(new Error('Blocked by CORS policy'));
      }
    },
    credentials: true
  })
);

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Rate Limiting on Analysis API (20 requests per 15 minutes per IP)
const analysisLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    error: 'Too many analysis requests from this IP. Please try again after 15 minutes.'
  }
});

// Configure Multer for secure temporary video upload
const uploadsDir = path.join(__dirname, 'temp_uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadsDir),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `upload_${Date.now()}_${Math.random().toString(36).substring(2, 8)}${ext}`);
  }
});

const fileFilter = (req, file, cb) => {
  const allowed = ['.mp4', '.mov', '.avi'];
  const ext = path.extname(file.originalname).toLowerCase();
  if (allowed.includes(ext)) {
    cb(null, true);
  } else {
    cb(new Error(`Unsupported video format "${ext}". Allowed: ${allowed.join(', ')}`), false);
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: 200 * 1024 * 1024 } // 200 MB limit
});

// Serve frontend static assets from public/
app.use(express.static(path.join(__dirname, 'public')));

// ── HEALTH CHECK ─────────────────────────────────────────────────────────────
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'teachcheck-cloudways-app',
    model: GEMMA_MODEL_ID,
    hasApiKey: Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY !== 'your_gemini_api_key_here'),
    timestamp: new Date().toISOString()
  });
});

// ── UTILITY: CLEAN JSON TEXT ────────────────────────────────────────────────
function cleanJsonText(rawText) {
  if (!rawText) return '';
  let cleaned = rawText.trim();

  // If markdown code block exists anywhere in the text, extract its inner contents
  const codeBlockMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (codeBlockMatch && codeBlockMatch[1]) {
    cleaned = codeBlockMatch[1].trim();
  }

  // Find the outermost JSON object bounds
  const firstBrace = cleaned.indexOf('{');
  const lastBrace = cleaned.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
    return cleaned.substring(firstBrace, lastBrace + 1).trim();
  }

  return cleaned;
}

// ── UTILITY: PARSE GEMMA RESPONSE ───────────────────────────────────────────
function parseGemmaResponse(rawText) {
  const validCategories = [
    'Confirmed inconsistency',
    'Potential inconsistency',
    'No inconsistency observed',
    'Insufficient evidence'
  ];

  const cleaned = cleanJsonText(rawText);
  let data = null;

  try {
    data = JSON.parse(cleaned);
  } catch (err) {
    const match = cleaned.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        data = JSON.parse(match[0]);
      } catch (err2) {
        return {
          is_parsed: false,
          raw_response: rawText,
          overall_summary: 'Raw output could not be strictly parsed as JSON.',
          findings: []
        };
      }
    } else {
      return {
        is_parsed: false,
        raw_response: rawText,
        overall_summary: 'Raw output could not be strictly parsed as JSON.',
        findings: []
      };
    }
  }

  const rawFindings = Array.isArray(data.findings) ? data.findings : [];
  const normalizedFindings = rawFindings.map((item, idx) => {
    const rawCat = (item.category || '').toLowerCase();
    let matchedCat = 'Potential inconsistency';
    for (const valid of validCategories) {
      if (rawCat.includes(valid.toLowerCase()) || valid.toLowerCase().includes(rawCat)) {
        matchedCat = valid;
        break;
      }
    }

    return {
      finding_id: idx + 1,
      frame_index: item.frame_index || idx + 1,
      timestamp: item.timestamp || `Frame ${idx + 1}`,
      spoken_statement: item.spoken_statement || 'N/A',
      visible_evidence: item.visible_evidence || 'N/A',
      explanation: item.explanation || 'No explanation provided.',
      category: matchedCat,
      suggested_correction: item.suggested_correction || 'None'
    };
  });

  return {
    is_parsed: true,
    raw_response: rawText,
    overall_summary: data.overall_summary || 'Analysis completed.',
    findings: normalizedFindings
  };
}

// ── UTILITY: COMPUTE METRICS ────────────────────────────────────────────────
function computeSummaryMetrics(findings) {
  const confirmed = findings.filter(f => f.category === 'Confirmed inconsistency').length;
  const potential = findings.filter(f => f.category === 'Potential inconsistency').length;
  const verified = findings.filter(f => f.category === 'No inconsistency observed').length;
  const insufficient = findings.filter(f => f.category === 'Insufficient evidence').length;

  return {
    total_issues: confirmed + potential,
    confirmed_inconsistencies: confirmed,
    potential_inconsistencies: potential,
    verified_sections: verified,
    insufficient_evidence: insufficient,
    total_findings: findings.length
  };
}

// ── UTILITY: CURATED BENCHMARK DATA (DEMO MODE) ─────────────────────────────
function getDemoBenchmarkData(frames = [], meta = {}) {
  const findings = [
    {
      finding_id: 1,
      frame_index: 1,
      timestamp: '00:00',
      spoken_statement: 'Welcome back everyone, today we are continuing our Python fundamentals course looking at collection types.',
      visible_evidence: "Slide title: 'Python Fundamentals: List Methods & Iteration' with intro bullet points.",
      explanation: 'Spoken introduction accurately matches the displayed lecture title and agenda.',
      category: 'No inconsistency observed',
      suggested_correction: 'None required.'
    },
    {
      finding_id: 2,
      frame_index: 2,
      timestamp: '00:05',
      spoken_statement: 'To add a new element to our Python list, we call the .add() method on the list object.',
      visible_evidence: 'Editor line 4: `scores.append(95)` is typed in the editor.',
      explanation: "Direct contradiction. The instructor verbally instructs students to use `.add()`, which is a `set` method in Python and raises an AttributeError when called on a `list`. The screen correctly displays `scores.append(95)`.",
      category: 'Confirmed inconsistency',
      suggested_correction: "Instructor should verbally state '.append()' instead of '.add()' when explaining Python lists."
    },
    {
      finding_id: 3,
      frame_index: 3,
      timestamp: '00:10',
      spoken_statement: 'Now we are going to print all elements by looping from index 0 through index 5.',
      visible_evidence: 'Editor line 8: `for i in range(len(scores)): print(scores[i])` where `scores` currently has 4 elements.',
      explanation: 'Potential inconsistency. The spoken statement mentions looping through index 5, but the visible list only contains 4 items (indices 0 to 3), and `len(scores)` evaluates to 4.',
      category: 'Potential inconsistency',
      suggested_correction: 'Clarify that the loop will iterate over the current length of 4 elements (indices 0 to 3).'
    },
    {
      finding_id: 4,
      frame_index: 4,
      timestamp: '00:15',
      spoken_statement: "Let's check the terminal output after running our script.",
      visible_evidence: 'Terminal split panel showing partially scrolled text with obscure bottom prompt.',
      explanation: 'Terminal output is scrolled halfway off-screen. While output text is visible, the specific return code and final printed output are occluded.',
      category: 'Insufficient evidence',
      suggested_correction: 'Ensure terminal panel is enlarged and scrolled to top so learners can verify output.'
    },
    {
      finding_id: 5,
      frame_index: 5,
      timestamp: '00:20',
      spoken_statement: 'Here we calculate the average score by taking sum(scores) divided by len(scores).',
      visible_evidence: "Line 12: `avg = sum(scores) / len(scores)` followed by `print(f'Average: {avg:.2f}')`.",
      explanation: 'The spoken mathematical explanation perfectly matches the visible Python arithmetic implementation.',
      category: 'No inconsistency observed',
      suggested_correction: 'None required.'
    },
    {
      finding_id: 6,
      frame_index: 6,
      timestamp: '00:25',
      spoken_statement: 'In the next video we will cover dictionary key-value lookups and hash maps.',
      visible_evidence: "Summary slide: 'Next Lecture: Dictionaries & Key-Value Lookups'.",
      explanation: 'Closing remarks and preview match the concluding slide text.',
      category: 'No inconsistency observed',
      suggested_correction: 'None required.'
    }
  ];

  return {
    is_parsed: true,
    is_demo_mode: true,
    model_used: GEMMA_MODEL_ID,
    overall_summary: '[DEMO BENCHMARK] Analyzed 6 representative frames across the Python Data Structures lecture. Identified 1 confirmed code-audio contradiction (.append vs .add) and 1 potential off-by-one boundary mismatch in the loop explanation. The remaining sections were verified.',
    summary_metrics: computeSummaryMetrics(findings),
    findings,
    video_metadata: {
      duration_seconds: meta.duration_sec || 30.0,
      duration_formatted: meta.duration_str || '00:30',
      resolution: `${meta.width || 800}x${meta.height || 500}`,
      fps: meta.fps || 10.0,
      total_frames_extracted: frames.length || 6
    }
  };
}

// ── ROUTE: DEMO ANALYSIS (Instant Benchmark) ───────────────────────────────
app.post('/api/analyze-demo', async (req, res) => {
  try {
    const demoData = getDemoBenchmarkData();
    res.json({
      success: true,
      analysis: demoData
    });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Failed to generate demo benchmark data.' });
  }
});

// ── ROUTE: LIVE CONSISTENCY ANALYSIS (Gemma 4) ─────────────────────────────
app.post('/api/analyze', analysisLimiter, upload.single('video'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ success: false, error: 'No video file provided.' });
  }

  const uploadedFilePath = req.file.path;
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey || apiKey === 'your_gemini_api_key_here') {
    // Clean up uploaded file
    if (fs.existsSync(uploadedFilePath)) fs.unlinkSync(uploadedFilePath);
    return res.status(400).json({
      success: false,
      error: 'GEMINI_API_KEY is not configured on the server. Please check your environment variables or use Demo Mode.'
    });
  }

  try {
    // 1. Forward video to Python Processing Microservice
    const fileStream = fs.createReadStream(uploadedFilePath);
    const formBlob = new Blob([fs.readFileSync(uploadedFilePath)]);
    const formData = new FormData();
    formData.append('video', formBlob, req.file.originalname);

    let pythonResponse = null;
    try {
      const pyRes = await fetch(`${PYTHON_PROCESSOR_URL}/api/v1/process-video`, {
        method: 'POST',
        headers: {
          'X-Internal-Secret': INTERNAL_AUTH_SECRET
        },
        body: formData
      });

      if (!pyRes.ok) {
        if (pyRes.status === 401) {
          const authErr = new Error('Authentication failed: Invalid internal service credentials.');
          authErr.statusCode = 401;
          throw authErr;
        }
        if (pyRes.status === 413) {
          const sizeErr = new Error('File size exceeds the maximum upload limit of 200 MB.');
          sizeErr.statusCode = 413;
          throw sizeErr;
        }
        if (pyRes.status === 400) {
          const formatErr = new Error('Unsupported video format. Allowed formats: .mp4, .mov, .avi');
          formatErr.statusCode = 400;
          throw formatErr;
        }
        const errorBody = await pyRes.text();
        throw new Error(`Python Processor failed with HTTP ${pyRes.status}`);
      }

      pythonResponse = await pyRes.json();
    } catch (fetchErr) {
      throw new Error(`Failed to communicate with Python Processor: ${fetchErr.message}`);
    }

    const { video_metadata, transcript_segments, frames } = pythonResponse;

    // 2. Prepare Gemma 4 Multimodal Payload
    const transcriptText = (transcript_segments || [])
      .map(s => `[${s.timestamp}] ${s.text}`)
      .join('\n');

    const promptText = `You are TeachCheck AI, a world-class educational video consistency checker.
Your task is to analyze an educational programming lecture for inconsistencies between:
1. What the instructor says in the spoken audio.
2. What visual code or slides appear on screen at each timestamp.
3. What the visible programming code actually does when executed.

### TIMESTAMPED AUDIO TRANSCRIPT:
${transcriptText}

### EXTRACTED REPRESENTATIVE FRAMES:
Examine each attached frame corresponding to its timestamp.

### ANALYSIS INSTRUCTIONS & GUIDELINES:
Carefully cross-reference the spoken statements around each timestamp with the visible screen content:
- Check whether spoken programming explanations contradict visible code (e.g. wrong method names like .add() vs .append(), off-by-one loop ranges, wrong return types, swapped parameters, syntax errors).
- Check whether spoken instructions match what is displayed.
- Check whether displayed code does what the instructor claims it does.
- CRITICAL RULE: If a frame is blurry, partially occluded, or does NOT contain enough visual evidence to prove an error, classify it as 'Insufficient evidence'. DO NOT classify an issue as a confirmed error without unambiguous visual proof.

### FINDING CATEGORIES (Use EXACTLY one of these four):
1. 'Confirmed inconsistency' (Direct contradiction between audio and visible code/text)
2. 'Potential inconsistency' (Plausible mismatch, ambiguity, or likely bug that depends on off-screen code)
3. 'No inconsistency observed' (Instructor speech perfectly matches visible screen)
4. 'Insufficient evidence' (Frame lacks sufficient code clarity or context to verify)

### REQUIRED OUTPUT FORMAT:
You MUST respond ONLY with valid JSON (no surrounding markdown commentary outside the json block):
{
  "overall_summary": "Concise 2-3 sentence evaluation of the consistency of the analyzed lecture frames.",
  "findings": [
    {
      "frame_index": 1,
      "timestamp": "00:05",
      "spoken_statement": "Exact or summarized statement by instructor",
      "visible_evidence": "Exact code or UI elements visible in this frame",
      "explanation": "Detailed explanation of whether an inconsistency exists and why",
      "category": "Confirmed inconsistency",
      "suggested_correction": "What the instructor should say or how the code should be fixed"
    }
  ]
}`;

    // Assemble contents array: parts mixing text and base64 inline images
    const parts = [{ text: promptText }];

    for (const f of (frames || [])) {
      parts.push({
        text: `--- FRAME ${f.frame_index} (Timestamp: ${f.timestamp_str}, File: ${f.filename}) ---`
      });
      parts.push({
        inline_data: {
          mime_type: f.mime_type || 'image/jpeg',
          data: f.image_base64
        }
      });
    }

    // 3. Call Google Gemma 4 via official Gen AI REST Endpoint
    const gemmaApiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${GEMMA_MODEL_ID}:generateContent?key=${apiKey}`;

    const gemmaRes = await fetch(gemmaApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        contents: [{ parts }],
        generationConfig: {
          temperature: 0.2
        }
      })
    });

    if (!gemmaRes.ok) {
      const errText = await gemmaRes.text();
      throw new Error(`Google Gemma 4 API Error (HTTP ${gemmaRes.status}): ${errText}`);
    }

    const gemmaJson = await gemmaRes.json();
    const candidateText =
      gemmaJson.candidates?.[0]?.content?.parts?.[0]?.text || '';

    if (!candidateText) {
      throw new Error('Gemma 4 returned an empty candidate text response.');
    }

    // 4. Parse & Normalize Gemma Output
    const parsedAnalysis = parseGemmaResponse(candidateText);
    const summaryMetrics = computeSummaryMetrics(parsedAnalysis.findings);

    // Build complete report object
    const finalReport = {
      application: 'TeachCheck AI',
      tagline: "Don't just watch the lesson. Verify what it teaches.",
      version: '1.0.0 (Cloudways Velocity Stack)',
      generated_at: new Date().toISOString(),
      is_demo_mode: false,
      model_used: GEMMA_MODEL_ID,
      analysis_scope_disclaimer:
        'This report is based on representative frames extracted at ~5-second intervals (maximum 6 frames for MVP). It verifies observed moments rather than exhaustive full-lecture footage.',
      video_metadata: {
        duration_seconds: video_metadata?.duration_sec || 0,
        duration_formatted: video_metadata?.duration_str || '00:00',
        resolution: `${video_metadata?.width || 0}x${video_metadata?.height || 0}`,
        fps: video_metadata?.fps || 0,
        total_frames_extracted: (frames || []).length
      },
      summary_metrics: summaryMetrics,
      overall_summary: parsedAnalysis.overall_summary,
      findings: parsedAnalysis.findings,
      transcript_segments: transcript_segments || []
    };

    res.json({
      success: true,
      analysis: finalReport,
      frames: (frames || []).map(f => ({
        frame_index: f.frame_index,
        timestamp_str: f.timestamp_str,
        mime_type: f.mime_type,
        image_base64: f.image_base64
      }))
    });
  } catch (err) {
    if (err.statusCode === 401 || err.status === 401) {
      return res.status(401).json({ success: false, error: err.message });
    }
    if (err.statusCode === 413 || err.status === 413) {
      return res.status(413).json({ success: false, error: err.message });
    }
    if (err.statusCode === 400 || err.status === 400) {
      return res.status(400).json({ success: false, error: err.message });
    }

    console.error('[TeachCheck API Error]:', err.message);
    return res.status(500).json({
      success: false,
      error: 'An internal error occurred during video analysis. Please try again.'
    });
  } finally {
    // 5. Clean up temporary uploaded video file
    if (fs.existsSync(uploadedFilePath)) {
      try {
        fs.unlinkSync(uploadedFilePath);
      } catch (cleanupErr) {
        // Non-blocking cleanup warning
      }
    }
  }
});

// Global error handling middleware (handles Multer and route-level validation errors)
app.use((err, req, res, next) => {
  // 1. Oversized file (Multer LIMIT_FILE_SIZE or HTTP 413)
  if ((err instanceof multer.MulterError && err.code === 'LIMIT_FILE_SIZE') || err.statusCode === 413 || err.status === 413) {
    return res.status(413).json({
      success: false,
      error: 'File size exceeds maximum allowed upload limit of 200 MB.'
    });
  }

  // 2. Invalid video format / unsupported format (HTTP 400)
  if (
    (err.message && err.message.toLowerCase().includes('unsupported video format')) ||
    err.statusCode === 400 ||
    err.status === 400 ||
    err instanceof multer.MulterError
  ) {
    return res.status(400).json({
      success: false,
      error: 'Unsupported video format. Allowed formats: .mp4, .mov, .avi'
    });
  }

  // 3. Unauthorized (HTTP 401)
  if (err.statusCode === 401 || err.status === 401) {
    return res.status(401).json({
      success: false,
      error: 'Unauthorized: Missing or invalid authentication.'
    });
  }

  // 4. Unexpected server error (HTTP 500)
  console.error('[TeachCheck Unhandled Error]:', err.message);
  return res.status(500).json({
    success: false,
    error: 'An internal server error occurred. Please try again.'
  });
});

app.listen(PORT, () => {
  console.log(`TeachCheck AI Cloudways Web Server listening on port ${PORT}`);
  console.log(`Python Processor URL: ${PYTHON_PROCESSOR_URL}`);
  console.log(`Reasoning Engine: Google Gemma 4 (${GEMMA_MODEL_ID})`);
});

