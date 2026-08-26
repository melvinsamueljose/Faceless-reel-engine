import os
import sys
import json
import requests

def send_video_to_telegram():
    # Sanitize inputs by stripping extra quotes, brackets, or whitespace
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip(" '\"[]")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip(" '\"[]")
    
    video_path = "final_reel.mp4"
    script_file = "script_summary.json"

    if not bot_token or not chat_id:
        print("[TELEGRAM ERROR] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secret.")
        sys.exit(1)

    caption_text = "🎬 *Faceless Reel Generated!*"
    if os.path.exists(script_file):
        try:
            with open(script_file, "r") as f:
                data = json.load(f)
                caption_text += f"\n\n📌 *On-Screen Hook:* {data.get('hook')}\n🎙️ *Voiceover Script:* {data.get('voiceover')}"
        except Exception as e:
            print(f"[TELEGRAM WARNING] Could not read script summary: {e}")

    # Build direct endpoint URL
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    print(f"[TELEGRAM] Dispatching video and script summary to chat ID: {chat_id}...")

    if not os.path.exists(video_path):
        print(f"[TELEGRAM ERROR] File '{video_path}' does not exist!")
        sys.exit(1)

    with open(video_path, "rb") as video_file:
        payload = {
            "chat_id": chat_id,
            "caption": caption_text,
            "parse_mode": "Markdown"
        }
        files = {"video": video_file}
        response = requests.post(url, data=payload, files=files, timeout=60)

    if response.status_code == 200:
        print("[TELEGRAM] Video delivered successfully!")
    else:
        print(f"[TELEGRAM ERROR] API returned status {response.status_code}: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    send_video_to_telegram()
