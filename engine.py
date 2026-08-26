import os
import sys
import requests

# Handles imports across MoviePy versions safely
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

# Target Resolution (9:16 Vertical Reel)
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

    # 1. Load Audio Track
    audio_clip = None
    if audio_path and os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            total_duration = audio_clip.duration
            print(f"[ENGINE] Audio loaded successfully ({total_duration:.2f}s).")
        except Exception as e:
            print(f"[WARNING] Failed to load audio track ({e}). Using default duration.")

    # 2. Base Canvas Layer (Solid Black RGB: 0, 0, 0)
    base_bg = ColorClip(
        size=(CANVAS_WIDTH, CANVAS_HEIGHT),
        color=(0, 0, 0),
        duration=total_duration
    )
    clips_to_composite.append(base_bg)

    # 3. Process Video / Screen Recording Layer
    if bg_video_path and os.path.exists(bg_video_path):
        try:
            print(f"[ENGINE] Loading video asset: {bg_video_path}")
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
            print("[ENGINE] Video asset composited successfully.")
        except Exception as e:
            print(f"[ERROR] Could not load video clip: {e}")

    # 4. Fallback Background Image Layer
    elif bg_image_path and os.path.exists(bg_image_path):
        try:
            print(f"[ENGINE] Loading image asset: {bg_image_path}")
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
            print(f"[ERROR] Could not load background image: {e}")

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
            print(f"[WARNING] Text rendering skipped: {e}")

    # 6. Build Final Video Output
    print("[ENGINE] Rendering final composite video timeline...")
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
    print("[ENGINE] Export completed successfully!")

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
