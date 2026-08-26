import os
import sys
import json
import requests

def send_video_to_telegram():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    video_path = "final_reel.mp4"
    script_file = "script_summary.json"

    if not bot_token or not chat_id:
        print("[TELEGRAM ERROR] Bot token or Chat ID missing.")
        sys.exit(1)

    # Load generated script verification log
    caption_text = "🎬 *Faceless Reel Generated!*"
    if os.path.exists(script_file):
        try:
            with open(script_file, "r") as f:
                data = json.load(f)
                caption_text += f"\n\n📌 *On-Screen Hook:* {data.get('hook')}\n🎙️ *Voiceover Script:* {data.get('voiceover')}"
        except Exception as e:
            print(f"[TELEGRAM WARNING] Could not read script log: {e}")

    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/sendVideo"
    print(f"[TELEGRAM] Dispatching video and script summary to chat {chat_id}...")

    with open(video_path, "rb") as video_file:
        payload = {
            "chat_id": chat_id,
            "caption": caption_text,
            "parse_mode": "Markdown"
        }
        files = {"video": video_file}
        response = requests.post(url, data=payload, files=files)

    if response.status_code == 200:
        print("[TELEGRAM] Delivered successfully!")
    else:
        print(f"[TELEGRAM ERROR] Response {response.status_code}: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    send_video_to_telegram()
