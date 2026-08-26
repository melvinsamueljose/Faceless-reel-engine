import os
import sys
import json
import asyncio
import subprocess
import requests
import edge_tts

async def generate_voiceover(text, output_file="voiceover.mp3"):
    communicate = edge_tts.Communicate(text, voice="en-US-ChristopherNeural", rate="+15%")
    await communicate.save(output_file)
    print(f"[AUDIO] Generated voiceover: {output_file}")

def get_audio_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return float(res.stdout.strip())

def compile_hyperframe_composition(hook_text, duration):
    with open("template.html", "r") as f:
        html = f.read()

    html = html.replace("{{HOOK_TEXT}}", hook_text)
    html = html.replace("{{DURATION}}", str(duration))

    with open("composition.html", "w") as f:
        f.write(html)

    print("[HYPERFRAMES] Rendering composition.html via headless Chrome engine...")
    render_cmd = ["npx", "hyperframes", "render", "composition.html", "--output", "final_reel.mp4"]
    subprocess.run(render_cmd, check=True)

def deliver_to_telegram(video_path):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip(" '\"[]")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip(" '\"[]")

    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/sendVideo"
    caption = "🔥 *Reel Rendered via OpenCode & HyperFrames!*"
    
    with open(video_path, "rb") as vf:
        requests.post(url, data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}, files={"video": vf})
    print("[TELEGRAM] Final Reel sent to your chat.")

async def main():
    with open("script.json") as f:
        script_data = json.load(f)

    await generate_voiceover(script_data["voiceover"])
    duration = get_audio_duration("voiceover.mp3") + 0.5
    
    compile_hyperframe_composition(script_data["hook"], duration)
    deliver_to_telegram("final_reel.mp4")

if __name__ == "__main__":
    asyncio.run(main())
