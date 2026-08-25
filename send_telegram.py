import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_file():
    video_dir = "output"
    
    # Ensure directory exists before reading
    if not os.path.exists(video_dir):
        print("Output directory does not exist yet.")
        return

    files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith('.webm') or f.endswith('.mp4')]
    if not files:
        print("No video files found in output directory.")
        return

    video_path = files[0]
    audio_path = os.path.join(video_dir, "voice.mp3")

    # Send Video
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(video_path, 'rb') as video:
        requests.post(url, data={'chat_id': CHAT_ID, 'caption': '🎬 Demo Recording Ready!'}, files={'video': video})

    # Send Audio (if present)
    if os.path.exists(audio_path):
        url_doc = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        with open(audio_path, 'rb') as audio:
            requests.post(url_doc, data={'chat_id': CHAT_ID, 'caption': '🎙️ Generated Voiceover Track'}, files={'document': audio})

if __name__ == "__main__":
    send_file()
