import os
import sys
from moviepy.editor import (
    ColorClip,
    ImageClip,
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    AudioFileClip
)

# Configuration Constants
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
DEFAULT_FPS = 30
DEFAULT_DURATION = 10.0  # Fallback duration in seconds

def create_faceless_reel(
    bg_video_path=None,
    bg_image_path=None,
    audio_path=None,
    overlay_text="",
    output_path="final_reel.mp4"
):
    """
    Generates a vertical 9:16 reel with proper dark background fallbacks
    and error-checked video composite layering.
    """
    clips_to_composite = []
    total_duration = DEFAULT_DURATION

    # 1. Determine base audio & duration
    audio_clip = None
    if audio_path and os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            total_duration = audio_clip.duration
            print(f"[INFO] Loaded voiceover track. Duration: {total_duration}s")
        except Exception as e:
            print(f"[WARNING] Could not load audio ({e}). Using default duration.")

    # 2. Setup Base Canvas (Default: Solid Black RGB [0,0,0])
    # THIS PREVENTS THE WHITE BACKGROUND ISSUE
    base_bg = ColorClip(
        size=(CANVAS_WIDTH, CANVAS_HEIGHT),
        color=(0, 0, 0),
        duration=total_duration
    )
    clips_to_composite.append(base_bg)

    # 3. Process Background Video / Screen Recording (if provided)
    if bg_video_path and os.path.exists(bg_video_path):
        try:
            print(f"[INFO] Loading video asset: {bg_video_path}")
            video_clip = VideoFileClip(bg_video_path)
            
            # Loop or trim video to match exact audio duration
            if video_clip.duration < total_duration:
                # Loop video if shorter than audio
                n_loops = int(total_duration // video_clip.duration) + 1
                video_clip = video_clip.loop(duration=total_duration)
            else:
                video_clip = video_clip.subclip(0, total_duration)

            # Resize to fill vertical 9:16 frame proportionally
            video_clip = video_clip.resize(height=CANVAS_HEIGHT)
            if video_clip.w < CANVAS_WIDTH:
                video_clip = video_clip.resize(width=CANVAS_WIDTH)
            
            # Center crop to exact 1080x1920
            video_clip = video_clip.crop(
                x_center=video_clip.w / 2,
                y_center=video_clip.h / 2,
                width=CANVAS_WIDTH,
                height=CANVAS_HEIGHT
            )
            
            clips_to_composite.append(video_clip)
        except Exception as e:
            print(f"[ERROR] Failed to process video/screen recording: {e}")
            print("[INFO] Falling back to dark canvas.")

    # 4. Process Background Image (if no video and image exists)
    elif bg_image_path and os.path.exists(bg_image_path):
        try:
            print(f"[INFO] Loading image asset: {bg_image_path}")
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
            print(f"[ERROR] Failed to process background image: {e}")

    # 5. Process Text Overlay (Optional)
    if overlay_text:
        try:
            txt_clip = TextClip(
                overlay_text,
                fontsize=50,
                color='white',
                font='Helvetica-Bold',
                method='caption',
                size=(CANVAS_WIDTH - 100, None)
            ).set_duration(total_duration).set_position(('center', 'center'))
            
            clips_to_composite.append(txt_clip)
        except Exception as e:
            print(f"[WARNING] Could not render TextClip: {e}")

    # 6. Build Final Composite Video
    print("[INFO] Building composite video clip stack...")
    final_video = CompositeVideoClip(clips_to_composite, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    
    if audio_clip:
        final_video = final_video.set_audio(audio_clip)

    # 7. Render Output Video File
    print(f"[INFO] Rendering final reel to {output_path}...")
    final_video.write_videofile(
        output_path,
        fps=DEFAULT_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

    # Clean up open file handles
    final_video.close()
    if audio_clip:
        audio_clip.close()
    print("[SUCCESS] Reel rendered successfully!")

if __name__ == "__main__":
    # Standard asset paths parsed from arguments or environment variables
    bg_video = os.getenv("BG_VIDEO_PATH", "assets/input_video.mp4")
    bg_image = os.getenv("BG_IMAGE_PATH", "assets/input_image.png")
    audio = os.getenv("AUDIO_PATH", "assets/voiceover.mp3")
    text = os.getenv("OVERLAY_TEXT", "")
    output = os.getenv("OUTPUT_PATH", "final_reel.mp4")

    create_faceless_reel(
        bg_video_path=bg_video if os.path.exists(bg_video) else None,
        bg_image_path=bg_image if os.path.exists(bg_image) else None,
        audio_path=audio if os.path.exists(audio) else None,
        overlay_text=text,
        output_path=output
    )
