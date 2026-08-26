import os
import sys
import json
import re
import subprocess
import requests

def clean_token(token_str):
    if not token_str:
        return ""
    token = re.sub(r'[\[\]\'"\s]', '', str(token_str))
    if token.startswith("bot"):
        token = token[3:]
    return token

def build_synced_audio(vo_timeline, output_final_audio="final_synced_vo.mp3"):
    print("[STAGE 2] Assembling synchronized voiceover track...")
    
    inputs = []
    filter_complex_parts = []
    
    for i, item in enumerate(vo_timeline):
        start_ms = int(item["start_sec"] * 1000)
        text = item["text"]
        part_filename = f"vo_part_{i}.mp3"
        
        # Generate segment TTS
        tts_cmd = f'edge-tts --text "{text}" --write-media {part_filename} --voice en-US-ChristopherNeural'
        subprocess.run(tts_cmd, shell=True, check=True)
        
        inputs.extend(["-i", part_filename])
        filter_complex_parts.append(f"[{i}:a]adelay={start_ms}|{start_ms}[a{i}]")

    concat_inputs = "".join([f"[a{i}]" for i in range(len(vo_timeline))])
    filter_complex = ";".join(filter_complex_parts) + f";{concat_inputs}amix=inputs={len(vo_timeline)}:normalize=0[aout]"
    
    ffmpeg_cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[aout]", output_final_audio]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"[STAGE 2] Synced audio generated successfully: {output_final_audio}")
    except subprocess.CalledProcessError as e:
        print(f"[STAGE 2 ERROR] Audio merging failed: {e}")
        # Fallback to single primary audio segment if filter graph fails
        if os.path.exists("vo_part_0.mp3"):
            os.rename("vo_part_0.mp3", output_final_audio)

def render_hyperframes():
    print("[STAGE 2] Executing HyperFrames HTML-to-Video Engine...")
    
    # Check if hyperframes executable exists, run build fallback if rendering natively
    cmd = "hyperframes render template.html --audio final_synced_vo.mp3 -o final_reel.mp4"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("[STAGE 2] HyperFrames rendering complete: final_reel.mp4")
    except Exception as e:
        print(f"[STAGE 2 WARNING] HyperFrames CLI execution failed ({e}). Running fallback conversion...")
        # Emergency FFmpeg fallback stitch if HyperFrames is missing environment dependencies
        input_media = "raw_desktop.webm" if os.path.exists("raw_desktop.webm") else "raw_desktop.png"
        fallback_cmd = f"ffmpeg -y -i {input_media} -i final_synced_vo.mp3 -c:v libx264 -c:a aac -shortest final_reel.mp4"
        subprocess.run(fallback_cmd, shell=True, check=True)

def dispatch_to_telegram():
    raw_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_token = clean_token(raw_bot_token)
    chat_id = clean_token(os.getenv("TELEGRAM_CHAT_ID", ""))

    if not bot_token or not chat_id:
        print("[STAGE 2 ERROR] Missing Telegram Bot credentials.")
        sys.exit(1)

    video_path = "final_reel.mp4"
    if not os.path.exists(video_path):
        video_path = "raw_desktop.webm"

    caption = "🚀 *Your Stitched HyperFrames Reel is Ready!*"
    
    # Direct endpoint string format to completely prevent InvalidSchema / markdown token injection
    api_endpoint = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    
    print(f"[STAGE 2] Dispatching video standard binary post to Telegram...")
    with open(video_path, "rb") as vf:
        resp = requests.post(
            api_endpoint,
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
            files={"video": vf},
            timeout=120
        )
    
    if resp.status_code == 200:
        print("[STAGE 2 SUCCESS] Final video sent to Telegram successfully!")
    else:
        print(f"[STAGE 2 ERROR] Telegram post failed with status code {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    if os.path.exists("script.json"):
        with open("script.json", "r") as f:
            data = json.load(f)
        
        vo_timeline = data.get("vo_timeline", [])
        build_synced_audio(vo_timeline)
        render_hyperframes()
        dispatch_to_telegram()
    else:
        print("[STAGE 2 ERROR] script.json not found. Run stage1_capture.py first.")
        sys.exit(1)
