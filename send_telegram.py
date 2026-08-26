import os
import sys
import requests

def send_video_to_telegram():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    video_path = os.getenv("OUTPUT_PATH", "final_reel.mp4")

    if not bot_token or not chat_id:
        print("[TELEGRAM] Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secrets.")
        sys.exit(1)

    if not os.path.exists(video_path):
        print(f"[TELEGRAM] Error: Rendered output '{video_path}' not found.")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    print(f"[TELEGRAM] Delivering '{video_path}' to target Telegram chat...")

    with open(video_path, "rb") as video_file:
        payload = {
            "chat_id": chat_id,
            "caption": "🎬 *Faceless Reel Output Ready!*",
            "parse_mode": "Markdown"
        }
        files = {"video": video_file}
        response = requests.post(url, data=payload, files=files)

    if response.status_code == 200:
        print("[TELEGRAM] Video sent successfully!")
    else:
        print(f"[TELEGRAM] Delivery failed ({response.status_code}): {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    send_video_to_telegram()
