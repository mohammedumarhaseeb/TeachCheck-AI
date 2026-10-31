"""
Generates a realistic educational programming lecture video (sample_data/sample_lecture_python.mp4)
with synchronized spoken audio and VS Code-style IDE graphics.
Demonstrates consistency discrepancies:
- Screen shows `.append()` while speech says `.add()`
- Screen loop range vs spoken boundary
- Verified sections
"""

import os
import subprocess
import cv2
import numpy as np
import imageio_ffmpeg


def create_editor_frame(lines: list[tuple[str, tuple[int, int, int]]], title: str, status_text: str = "") -> np.ndarray:
    """
    Renders an 800x500 dark-themed IDE frame with title bar, line numbers, and syntax colored text.
    """
    width, height = 800, 500
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (30, 30, 30)  # Dark background #1E1E1E

    # Title bar #252526
    cv2.rectangle(img, (0, 0), (width, 36), (37, 37, 37), -1)

    # Window control dots (mac/linux style)
    cv2.circle(img, (20, 18), 6, (60, 60, 255), -1)   # Red
    cv2.circle(img, (40, 18), 6, (60, 215, 255), -1)  # Yellow
    cv2.circle(img, (60, 18), 6, (80, 200, 80), -1)   # Green

    # Title text
    cv2.putText(img, f"TeachCheck AI - {title}", (85, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)

    # Line number gutter
    cv2.rectangle(img, (0, 36), (55, height - 30), (33, 33, 33), -1)

    y_pos = 75
    for idx, (code_line, color) in enumerate(lines, 1):
        # Line number
        cv2.putText(img, f"{idx:2d}", (15, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (110, 110, 110), 1, cv2.LINE_AA)
        # Code text
        cv2.putText(img, code_line, (70, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1, cv2.LINE_AA)
        y_pos += 30

    # Status bar at bottom
    cv2.rectangle(img, (0, height - 28), (width, height), (70, 30, 110), -1)
    cv2.putText(img, f"Python 3.11 | UTF-8 | {status_text}", (15, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1, cv2.LINE_AA)

    return img


def create_slide_frame(header: str, subheaders: list[str], subtitle: str) -> np.ndarray:
    """
    Renders an educational presentation slide frame.
    """
    width, height = 800, 500
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (24, 18, 15)  # Deep navy background

    # Decorative top bar
    cv2.rectangle(img, (0, 0), (width, 10), (255, 120, 0), -1)

    # Slide Header
    cv2.putText(img, header, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, subtitle, (52, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 180, 255), 1, cv2.LINE_AA)

    # Divider
    cv2.line(img, (50, 165), (750, 165), (80, 80, 120), 1)

    # Subheaders
    y_pos = 220
    for bullet in subheaders:
        cv2.circle(img, (60, y_pos - 6), 5, (255, 140, 50), -1)
        cv2.putText(img, bullet, (80, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (230, 230, 230), 1, cv2.LINE_AA)
        y_pos += 45

    # Footer
    cv2.putText(img, "TeachCheck AI Educational Test Suite", (50, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 120, 140), 1, cv2.LINE_AA)
    return img


def generate_sample_video():
    sample_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(sample_dir, exist_ok=True)
    video_raw_path = os.path.join(sample_dir, "temp_video_no_audio.mp4")
    audio_path = os.path.join(sample_dir, "temp_audio.wav")
    final_video_path = os.path.join(sample_dir, "sample_lecture_python.mp4")

    # 1. Generate Voice Narration using Windows Speech Synthesizer via PowerShell
    narration = (
        "Welcome back everyone. Today we are continuing our Python fundamentals course on collection types. "
        "To add a new element to our Python list, we call the add method on the list object. "
        "Now we will loop through index 0 through index 5 to display each score. "
        "Let us check the terminal output after running our script. "
        "Here we compute the average score by taking sum of scores divided by length of scores. "
        "In our next lecture, we will explore Python dictionaries and sets."
    )

    ps_script_path = os.path.join(sample_dir, "gen_audio.ps1")
    with open(ps_script_path, "w", encoding="utf-8") as f:
        f.write(f'''
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate = -1
$speaker.SetOutputToWaveFile("{audio_path.replace(os.sep, '/')}")
$speaker.Speak("{narration}")
$speaker.Dispose()
''')

    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script_path], check=True)
    if os.path.exists(ps_script_path):
        os.remove(ps_script_path)

    # 2. Generate Video Frames (6 scenes, 5 seconds each at 10 fps = 300 frames)
    # Define scenes
    CYAN = (230, 200, 70)
    WHITE = (240, 240, 240)
    GREEN = (100, 210, 100)
    PURPLE = (220, 120, 220)
    GRAY = (130, 130, 130)

    scene1_frame = create_slide_frame(
        "Python Fundamentals",
        ["Introduction to List Operations", "Mutability and Common Methods", "Iterating with For Loops"],
        "Lecture 4: Sequence Types"
    )

    scene2_lines = [
        ("# Lesson: Adding elements to a list", GRAY),
        ("scores = [85, 90, 78]", CYAN),
        ("", WHITE),
        ("# Note: We use .append() on lists", GRAY),
        ("scores.append(95)", GREEN),
        ("", WHITE),
        ("print('Updated scores:', scores)", WHITE),
    ]
    scene2_frame = create_editor_frame(scene2_lines, "main.py - Adding Elements", "Line 5, Col 1")

    scene3_lines = [
        ("# Lesson: Looping over scores", GRAY),
        ("scores = [85, 90, 78, 95]", CYAN),
        ("", WHITE),
        ("for i in range(len(scores)):", PURPLE),
        ("    print(f'Score {i}: {scores[i]}')", WHITE),
    ]
    scene3_frame = create_editor_frame(scene3_lines, "main.py - List Iteration", "Line 4, Col 5")

    # Scene 4: Terminal view
    scene4_lines = [
        ("Terminal - bash (output window)", GRAY),
        ("$ python main.py", GREEN),
        ("Updated scores: [85, 90, 78, 95]", WHITE),
        ("Score 0: 85", WHITE),
        ("Score 1: 90", WHITE),
        ("Score 2: 78", WHITE),
        ("Score 3: 95", WHITE),
        ("[Process completed with exit code 0]", GRAY),
    ]
    scene4_frame = create_editor_frame(scene4_lines, "Terminal Output", "Terminal View")

    scene5_lines = [
        ("# Lesson: Computing Statistics", GRAY),
        ("total = sum(scores)", CYAN),
        ("count = len(scores)", CYAN),
        ("average = total / count", PURPLE),
        ("print(f'Class Average: {average:.2f}')", WHITE),
    ]
    scene5_frame = create_editor_frame(scene5_lines, "main.py - Summary Metrics", "Line 5, Col 1")

    scene6_frame = create_slide_frame(
        "Lecture Wrap-Up",
        ["Next Video: Dictionaries & Key-Value Lookups", "Self-Assessment Exercises on Portal", "Q&A Discussion Forum"],
        "Thank you for watching!"
    )

    scenes = [scene1_frame, scene2_frame, scene3_frame, scene4_frame, scene5_frame, scene6_frame]

    fps = 10
    seconds_per_scene = 5
    frames_per_scene = fps * seconds_per_scene
    width, height = 800, 500

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_raw_path, fourcc, fps, (width, height))

    for scene in scenes:
        for _ in range(frames_per_scene):
            out.write(scene)

    out.release()

    # 3. Combine Video and Audio using FFmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    combine_cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_raw_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        final_video_path
    ]
    subprocess.run(combine_cmd, check=True)

    # Cleanup temp
    if os.path.exists(video_raw_path):
        os.remove(video_raw_path)
    if os.path.exists(audio_path):
        os.remove(audio_path)

    print(f"Sample lecture video successfully created at: {final_video_path}")


if __name__ == "__main__":
    generate_sample_video()
