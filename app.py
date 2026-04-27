import json
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

MEMORY_FILE = Path(__file__).parent / "memory.json"
MODEL = os.environ.get("CHAT_MODEL", "gemini-1.5-flash")
MAX_TURNS = int(os.environ.get("MAX_TURNS", "40"))
SYSTEM_PROMPT = (
    "You are a helpful, friendly personal assistant. "
    "You have access to the full conversation history and should use it "
    "to give consistent, context-aware answers. Refer back to earlier "
    "messages naturally when relevant."
)

model = genai.GenerativeModel(
    model_name=MODEL,
    system_instruction=SYSTEM_PROMPT,
)


def to_gemini(history):
    return [
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": m["content"]}],
        }
        for m in history
    ]


def load_memory():
    if not MEMORY_FILE.exists():
        return []
    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_memory(history):
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify({"history": load_memory()})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    history = load_memory()
    history.append({"role": "user", "content": user_message})

    # Trim to last MAX_TURNS messages so the prompt stays bounded.
    context = history[-MAX_TURNS:]

    try:
        response = model.generate_content(to_gemini(context))
        reply = response.text
    except Exception as e:
        # Roll back the user message on failure so retry doesn't duplicate.
        history.pop()
        save_memory(history)
        return jsonify({"error": f"LLM request failed: {e}"}), 502

    history.append({"role": "assistant", "content": reply})
    save_memory(history)
    return jsonify({"reply": reply})


@app.route("/api/clear", methods=["POST"])
def clear():
    save_memory([])
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
