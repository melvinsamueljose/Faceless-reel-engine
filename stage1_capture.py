import os
import re
import json
import requests

def clean_token(token_str):
    token = re.sub(r'[\[\]\'"\s]', '', str(token_str))
    if "bot" in token:
        token = token.split("bot")[-1]
    return token

def fetch_telegram_input():
    bot_token = clean_token(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    resp = requests.get(url).json()
    if not resp.get("ok"):
        raise RuntimeError("Failed to fetch Telegram updates.")

    latest_video_id = None
    user_caption = ""

    # Search updates backwards for the last uploaded media
    for result in reversed(resp.get("result", [])):
        msg = result.get("message", {})
        caption = msg.get("caption", "") or msg.get("text", "")
        
        if "/create_reel" in caption or "HOOK:" in caption:
            user_caption = caption
            if "video" in msg:
                latest_video_id = msg["video"]["file_id"]
                break
            elif "document" in msg and msg["document"]["mime_type"].startswith("video/"):
                latest_video_id = msg["document"]["file_id"]
                break

    # Default fallbacks if no new media attached
    hook = "INSANE AI TOOL FOR CREATORS!"
    voiceover = "Check out this AI tool to automate your digital content workflow."
    caption_style = "default_white"
    edit_instructions = "Full clip display."

    if user_caption:
        for line in user_caption.split("\n"):
            if line.startswith("HOOK:"):
                hook = line.replace("HOOK:", "").strip()
            elif line.startswith("VOICEOVER:"):
                voiceover = line.replace("VOICEOVER:", "").strip()
            elif line.startswith("CAPTION_STYLE:"):
                caption_style = line.replace("CAPTION_STYLE:", "").strip()

        if "PROMPT:" in user_caption:
            edit_instructions = user_caption.split("PROMPT:")[-1].strip()

    script_data = {
        "hook": hook,
        "voiceover": voiceover,
        "caption_style": caption_style,
        "instructions": edit_instructions
    }

    with open("script.json", "w") as f:
        json.dump(script_data, f, indent=2)

    if latest_video_id:
        file_info = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={latest_video_id}").json()
        file_path = file_info["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        
        print("[STAGE 1] Downloading raw manual recording from Telegram...")
        res = requests.get(download_url)
        with open("raw_desktop.webm", "wb") as f:
            f.write(res.content)
        print("[STAGE 1] Raw media saved successfully.")

def notify_received():
    bot_token = clean_token(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = clean_token(os.getenv("TELEGRAM_CHAT_ID", ""))
    
    with open("script.json", "r") as f:
        data = json.load(f)

    msg = (
        "⚙️ *Raw Media & Edit Instructions Received*\n\n"
        f"📌 *Hook:* {data['hook']}\n"
        f"🎙️ *Voiceover:* {data['voiceover']}\n"
        f"🎨 *Style:* {data['caption_style']}\n\n"
        "⚡ *Processing Stage 2 HyperFrames render now...*"
    )
    
    api_endpoint = "https://api.telegram.org/bot" + bot_token + "/sendMessage"
    requests.post(api_endpoint, data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    fetch_telegram_input()
    notify_received()
