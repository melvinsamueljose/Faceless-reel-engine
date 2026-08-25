import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_file():
    video_dir = "output"
    
    if not os.path.exists(video_dir):
        print("Error: output/ directory does not exist.")
        return

    # Locate generated video file in output/
    files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith('.webm') or f.endswith('.mp4')]
    
    if not files:
        print("Error: No video files found in output/.")
        return

    video_path = files[0]
    audio_path = os.path.join(video_dir, "voice.mp3")

    # Send Video File
    print(f"Sending video file: {video_path}")
    url_video = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(video_path, 'rb') as video:
        res_v = requests.post(url_video, data={'chat_id': CHAT_ID, 'caption': '🎬 Demo Video Ready!'}, files={'video': video})
        print(f"Video Send Status: {res_v.status_code}")
        print(f"Video Send Response: {res_v.text}")

    # Send Audio Voiceover File (if present)
    if os.path.exists(audio_path):
        print(f"Sending audio file: {audio_path}")
        url_audio = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
        with open(audio_path, 'rb') as audio:
            res_a = requests.post(url_audio, data={'chat_id': CHAT_ID, 'caption': '🎙️ Generated AI Voiceover'}, files={'audio': audio})
            print(f"Audio Send Status: {res_a.status_code}")

if __name__ == "__main__":
    send_file()
