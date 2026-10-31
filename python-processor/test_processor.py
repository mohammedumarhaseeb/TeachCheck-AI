"""
Test suite for Python Processor FastAPI microservice
Verifies:
1. /health endpoint
2. 401 Unauthorized when X-Internal-Secret is missing/invalid
3. 200 OK when X-Internal-Secret is valid, processing sample video
4. Validates base64 frame encoding and Whisper transcript
"""

import os
import sys
import time
import requests

PROCESSOR_URL = "http://127.0.0.1:8000"
SECRET = "tc_internal_secret_change_in_production_12345"
SAMPLE_VIDEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data", "sample_lecture_python.mp4")

print(f"=== Testing Python Processor at {PROCESSOR_URL} ===")

# 1. Health Check
try:
    res = requests.get(f"{PROCESSOR_URL}/health", timeout=5)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print("1. Health check: PASS -", res.json())
except Exception as e:
    print("1. Health check: FAIL -", e)
    sys.exit(1)

# 2. Auth Rejection (Missing header)
dummy_files = {"video": ("test.mp4", b"dummy content", "video/mp4")}
res = requests.post(f"{PROCESSOR_URL}/api/v1/process-video", files=dummy_files, timeout=5)
assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
print("2. Auth check (missing header): PASS - rejected with 401")

# 3. Auth Rejection (Invalid header)
dummy_files2 = {"video": ("test.mp4", b"dummy content", "video/mp4")}
res = requests.post(f"{PROCESSOR_URL}/api/v1/process-video", files=dummy_files2, headers={"X-Internal-Secret": "wrong_secret"}, timeout=5)
assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
print("3. Auth check (invalid header): PASS - rejected with 401")

# 4. Process Video with Valid Auth
print("4. Processing sample video through Python Processor...")
t0 = time.time()
with open(SAMPLE_VIDEO, "rb") as vf:
    files = {"video": ("sample_lecture_python.mp4", vf, "video/mp4")}
    headers = {"X-Internal-Secret": SECRET}
    res = requests.post(f"{PROCESSOR_URL}/api/v1/process-video", files=files, headers=headers, timeout=60)

elapsed = time.time() - t0
assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
data = res.json()

assert data["success"] == True, "Expected success: True"
assert len(data["frames"]) == 6, f"Expected 6 frames, got {len(data['frames'])}"
assert len(data["transcript_segments"]) >= 5, f"Expected >= 5 segments, got {len(data['transcript_segments'])}"

# Check that frames have base64 content
for f in data["frames"]:
    assert "image_base64" in f and len(f["image_base64"]) > 1000, f"Invalid base64 for frame {f['frame_index']}"

print(f"4. Video processing: PASS in {elapsed:.2f}s!")
print(f"   Frames extracted: {len(data['frames'])}")
print(f"   Transcript segments: {len(data['transcript_segments'])}")
print(f"   First segment: [{data['transcript_segments'][0]['timestamp']}] {data['transcript_segments'][0]['text'][:50]}...")
print("=== Python Processor Tests ALL PASSED! ===")
