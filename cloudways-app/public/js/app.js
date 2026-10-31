/**
 * TeachCheck AI — Cloudways Velocity Client Application
 */

document.addEventListener('DOMContentLoaded', () => {
  // ── DOM ELEMENTS ───────────────────────────────────────────────────────────
  const apiStatusCard = document.getElementById('apiStatusCard');
  const modeRadios = document.querySelectorAll('input[name="operationMode"]');
  const demoBanner = document.getElementById('demoModeBanner');

  const dropZone = document.getElementById('dropZone');
  const videoFileInput = document.getElementById('videoFileInput');
  const btnBrowseFile = document.getElementById('btnBrowseFile');
  const fileInfoBox = document.getElementById('fileInfoBox');
  const fileInfoName = document.getElementById('fileInfoName');
  const fileInfoSize = document.getElementById('fileInfoSize');
  const btnRemoveFile = document.getElementById('btnRemoveFile');

  const previewPlaceholder = document.getElementById('previewPlaceholder');
  const videoPlayer = document.getElementById('videoPlayer');

  const btnLoadSample = document.getElementById('btnLoadSample');
  const btnResetApp = document.getElementById('btnResetApp');

  const btnAnalyze = document.getElementById('btnAnalyze');
  const btnAnalyzeText = document.getElementById('btnAnalyzeText');
  const spinIcon = document.getElementById('spinIcon');
  const controlCaption = document.getElementById('controlCaption');

  const progressTracker = document.getElementById('progressTracker');
  const progressBarFill = document.getElementById('progressBarFill');
  const progressStatusText = document.getElementById('progressStatusText');
  const stepBadges = [
    document.getElementById('stepBadge1'),
    document.getElementById('stepBadge2'),
    document.getElementById('stepBadge3'),
    document.getElementById('stepBadge4')
  ];

  const contextSection = document.getElementById('contextSection');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');
  const framesGrid = document.getElementById('framesGrid');
  const frameCount = document.getElementById('frameCount');
  const transcriptList = document.getElementById('transcriptList');

  const resultsSection = document.getElementById('resultsSection');
  const metricTotalIssues = document.getElementById('metricTotalIssues');
  const metricConfirmed = document.getElementById('metricConfirmed');
  const metricPotential = document.getElementById('metricPotential');
  const metricVerified = document.getElementById('metricVerified');
  const metricInsufficient = document.getElementById('metricInsufficient');

  const summaryText = document.getElementById('summaryText');
  const summaryBadge = document.getElementById('summaryBadge');
  const findingsContainer = document.getElementById('findingsContainer');
  const btnDownloadJson = document.getElementById('btnDownloadJson');
  const jsonRawView = document.getElementById('jsonRawView');

  // ── APPLICATION STATE ──────────────────────────────────────────────────────
  let currentFile = null;
  let currentReportData = null;
  let isDemoMode = false;
  let isAnalyzing = false;

  // ── STEP 1: INITIALIZE & CHECK SERVER HEALTH ──────────────────────────────
  async function checkServerHealth() {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();

      if (data.hasApiKey) {
        apiStatusCard.className = 'api-status-card api-status-configured';
        apiStatusCard.innerHTML = `
          <span class="status-indicator"></span>
          <div>
            <div class="api-status-title">Google Gemini API: Configured</div>
            <div class="api-status-desc">Server-side active (masked)</div>
          </div>
        `;
      } else {
        apiStatusCard.className = 'api-status-card api-status-missing';
        apiStatusCard.innerHTML = `
          <span class="status-indicator"></span>
          <div>
            <div class="api-status-title">Google Gemini API: Not Found</div>
            <div class="api-status-desc">Use Demo Mode or set .env</div>
          </div>
        `;
      }
    } catch (err) {
      apiStatusCard.className = 'api-status-card api-status-missing';
      apiStatusCard.innerHTML = `
        <span class="status-indicator"></span>
        <div>
          <div class="api-status-title">Server Offline</div>
          <div class="api-status-desc">Cannot reach backend API</div>
        </div>
      `;
    }
  }

  checkServerHealth();

  // ── STEP 2: MODE SELECTION ────────────────────────────────────────────────
  modeRadios.forEach(radio => {
    radio.addEventListener('change', e => {
      isDemoMode = e.target.value === 'demo';
      if (isDemoMode) {
        demoBanner.classList.remove('hidden');
      } else {
        demoBanner.classList.add('hidden');
      }
      updateAnalyzeButtonState();
    });
  });

  // ── STEP 3: FILE UPLOAD & PREVIEW ─────────────────────────────────────────
  btnBrowseFile.addEventListener('click', () => videoFileInput.click());

  videoFileInput.addEventListener('change', e => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  // Drag and Drop
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, e => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, e => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
    });
  });

  dropZone.addEventListener('drop', e => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  function handleFileSelected(file) {
    const validExts = ['.mp4', '.mov', '.avi'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validExts.includes(ext)) {
      alert(`Unsupported video format "${ext}". Please upload an MP4, MOV, or AVI video.`);
      return;
    }

    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > 200) {
      alert(`File size (${sizeMb.toFixed(1)} MB) exceeds maximum limit of 200 MB.`);
      return;
    }

    currentFile = file;

    // Update UI info
    fileInfoName.textContent = file.name;
    fileInfoSize.textContent = `${sizeMb.toFixed(1)} MB`;
    fileInfoBox.classList.remove('hidden');
    dropZone.classList.add('hidden');

    // Update Video Preview
    const objectUrl = URL.createObjectURL(file);
    videoPlayer.src = objectUrl;
    videoPlayer.classList.remove('hidden');
    previewPlaceholder.classList.add('hidden');

    updateAnalyzeButtonState();
  }

  btnRemoveFile.addEventListener('click', () => {
    clearFile();
    updateAnalyzeButtonState();
  });

  function clearFile() {
    currentFile = null;
    videoFileInput.value = '';
    if (videoPlayer.src) {
      URL.revokeObjectURL(videoPlayer.src);
      videoPlayer.src = '';
    }
    videoPlayer.classList.add('hidden');
    previewPlaceholder.classList.remove('hidden');
    fileInfoBox.classList.add('hidden');
    dropZone.classList.remove('hidden');
  }

  // ── STEP 4: LOAD SAMPLE LECTURE (QUICK DEMO) ─────────────────────────────
  btnLoadSample.addEventListener('click', async () => {
    try {
      btnLoadSample.disabled = true;
      btnLoadSample.textContent = '⏳ Loading Sample...';

      // Switch to Demo Mode for instant review
      const demoRadio = document.querySelector('input[name="operationMode"][value="demo"]');
      if (demoRadio) {
        demoRadio.checked = true;
        isDemoMode = true;
        demoBanner.classList.remove('hidden');
      }

      // Fetch sample mock file representation
      const dummyBlob = new Blob(['sample-mp4-stream'], { type: 'video/mp4' });
      const sampleFile = new File([dummyBlob], 'sample_lecture_python.mp4', { type: 'video/mp4' });
      handleFileSelected(sampleFile);

      btnLoadSample.textContent = '✓ Sample Lecture Loaded';
      setTimeout(() => {
        btnLoadSample.disabled = false;
        btnLoadSample.textContent = '📁 Load Sample Lecture Video';
      }, 1500);
    } catch (err) {
      alert('Could not load sample video.');
      btnLoadSample.disabled = false;
      btnLoadSample.textContent = '📁 Load Sample Lecture Video';
    }
  });

  function updateAnalyzeButtonState() {
    if (currentFile && !isAnalyzing) {
      btnAnalyze.disabled = false;
      controlCaption.textContent = isDemoMode
        ? 'Ready to run benchmark evaluation on selected video (Instant).'
        : 'Ready to run live multimodal verification using Google Gemma 4.';
    } else {
      btnAnalyze.disabled = true;
      controlCaption.textContent = isAnalyzing
        ? 'Consistency analysis in progress...'
        : 'Select or load a lecture video above to begin cross-modal analysis.';
    }
  }

  // ── STEP 5: TABS SWITCHING ────────────────────────────────────────────────
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      document.getElementById(targetId).classList.add('active');
    });
  });

  // ── STEP 6: RUN CONSISTENCY ANALYSIS ──────────────────────────────────────
  btnAnalyze.addEventListener('click', async () => {
    if (!currentFile || isAnalyzing) return;

    isAnalyzing = true;
    updateAnalyzeButtonState();

    // Show Progress
    progressTracker.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    contextSection.classList.add('hidden');
    btnAnalyzeText.textContent = 'Analyzing Lecture...';
    spinIcon.classList.remove('hidden');

    try {
      if (isDemoMode) {
        await runDemoAnalysis();
      } else {
        await runLiveAnalysis();
      }
    } catch (err) {
      alert(`Analysis Failed: ${err.message}`);
      progressStatusText.textContent = `❌ Analysis halted: ${err.message}`;
    } finally {
      isAnalyzing = false;
      btnAnalyzeText.textContent = '🔍 Analyze Lecture Consistency';
      spinIcon.classList.add('hidden');
      updateAnalyzeButtonState();
    }
  });

  function updateProgress(percent, text, stepIndex) {
    progressBarFill.style.width = `${percent}%`;
    progressStatusText.textContent = text;
    stepBadges.forEach((badge, idx) => {
      if (idx < stepIndex) {
        badge.className = 'step-badge done';
      } else if (idx === stepIndex) {
        badge.className = 'step-badge active';
      } else {
        badge.className = 'step-badge';
      }
    });
  }

  // Demo Pipeline Simulation
  async function runDemoAnalysis() {
    updateProgress(25, 'Step 1/4: Validating video metadata...', 0);
    await delay(300);
    updateProgress(50, 'Step 2/4: Extracting representative frames with OpenCV...', 1);
    await delay(350);
    updateProgress(75, 'Step 3/4: Transcribing speech with Faster-Whisper (CPU INT8)...', 2);
    await delay(400);
    updateProgress(90, 'Step 4/4: Cross-referencing speech and visual code with Gemma 4...', 3);

    const res = await fetch('/api/analyze-demo', { method: 'POST' });
    if (!res.ok) throw new Error('Demo endpoint failed.');

    const data = await res.json();
    updateProgress(100, 'Analysis Complete!', 4);
    await delay(200);

    renderResults(data.analysis, []);
  }

  // Live Pipeline Execution
  async function runLiveAnalysis() {
    updateProgress(20, 'Step 1/4: Uploading video and validating parameters...', 0);

    const formData = new FormData();
    formData.append('video', currentFile);

    updateProgress(40, 'Step 2/4: Python Processor extracting frames and transcribing speech...', 1);

    const res = await fetch('/api/analyze', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || `Server responded with HTTP ${res.status}`);
    }

    updateProgress(85, 'Step 4/4: Google Gemma 4 performing multimodal reasoning...', 3);

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || 'Server reported analysis failure.');
    }

    updateProgress(100, 'Analysis Complete!', 4);
    await delay(200);

    renderResults(data.analysis, data.frames || []);
  }

  function delay(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  // ── STEP 7: RENDER VERIFICATION RESULTS ───────────────────────────────────
  function renderResults(analysis, rawFrames) {
    currentReportData = analysis;

    // 1. Context Section
    contextSection.classList.remove('hidden');

    // Frames gallery
    framesGrid.innerHTML = '';
    const framesToDisplay = rawFrames.length > 0 ? rawFrames : (analysis.video_metadata?.total_frames_extracted ? Array.from({ length: 6 }, (_, i) => ({ frame_index: i + 1, timestamp_str: `00:${String(i * 5).padStart(2, '0')}` })) : []);
    frameCount.textContent = framesToDisplay.length;

    framesToDisplay.forEach(f => {
      const card = document.createElement('div');
      card.className = 'frame-card';
      const imgSrc = f.image_base64
        ? `data:${f.mime_type || 'image/jpeg'};base64,${f.image_base64}`
        : '';

      card.innerHTML = `
        ${imgSrc ? `<img src="${imgSrc}" alt="Frame ${f.frame_index}">` : `<div class="finding-img-placeholder">Frame ${f.frame_index}</div>`}
        <div class="frame-card-info">Frame ${f.frame_index} • ⏱️ ${f.timestamp_str}</div>
      `;
      framesGrid.appendChild(card);
    });

    // Transcript List
    transcriptList.innerHTML = '';
    const segments = analysis.transcript_segments || [];
    if (segments.length === 0) {
      transcriptList.innerHTML = '<div style="color: #94A3B8; font-size: 0.9rem;">No transcript segments available.</div>';
    } else {
      segments.forEach(seg => {
        const item = document.createElement('div');
        item.className = 'transcript-item';
        item.innerHTML = `
          <span class="transcript-ts">[${seg.timestamp || '00:00'}]</span>
          <span class="transcript-text">${escapeHtml(seg.text || '')}</span>
        `;
        transcriptList.appendChild(item);
      });
    }

    // 2. Metrics Cards
    const metrics = analysis.summary_metrics || {};
    metricTotalIssues.textContent = metrics.total_issues ?? 0;
    metricConfirmed.textContent = metrics.confirmed_inconsistencies ?? 0;
    metricPotential.textContent = metrics.potential_inconsistencies ?? 0;
    metricVerified.textContent = metrics.verified_sections ?? 0;
    metricInsufficient.textContent = metrics.insufficient_evidence ?? 0;

    // 3. AI Summary
    summaryText.textContent = analysis.overall_summary || 'No summary available.';
    if (analysis.is_demo_mode) {
      summaryBadge.className = 'badge badge-potential';
      summaryBadge.textContent = 'DEMO BENCHMARK';
    } else {
      summaryBadge.className = 'badge badge-verified';
      summaryBadge.textContent = 'GEMMA 4 VERIFIED';
    }

    // 4. Finding Cards
    findingsContainer.innerHTML = '';
    const findings = analysis.findings || [];

    findings.forEach(f => {
      const box = document.createElement('div');
      let boxClass = 'finding-box-potential';
      let badgeHtml = '<span class="badge badge-potential">Potential Inconsistency</span>';

      if (f.category === 'Confirmed inconsistency') {
        boxClass = 'finding-box-confirmed';
        badgeHtml = '<span class="badge badge-confirmed">🚨 Confirmed Inconsistency</span>';
      } else if (f.category === 'No inconsistency observed') {
        boxClass = 'finding-box-verified';
        badgeHtml = '<span class="badge badge-verified">✅ Verified Consistent</span>';
      } else if (f.category === 'Insufficient evidence') {
        boxClass = 'finding-box-insufficient';
        badgeHtml = '<span class="badge badge-insufficient">⚠️ Insufficient Evidence</span>';
      }

      box.className = `finding-box ${boxClass}`;

      // Frame image if available
      const matchingFrame = rawFrames.find(rf => rf.frame_index === f.frame_index);
      const imgHtml = matchingFrame && matchingFrame.image_base64
        ? `<div class="finding-img-wrap"><img src="data:${matchingFrame.mime_type || 'image/jpeg'};base64,${matchingFrame.image_base64}" alt="Frame ${f.frame_index}"></div>`
        : `<div class="finding-img-wrap finding-img-placeholder">Frame ${f.frame_index} Preview</div>`;

      box.innerHTML = `
        ${imgHtml}
        <div class="finding-content">
          <div class="finding-header">
            <span class="finding-ts">⏱️ Timestamp: ${f.timestamp}</span>
            ${badgeHtml}
          </div>
          <div class="finding-row">
            <span class="finding-row-label">🗣️ Spoken Statement:</span>
            <span class="finding-spoken">"${escapeHtml(f.spoken_statement)}"</span>
          </div>
          <div class="finding-row">
            <span class="finding-row-label">👁️ Visible Evidence on Screen:</span>
            <span class="finding-visible">${escapeHtml(f.visible_evidence)}</span>
          </div>
          <div class="finding-row">
            <span class="finding-row-label">🧠 AI Visual Reasoning:</span>
            <span class="finding-reason">${escapeHtml(f.explanation)}</span>
          </div>
          <div class="finding-correction">
            <span class="finding-correction-label">💡 Suggested Correction:</span>
            <span class="finding-correction-text">${escapeHtml(f.suggested_correction)}</span>
          </div>
        </div>
      `;
      findingsContainer.appendChild(box);
    });

    // 5. Raw JSON Inspector
    jsonRawView.textContent = JSON.stringify(analysis, null, 2);

    // Show Results Section
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
  }

  // ── STEP 8: DOWNLOAD JSON REPORT ──────────────────────────────────────────
  btnDownloadJson.addEventListener('click', () => {
    if (!currentReportData) return;
    const jsonStr = JSON.stringify(currentReportData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `teachcheck_report_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // ── STEP 9: RESET APPLICATION ─────────────────────────────────────────────
  btnResetApp.addEventListener('click', () => {
    clearFile();
    contextSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    progressTracker.classList.add('hidden');
    currentReportData = null;
    updateAnalyzeButtonState();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});

