import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _call_groq(prompt: str) -> str | None:
    if not GROQ_API_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    for model in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]:
        try:
            res = requests.post(
                url,
                headers=headers,
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
                timeout=30
            )
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
        except requests.RequestException:
            continue
    return None


def _call_gemini(prompt: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    for model in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30
            )
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            time.sleep(0.5)
        except requests.RequestException:
            continue
    return None


def ask_ai(prompt: str) -> str:
    """Groq (Primary) -> Gemini (Fallback) Unified AI Engine."""
    reply = _call_groq(prompt)
    if reply:
        return reply
    print("🔄 Switching to Gemini backup AI...")
    reply = _call_gemini(prompt)
    return reply or "AI service temporarily unavailable."