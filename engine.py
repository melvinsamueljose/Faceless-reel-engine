import os
import sys
import requests
from moviepy.editor import (
    ColorClip,
    ImageClip,
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    AudioFileClip
)

# Render Target Resolution (9:16 Vertical Reel)
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
DEFAULT_FPS = 30
DEFAULT_DURATION = 10.0

def generate_reel(
    bg_video_path=None,
    bg_image_path=None,
    audio_path=None,
    overlay_text="",
    output_path="final_reel.mp4"
):
    print("[ENGINE] Initializing Reel Generation Pipeline...")
    clips_to_composite = []
    total_duration = DEFAULT_DURATION

    # 1. Load Audio & Target Duration
    audio_clip = None
    if audio_path and os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            total_duration = audio_clip.duration
            print(f"[ENGINE] Audio loaded successfully. Target duration: {total_duration:.2f}s")
        except Exception as e:
            print(f"[WARNING] Failed to load audio clip ({e}). Using default duration ({DEFAULT_DURATION}s).")

    # 2. Base Canvas Layer (Solid Black RGB: 0, 0, 0)
    # Fixes the solid white background bug when assets are missing or transparent.
    base_bg = ColorClip(
        size=(CANVAS_WIDTH, CANVAS_HEIGHT),
        color=(0, 0, 0),
        duration=total_duration
    )
    clips_to_composite.append(base_bg)

    # 3. Process Video / Screen Recording Layer
    if bg_video_path and os.path.exists(bg_video_path):
        try:
            print(f"[ENGINE] Processing background video track: {bg_video_path}")
            video_clip = VideoFileClip(bg_video_path)
            
            # Loop video if shorter than target audio length
            if video_clip.duration < total_duration:
                video_clip = video_clip.loop(duration=total_duration)
            else:
                video_clip = video_clip.subclip(0, total_duration)

            # Proportional Resize & Crop to 1080x1920
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
            print("[ENGINE] Video track layered successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to composite video recording: {e}")

    # 4. Fallback Background Image Layer
    elif bg_image_path and os.path.exists(bg_image_path):
        try:
            print(f"[ENGINE] Processing background image track: {bg_image_path}")
            img_clip = ImageClip(bg_image_path).set_duration(total_duration)
            img_clip = img_clip.resize(height=CANVAS_HEIGHT)
            if img_clip.w < CANVAS_WIDTH:
                img_clip = img_clip.resize(width=CANVAS_WIDTH)
            
            img_clip = img_clip.crop(
                x_center=img_clip.w / 2,
                y_center=img_clip.h / 2,
                width=CANVAS_WIDTH,
                height=CANVAS_HEIGHT
            )
            clips_to_composite.append(img_clip)
        except Exception as e:
            print(f"[ERROR] Failed to composite background image: {e}")

    # 5. Text Overlay Layer
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
            print(f"[WARNING] Skipping text overlay rendering: {e}")

    # 6. Composite & Render Video File
    print("[ENGINE] Compositing all visual clips into final timeline...")
    final_video = CompositeVideoClip(clips_to_composite, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    
    if audio_clip:
        final_video = final_video.set_audio(audio_clip)

    print(f"[ENGINE] Rendering final reel output to: {output_path}")
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
    print("[ENGINE] Render completed successfully!")

if __name__ == "__main__":
    bg_vid = os.getenv("BG_VIDEO_PATH", "assets/input_video.mp4")
    bg_img = os.getenv("BG_IMAGE_PATH", "assets/input_image.png")
    aud_path = os.getenv("AUDIO_PATH", "assets/voiceover.mp3")
    txt_content = os.getenv("OVERLAY_TEXT", "")
    out_path = os.getenv("OUTPUT_PATH", "final_reel.mp4")

    generate_reel(
        bg_video_path=bg_vid if os.path.exists(bg_vid) else None,
        bg_image_path=bg_img if os.path.exists(bg_img) else None,
        audio_path=aud_path if os.path.exists(aud_path) else None,
        overlay_text=txt_content,
        output_path=out_path
    )
