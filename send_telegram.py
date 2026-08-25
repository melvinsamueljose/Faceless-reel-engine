import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_file():
    video_dir = "output"
    if not os.path.exists(video_dir):
        print("Output directory does not exist.")
        return

    files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith('.webm') or f.endswith('.mp4')]
    if not files:
        print("No video files found.")
        return

    video_path = files[0]
    
    # Send Video
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(video_path, 'rb') as video:
        res = requests.post(url, data={'chat_id': CHAT_ID, 'caption': '🎬 Your Faceless Reel is Ready!'}, files={'video': video})
        print(f"Telegram API Response Status: {res.status_code}")
        print(f"Telegram API Response Body: {res.text}")

if __name__ == "__main__":
    send_file()
