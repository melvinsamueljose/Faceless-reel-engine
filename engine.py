import os
import sys
import asyncio
import requests
from playwright.async_api import async_playwright

try:
    from moviepy.editor import (
        ColorClip,
        ImageClip,
        VideoFileClip,
        TextClip,
        CompositeVideoClip,
        AudioFileClip
    )
except ImportError:
    from moviepy.video.VideoClip import ColorClip, ImageClip, TextClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
DEFAULT_FPS = 30

async def record_website_video(url, output_video_path="recording.webm", duration=10):
    """
    Launches headless chromium via Playwright, opens target URL, and captures a video recording.
    """
    print(f"[PLAYWRIGHT] Starting screen recording of {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Configure mobile/vertical viewport for reel recording
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir="recordings/",
            record_video_size={"width": 1080, "height": 1920}
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            print(f"[PLAYWRIGHT] Page loaded successfully. Recording for {duration} seconds...")
            
            # Smooth scroll effect down the page
            for i in range(5):
                await page.evaluate(f"window.scrollBy(0, {400});")
                await asyncio.sleep(duration / 5)
        except Exception as e:
            print(f"[PLAYWRIGHT ERROR] Error during browser session: {e}")
        finally:
            await context.close()
            await browser.close()

    # Move generated webm file to expected path
    recording_dir = "recordings"
    if os.path.exists(recording_dir):
        files = [os.path.join(recording_dir, f) for f in os.listdir(recording_dir) if f.endswith(".webm")]
        if files:
            os.rename(files[0], output_video_path)
            print(f"[PLAYWRIGHT] Saved video recording to {output_video_path}")
            return output_video_path
    return None

def generate_reel(
    bg_video_path=None,
    bg_image_path=None,
    audio_path=None,
    overlay_text="",
    output_path="final_reel.mp4"
):
    print("[ENGINE] Initializing Reel Generation Pipeline...")
    clips_to_composite = []
    total_duration = 10.0

    # 1. Base Audio
    audio_clip = None
    if audio_path and os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            total_duration = audio_clip.duration
            print(f"[ENGINE] Loaded audio track ({total_duration:.2f}s).")
        except Exception as e:
            print(f"[WARNING] Could not load audio: {e}")

    # 2. Base Layer (Black background)
    base_bg = ColorClip(
        size=(CANVAS_WIDTH, CANVAS_HEIGHT),
        color=(0, 0, 0),
        duration=total_duration
    )
    clips_to_composite.append(base_bg)

    # 3. Screen Recording Layer
    if bg_video_path and os.path.exists(bg_video_path):
        try:
            print(f"[ENGINE] Adding screen recording layer from: {bg_video_path}")
            video_clip = VideoFileClip(bg_video_path)
            
            if video_clip.duration < total_duration:
                video_clip = video_clip.loop(duration=total_duration)
            else:
                video_clip = video_clip.subclip(0, total_duration)

            video_clip = video_clip.resize(height=CANVAS_HEIGHT)
            if video_clip.w < CANVAS_WIDTH:
                video_clip = video_clip.resize(width=CANVAS_WIDTH)
            
            video_clip = video_clip.crop(
                x_center=video_clip.w / 2,
                y_center=video_clip.h / 2,
                width=CANVAS_WIDTH,
                height=CANVAS_HEIGHT
            )
            clips_to_composite.append(video_clip)
            print("[ENGINE] Screen recording layer merged into video.")
        except Exception as e:
            print(f"[ERROR] Failed to composite screen recording: {e}")

    # 4. Text Overlay Layer
    if overlay_text:
        try:
            txt_clip = TextClip(
                overlay_text,
                fontsize=48,
                color='white',
                font='DejaVu-Sans-Bold',
                method='caption',
                size=(CANVAS_WIDTH - 120, None)
            ).set_duration(total_duration).set_position(('center', 'center'))
            
            clips_to_composite.append(txt_clip)
        except Exception as e:
            print(f"[WARNING] Text rendering failed: {e}")

    # 5. Composite Output
    print("[ENGINE] Exporting final video...")
    final_video = CompositeVideoClip(clips_to_composite, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    if audio_clip:
        final_video = final_video.set_audio(audio_clip)

    final_video.write_videofile(
        output_path,
        fps=DEFAULT_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

    final_video.close()
    if audio_clip:
        audio_clip.close()
    print("[ENGINE] Video export successful!")

if __name__ == "__main__":
    target_url = os.getenv("TOOL_URL", "https://aicarousels.com")
    rec_path = "recording.webm"
    
    # Run Playwright scraper to capture website video before rendering
    captured_video = asyncio.run(record_website_video(target_url, rec_path, duration=10))

    aud_path = os.getenv("AUDIO_PATH", "assets/voiceover.mp3")
    txt_content = os.getenv("OVERLAY_TEXT", f"Check out {target_url}")
    out_path = os.getenv("OUTPUT_PATH", "final_reel.mp4")

    generate_reel(
        bg_video_path=captured_video if captured_video else None,
        audio_path=aud_path if os.path.exists(aud_path) else None,
        overlay_text=txt_content,
        output_path=out_path
    )
