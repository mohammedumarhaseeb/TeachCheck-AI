# TeachCheck AI 🎯
> *"Don't just watch the lesson. Verify what it teaches."*

TeachCheck AI is an automated educational video consistency checker designed to expose discrepancies between:
1. **What the instructor says** (spoken audio).
2. **What appears on screen** (slides, editor, terminal).
3. **What the displayed code actually executes** (program behavior, method names, loop boundaries).

Built for the **MLH / Google AI Hackathon**, powered strictly by **Google Gemma 4 (`gemma-4-26b-a4b-it`)** as its visual reasoning engine, coupled with **Faster-Whisper (INT8 CPU)** and **OpenCV** frame analysis.

---

## 📌 Problem Statement

Online programming education is booming, but recorded video lectures frequently suffer from subtle, confusing bugs:
- **Audio-to-Visual Mismatches**: An instructor verbally says `.add()`, while the screen displays `.append()`. In Python, `.add()` only exists on `set` objects and throws an `AttributeError` on lists.
- **Off-by-One Boundary Errors**: An instructor claims a loop iterates through index 5, but the visible list only contains 4 items.
- **Occluded Output**: Critical terminal output is scrolled halfway off-screen or unreadable.

Students waste countless hours debugging code that contradicted what the teacher spoke. **TeachCheck AI acts as an automated pedagogical peer reviewer**, catching cross-modal discrepancies before videos reach learners.

---

## 🛠️ Technology Stack

| Component | Technology | Role |
|---|---|---|
| **Visual Reasoning Engine** | **Google Gemma 4 (`gemma-4-26b-a4b-it`)** | Multimodal reasoning over extracted lecture frames & transcript |
| **Speech Transcription** | **Faster-Whisper (`tiny` on CPU, INT8)** | Fast, offline, timestamped audio transcription |
| **Frame Sampling** | **OpenCV (`opencv-python`)** | Representative frame extraction (~1 frame every 5s, max 6 frames) |
| **Audio Demuxing** | **FFmpeg (`imageio-ffmpeg`)** | Extracts 16kHz mono uncompressed WAV audio |
| **Cloud Web Server** | **Node.js (Express + Helmet + CORS + RateLimit)** | Cloudways Velocity deployment, API gateway & Gemma 4 orchestrator |
| **Multimedia Microservice**| **Python (FastAPI + Pydantic + Uvicorn)** | CPU-bound multimedia worker with internal bearer authentication |
| **Local Dashboard** | **Streamlit** | Rapid local testing interface with interactive cards |
| **Frontend UI** | **Vanilla HTML5, CSS3 & JavaScript** | High-contrast, zero-framework, dark navy & purple UI |

---

## 🏛️ System Architecture

TeachCheck AI supports two deployment topologies:
1. **Cloudways Velocity Architecture (Distributed / Production)**: High-performance Node.js/Express web application deployed on Cloudways Velocity, interfacing with a secure Python multimedia microservice and Google Gemma 4.
2. **Standalone Streamlit Architecture (Local / Rapid Testing)**: Single-process dashboard for rapid local experimentation.

### Distributed Production Topology (Cloudways Velocity)
```
                                 [ Cloudways Velocity ]
+----------------------+        +-----------------------+        +---------------------------+
|                      |  HTTP  |  Node.js Web App      |  REST  |  Google Gen AI API        |
|  Student / Judge     |------->|  (Express + Frontend) |------->|  (gemma-4-26b-a4b-it)     |
|  Browser             |        |  Port 3000            |        +---------------------------+
+----------------------+        +-----------------------+
                                            |
                                            | Internal HTTP
                                            | (X-Internal-Secret)
                                            v
                                +-----------------------+
                                |  Python Microservice  |
                                |  (FastAPI + Whisper)  |
                                |  Port 8000            |
                                +-----------------------+
                                  - FFmpeg 16kHz audio
                                  - Faster-Whisper INT8
                                  - OpenCV frame sampling
```

---

## 📁 Repository Structure

```
TeachCheck-AI/
├── cloudways-app/                  # Cloudways Velocity Node.js Application
│   ├── package.json                # Express, Multer, Helmet, Rate-Limit dependencies
│   ├── .env.example                # Cloudways environment variable template
│   ├── server.js                   # Node.js backend & Gemma 4 REST orchestrator
│   ├── test_node_app.js            # Node.js test suite
│   └── public/                     # Modern responsive dark-themed frontend
│       ├── index.html              # Single-page interface
│       ├── css/style.css           # Navy & purple design system
│       └── js/app.js               # Client state, drag-and-drop, report export
│
├── python-processor/               # Python Multimedia Processing Microservice
│   ├── main.py                     # FastAPI service (OpenCV, FFmpeg, Whisper)
│   ├── requirements.txt            # Microservice dependencies
│   ├── test_processor.py           # Automated Python processor test suite
│   └── .env.example                # Internal server auth template
│
├── modules/                        # Reusable core Python processing modules
│   ├── video_processor.py          # OpenCV frame extraction & FFmpeg audio extraction
│   ├── audio_transcriber.py        # Faster-Whisper INT8 CPU transcription & fallback parser
│   ├── gemma_analyzer.py           # Google Gen AI SDK + Gemma 4 integration
│   └── report_generator.py         # Metrics aggregation & JSON export generator
│
├── app.py                          # Original Streamlit dashboard (preserved)
├── requirements.txt                # Streamlit root dependencies
├── sample_data/                    # Bundled test lecture & generator
│   └── sample_lecture_python.mp4   # 30s test video with .append vs .add mismatch
├── .env.example                    # Root environment variable template
├── .gitignore                      # Multi-tier secret and cache exclusions
└── README.md                       # Comprehensive deployment & architecture documentation
```

