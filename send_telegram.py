import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_file():
    video_path = "output/final_reel.mp4"
    audio_path = "output/voice.mp3"
    
    if not os.path.exists(video_path):
        print("Error: output/final_reel.mp4 does not exist.")
        return

    # Send Final Compiled Reel Video
    print(f"Sending compiled Reel to Telegram: {video_path}")
    url_video = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(video_path, 'rb') as video:
        res_v = requests.post(url_video, data={'chat_id': CHAT_ID, 'caption': '🎬 Reel 5 Final Output Ready!'}, files={'video': video})
        print(f"Video Send Status: {res_v.status_code}")
        print(f"Video Send Response: {res_v.text}")

    # Send Raw Audio File
    if os.path.exists(audio_path):
        url_audio = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
        with open(audio_path, 'rb') as audio:
            requests.post(url_audio, data={'chat_id': CHAT_ID, 'caption': '🎙️ Generated AI Voiceover'}, files={'audio': audio})

if __name__ == "__main__":
    send_file()
