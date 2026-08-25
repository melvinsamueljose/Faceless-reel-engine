import os
import requests

def generate_script():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY secret is not set in GitHub Secrets.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "Write a punchy, viral 15-second script for an Instagram Reel promoting an AI tool. "
        "Return ONLY the plain spoken voiceover script text with no stage directions or formatting."
    )

    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    if "choices" not in data:
        print(f"OpenRouter API Response Error: {data}")
        raise KeyError(f"OpenRouter call failed. Response payload was: {data}")

    return data["choices"][0]["message"]["content"].strip()
