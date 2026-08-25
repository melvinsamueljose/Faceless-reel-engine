import os
import asyncio

async def main():
    # 1. Force-create output directory immediately
    os.makedirs("output", exist_ok=True)

    print("[1/4] Recording screen...")
    # Make sure your Playwright recording saves to "output/demo.webm" or "output/demo.mp4"
    # await page.video.path() or custom video save path here

    print("[2/4] Generating script...")
    script = generate_script()

    print("[3/4] Generating voiceover...")
    # Save TTS voiceover directly into the output directory
    # e.g., await generate_voiceover(script, "output/voice.mp3")

    print("[4/4] Asset generation complete.")

if __name__ == "__main__":
    asyncio.run(main())