---

## 💻 Local Setup & Development

### 1. Prerequisites
- **Python 3.10+** (tested on 3.11)
- **Node.js 18+** (tested on Node v24)
- **Google Gemini API Key** with Gemma 4 access ([Google AI Studio](https://aistudio.google.com/))

### 2. Start Python Processor Microservice
```bash
cd python-processor
pip install -r requirements.txt
cp .env.example .env
python main.py
# Running on http://127.0.0.1:8000
```

### 3. Start Cloudways Node.js Application
```bash
cd cloudways-app
npm install
cp .env.example .env
# Edit .env and insert your GEMINI_API_KEY
node server.js
# Running on http://127.0.0.1:3000
```

Open your browser at **`http://localhost:3000`**.

---

## 🚀 Cloudways Velocity Deployment Guide

Cloudways Velocity provides native Git deployment, SSL, and Node.js process management.

### 1. Cloudways Application Settings
- **Application Deployment Directory:** `cloudways-app/`
- **Install Command:** `npm install --omit=dev`
- **Build Command:** `npm run build` *(default serves pre-built static assets)*
- **Start Command:** `npm start` *(runs `node server.js`)*

### 2. Environment Variables Configuration
Configure these in the Cloudways Server Settings:
```ini
PORT=3000
NODE_ENV=production
PYTHON_PROCESSOR_URL=https://your-python-service.domain.com
INTERNAL_AUTH_SECRET=your_strong_random_token_here
GEMINI_API_KEY=your_actual_google_gemini_api_key_here
ALLOWED_ORIGINS=https://your-app.cloudwaysapps.com
```

### 3. Python Microservice Deployment
Host `python-processor/` as a container or background service on Railway, Render, AWS EC2, or a VPS:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## 🔒 API Security Architecture

- **Server-Side Key Isolation**: `GEMINI_API_KEY` is strictly held on the Node.js server. It is **never** sent to the client browser, never logged, and never included in error responses.
- **Server-to-Server Authentication**: Communication between Node.js and the Python microservice is guarded by a shared internal token (`X-Internal-Secret`). Direct public requests are rejected with `HTTP 401 Unauthorized`.
- **Zero Secrets in Git**: Multi-tier `.gitignore` patterns strictly exclude all `.env` files across root and subfolders. Templates contain placeholders only.
- **Defensive Error Handling**: Rejections use strict HTTP codes (`400` Bad Request, `401` Unauthorized, `413` Payload Too Large, `500` Internal Server Error) without exposing internal paths or stack traces.
- **Automatic Temp File Purging**: Uploaded video files, extracted audio WAVs, and sampled frames are automatically purged in `finally` blocks immediately post-processing.
- **Rate Limiting**: Public analysis endpoints are rate-limited via `express-rate-limit` (20 requests per 15 minutes per IP).

---

## 🎨 UI & Dashboard Features

```
+-----------------------------------------------------------------------------------------+
|  🎯 TeachCheck AI  |  "Don't just watch the lesson. Verify what it teaches."            |
+-----------------------------------------------------------------------------------------+
| [Upload Lecture Video]          | [Video Preview Player]                                |
| Drag & drop (MP4, MOV, AVI)     | 🎬 Shows synchronized lecture video                   |
+-----------------------------------------------------------------------------------------+
| [🔍 Analyze Lecture Consistency]   Progress: [==================== 100%] Complete       |
+-----------------------------------------------------------------------------------------+
| METRICS:  [2 Total Issues]  [2 Confirmed Errors]  [0 Mismatches]  [0 Verified]  [0 Insuff]|
+-----------------------------------------------------------------------------------------+
| FINDINGS:                                                                               |
|  🚨 Frame 2 [00:07] — Confirmed Inconsistency                                           |
|     🗣️ Spoken: "To add a new element to our Python list, we call the add method..."     |
|     👁️ Visible: scores.append(95)                                                       |
|     🧠 AI Reasoning: Lists use .append(). In Python, .add() is for sets (AttributeError)|
|     💡 Correction: "To add a new element to our Python list, we call the append method" |
+-----------------------------------------------------------------------------------------+
| [📥 Download JSON Report]        | [🛠️ Inspect Raw Report Payload]                       |
+-----------------------------------------------------------------------------------------+
```

---

## 🏆 Benchmark Demo Scenario

The bundled sample video (`sample_data/sample_lecture_python.mp4`) presents a 30-second Python lesson covering list manipulation:
- **Frame 2 (`00:05` / `00:07`)**: Instructor says: *"To add a new element to our Python list, we call the add method..."*, while the editor screen clearly shows `scores.append(95)`. TeachCheck AI flags this as a **Confirmed Inconsistency**.
- **Frame 3 (`00:10` / `00:13`)**: Instructor claims the loop iterates through index 5, but the visible list has only 4 elements. TeachCheck AI flags this as a **Confirmed Inconsistency** (out-of-bounds loop range).
- **Frame 4 (`00:15`)**: Partially occluded terminal. TeachCheck AI accurately flags this as **Insufficient Evidence**.
- **Frame 5 (`00:20`)**: Arithmetic matches `sum(scores) / len(scores)`. Verified consistent.

---

## ⚠️ Known Limitations

1. **Gemma 4 Multimodal Inference Latency**: Multimodal reasoning over 6 high-resolution frames via `gemma-4-26b-a4b-it` takes 60–120 seconds depending on Google API queue load. *(The 1-click Demo Mode is provided for instantaneous judging without API quota).*
2. **Whisper Tiny Quantization**: On synthetic text-to-speech audio, Whisper `tiny` may transcribe `"sum"` as `"some"`. On human voice, accuracy is significantly higher.
