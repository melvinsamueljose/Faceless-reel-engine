import os
import json
import re
import subprocess
import requests

def clean_token(token_str):
    token = re.sub(r'[\[\]\'"\s]', '', str(token_str))
    if "bot" in token:
        token = token.split("bot")[-1]
    return token

def generate_tts_audio(voiceover_text, output_audio="voiceover.mp3"):
    print("[STAGE 2] Generating Edge-TTS Voiceover Audio...")
    cmd = f'edge-tts --text "{voiceover_text}" --write-media {output_audio} --voice en-US-ChristopherNeural'
    subprocess.run(cmd, shell=True, check=True)

def render_hyperframes_reel():
    print("[STAGE 2] Rendering vertical Reel layout & animated captions...")
    # Executes HyperFrames HTML-to-Video Engine
    cmd = "hyperframes render template.html -o final_reel.mp4"
    subprocess.run(cmd, shell=True, check=True)

def send_final_reel():
    bot_token = clean_token(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = clean_token(os.getenv("TELEGRAM_CHAT_ID", ""))

    caption = "🚀 *Your Stitched Final Reel is Ready!*"
    api_endpoint = "https://api.telegram.org/bot" + bot_token + "/sendVideo"
    
    video_file = "final_reel.mp4" if os.path.exists("final_reel.mp4") else "raw_desktop.webm"

    print(f"[STAGE 2] Uploading final Reel ({video_file}) to Telegram...")
    with open(video_file, "rb") as vf:
        requests.post(
            api_endpoint,
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
            files={"video": vf}
        )

if __name__ == "__main__":
    if os.path.exists("script.json"):
        with open("script.json", "r") as f:
            script = json.load(f)
        
        generate_tts_audio(script.get("voiceover", ""))
        render_hyperframes_reel()
        send_final_reel()
