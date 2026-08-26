import os
import sys
import json
import asyncio
import glob
from PIL import Image, ImageDraw, ImageFont

# --- MOVIEPY + PILLOW 10+ COMPATIBILITY ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

import edge_tts
from playwright.async_api import async_playwright

try:
    from moviepy.editor import (
        ColorClip,
        VideoFileClip,
        ImageClip,
        CompositeVideoClip,
        AudioFileClip,
        concatenate_videoclips
    )
    import moviepy.video.fx.all as vfx
except ImportError:
    from moviepy.video.VideoClip import ColorClip, ImageClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    import moviepy.video.fx.all as vfx

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
DEFAULT_FPS = 30

def generate_script_with_openrouter(target_url):
    """Generates punchy, viral hook & script."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]

    if not api_key:
        return {
            "hook": "Stop wasting hours on carousels!",
            "voiceover": f"This tool creates viral carousels in 10 seconds. Just enter your prompt, let the AI design the slides, and hit export!"
        }

    prompt = f"""
    Write a viral 8-second Instagram Reel script for {target_url}.
    Return strictly JSON:
    {{
      "hook": "Short punchy 4-6 word hook",
      "voiceover": "Fast-paced 20-25 word high-energy pitch."
    }}
    """

    try:
        import requests
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": prompt}]
            }),
            timeout=15
        )
        data = response.json()
        raw_text = data['choices'][0]['message']['content'].strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        print(f"[AI SCRIPT ERROR] {e}")
        return {
            "hook": "Create carousels 10x faster!",
            "voiceover": f"Need social media posts fast? {domain} generates and formats full carousel designs using AI automatically!"
        }

async def generate_voiceover(text, output_audio_path="voiceover.mp3"):
    """Synthesizes high-pitch fast voiceover."""
    print(f"[TTS] Synthesizing speech...")
    communicate = edge_tts.Communicate(text, voice="en-US-ChristopherNeural", rate="+15%")
    await communicate.save(output_audio_path)
    return output_audio_path

async def record_hyperframe_shots(url, output_dir="shots"):
    """
    Captures fast-cut multi-scene shots:
    Shot 1: Hero Page Scroll
    Shot 2: Direct Click Action
    Shot 3: App Workspace Overview
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"[HYPERFRAME RECORD] Capturing multi-scene workflow for {url}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        # Shot 1: Landing Page
        ctx1 = await browser.new_context(viewport={"width": 1080, "height": 1920}, record_video_dir=output_dir)
        p1 = await ctx1.new_page()
        await p1.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        await p1.mouse.wheel(0, 500)
        await asyncio.sleep(1.5)
        await ctx1.close()

        # Shot 2: Button Interaction
        ctx2 = await browser.new_context(viewport={"width": 1080, "height": 1920}, record_video_dir=output_dir)
        p2 = await ctx2.new_page()
        await p2.goto(url, wait_until="domcontentloaded")
        cta = p2.locator("a:has-text('Create Carousel'), button:has-text('Create Carousel'), a.btn").first
        if await cta.is_visible():
            await cta.hover()
            await asyncio.sleep(0.5)
            await cta.click()
            await asyncio.sleep(2)
        await ctx2.close()

        await browser.close()

    # Find recorded WebM shots
    recorded_files = sorted(glob.glob(os.path.join(output_dir, "*.webm")), key=os.path.getctime)
    return recorded_files

def create_caption_overlay(text, width=1080, height=1920, output_img_path="caption_overlay.png"):
    """Creates modern pop-up text banner."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 54) if os.path.exists(font_path) else ImageFont.load_default()

    words = text.split()
    lines, current_line = [], []

    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        bbox = draw.textbbox((0, 0), line_str, font=font)
        if (bbox[2] - bbox[0]) > (width - 200):
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    wrapped_text = "\n".join(lines).upper()
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=12)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    x = (width - text_w) / 2
    y = height - text_h - 320

    # Draw neon accent card background
    draw.rounded_rectangle(
        [x - 35, y - 20, x + text_w + 35, y + text_h + 20],
        radius=16, fill=(0, 0, 0, 240), outline=(0, 255, 170, 255), width=5
    )
    draw.multiline_text((x, y), wrapped_text, font=font, fill=(255, 255, 255, 255), align="center", spacing=12)
    img.save(output_img_path)
    return output_img_path

def build_and_render_reel(shot_paths, audio_path, overlay_text, output_path="final_reel.mp4"):
    """Composites modular cuts with 1.75x speed ramps and zoom keyframing."""
    print("[HYPERFRAME RENDER] Building fast-paced timeline...")
    audio_clip = AudioFileClip(audio_path)
    target_duration = audio_clip.duration + 0.3

    processed_clips = []
    
    if shot_paths:
        num_shots = len(shot_paths)
        per_shot_duration = target_duration / num_shots

        for idx, shot_file in enumerate(shot_paths):
            clip = VideoFileClip(shot_file)
            
            # Apply 1.75x Speed Ramp to delete dead space
            clip = clip.fx(vfx.speedx, 1.75)
            clip = clip.subclip(0, min(per_shot_duration, clip.duration))

            # Apply Zoom FX on second shot (CTA Interaction)
            if idx == 1:
                clip = clip.resize(width=CANVAS_WIDTH * 1.2)  # 120% Zoom
                clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
            else:
                clip = clip.resize(width=CANVAS_WIDTH)
                clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)

            processed_clips.append(clip)

        # Concatenate fast cuts into a single stream
        background_track = concatenate_videoclips(processed_clips, method="compose")
        if background_track.duration < target_duration:
            background_track = background_track.loop(duration=target_duration)
        else:
            background_track = background_track.subclip(0, target_duration)
    else:
        background_track = ColorClip(size=(CANVAS_WIDTH, CANVAS_HEIGHT), color=(15, 15, 18), duration=target_duration)

    layers = [background_track]

    # Add Text Overlay Layer
    if overlay_text:
        caption_img = create_caption_overlay(overlay_text, CANVAS_WIDTH, CANVAS_HEIGHT)
        caption_clip = ImageClip(caption_img).set_duration(target_duration)
        layers.append(caption_clip)

    final_video = CompositeVideoClip(layers, size=(CANVAS_WIDTH, CANVAS_HEIGHT)).set_audio(audio_clip)
    
    print(f"[ENGINE] Exporting HyperFrame reel to {output_path}...")
    final_video.write_videofile(
        output_path,
        fps=DEFAULT_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

    final_video.close()
    audio_clip.close()

async def main():
    target_url = os.getenv("TOOL_URL", "[https://aicarousels.com](https://aicarousels.com)")
    
    script_data = generate_script_with_openrouter(target_url)
    hook_text = script_data.get("hook")
    voiceover_text = script_data.get("voiceover")

    with open("script_summary.json", "w") as f:
        json.dump({"hook": hook_text, "voiceover": voiceover_text}, f, indent=2)

    audio_file = await generate_voiceover(voiceover_text, "voiceover.mp3")
    shot_files = await record_hyperframe_shots(target_url, "shots")

    build_and_render_reel(shot_files, audio_file, hook_text, "final_reel.mp4")

if __name__ == "__main__":
    asyncio.run(main())
