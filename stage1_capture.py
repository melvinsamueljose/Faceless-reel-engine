import os
import sys
import json
import re
import requests

def clean_token(token_str):
    """
    Strips brackets, quotes, whitespace, and prevents double 'bot' prefixing errors.
    """
    if not token_str:
        return ""
    token = re.sub(r'[\[\]\'"\s]', '', str(token_str))
    if token.startswith("bot"):
        token = token[3:]
    return token

def parse_telegram_payload():
    raw_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_token = clean_token(raw_bot_token)
    chat_id = clean_token(os.getenv("TELEGRAM_CHAT_ID", ""))

    if not bot_token:
        print("[STAGE 1 ERROR] TELEGRAM_BOT_TOKEN is missing or invalid.")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        resp = requests.get(url, timeout=15).json()
    except Exception as e:
        print(f"[STAGE 1 ERROR] Failed to connect to Telegram API: {e}")
        sys.exit(1)

    if not resp.get("ok"):
        print(f"[STAGE 1 ERROR] Telegram API returned error: {resp}")
        sys.exit(1)

    user_caption = ""
    video_file_id = None
    media_type = None

    # Search backwards for the most recent message with /create_reel or structured data
    for result in reversed(resp.get("result", [])):
        msg = result.get("message", {})
        caption = msg.get("caption", "") or msg.get("text", "")
        
        if "/create_reel" in caption or "HOOK:" in caption or "VOICEOVER:" in caption:
            user_caption = caption
            if "video" in msg:
                video_file_id = msg["video"]["file_id"]
                media_type = "video"
                break
            elif "document" in msg and msg["document"].get("mime_type", "").startswith("video/"):
                video_file_id = msg["document"]["file_id"]
                media_type = "video"
                break
            elif "photo" in msg:
                # Select highest resolution photo
                video_file_id = msg["photo"][-1]["file_id"]
                media_type = "photo"
                break

    # Default fallback values
    hook = os.getenv("CUSTOM_HOOK", "STOP CREATING CAROUSELS MANUALLY!")
    caption_style = "energetic_yellow_highlight"
    vo_timeline = []

    # Parse user structured text
    if user_caption:
        print("[STAGE 1] Parsing custom Telegram instructions...")
        lines = user_caption.split("\n")
        
        # Simple global VO fallback parsing
        simple_vo = ""
        
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("HOOK:"):
                hook = line_str.replace("HOOK:", "").strip()
            elif line_str.startswith("CAPTION_STYLE:"):
                caption_style = line_str.replace("CAPTION_STYLE:", "").strip()
            elif line_str.startswith("VOICEOVER:"):
                simple_vo = line_str.replace("VOICEOVER:", "").strip()

        # Parse VOICEOVER_TIMELINE blocks
        if "VOICEOVER_TIMELINE:" in user_caption:
            timeline_block = user_caption.split("VOICEOVER_TIMELINE:")[-1].split("PROMPT:")[0]
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*s\s*-\s*(.+)', timeline_block)
            for match in matches:
                vo_timeline.append({
                    "start_sec": float(match[0]),
                    "text": match[1].strip()
                })
        
        # Fallback if no timeline markers specified
        if not vo_timeline and simple_vo:
            vo_timeline.append({"start_sec": 0.0, "text": simple_vo})

    if not vo_timeline:
        vo_timeline.append({
            "start_sec": 0.0, 
            "text": "Need high converting social media carousels fast? AICarousels automatically formats full posts in seconds."
        })

    payload = {
        "hook": hook,
        "caption_style": caption_style,
        "vo_timeline": vo_timeline
    }

    with open("script.json", "w") as f:
        json.dump(payload, f, indent=2)
    print("[STAGE 1] Saved payload to script.json")

    # Download raw attached file
    if video_file_id:
        file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={video_file_id}"
        file_info = requests.get(file_info_url).json()
        
        if file_info.get("ok"):
            file_path = file_info["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            
            ext = ".png" if media_type == "photo" else ".webm"
            output_filename = f"raw_desktop{ext}"
            
            print(f"[STAGE 1] Downloading raw media file ({output_filename})...")
            res = requests.get(download_url)
            with open(output_filename, "wb") as f:
                f.write(res.content)
            print("[STAGE 1] Download complete.")
    else:
        print("[STAGE 1 WARNING] No media file found attached to message. Proceeding with existing assets.")

def send_ack():
    raw_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_token = clean_token(raw_bot_token)
    chat_id = clean_token(os.getenv("TELEGRAM_CHAT_ID", ""))
    
    if not bot_token or not chat_id:
        return

    with open("script.json", "r") as f:
        data = json.load(f)

    msg = (
        "⚙️ *Media Payload & Script Parsing Complete*\n\n"
        f"📌 *Hook:* {data['hook']}\n"
        f"🎨 *Style:* {data['caption_style']}\n"
        f"🎙️ *Voiceover Clips:* {len(data['vo_timeline'])} segments synced.\n\n"
        "⚡ *Starting Stage 2 Audio Assembly & HyperFrames Render...*"
    )
    
    api_endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(api_endpoint, data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"[STAGE 1 WARNING] Failed to send ACK message: {e}")

if __name__ == "__main__":
    parse_telegram_payload()
    send_ack()
