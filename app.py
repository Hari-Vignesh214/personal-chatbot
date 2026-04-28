import json
import os
from io import BytesIO
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pypdf
import docx as python_docx

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload cap
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

MEMORY_FILE = Path(__file__).parent / "memory.json"
MODEL = os.environ.get("CHAT_MODEL", "gemini-2.5-flash")
MAX_TURNS = int(os.environ.get("MAX_TURNS", "40"))
PER_FILE_TEXT_LIMIT = int(os.environ.get("PER_FILE_TEXT_LIMIT", "200000"))  # chars
SYSTEM_PROMPT = (
    "You are a helpful, friendly personal assistant. "
    "You have access to the full conversation history and should use it "
    "to give consistent, context-aware answers. Refer back to earlier "
    "messages naturally when relevant. The user may attach files; their "
    "extracted text is included in the conversation between [Attached file: NAME] "
    "and [End of NAME] markers — treat that content as context the user shared."
)

TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".log", ".yaml", ".yml",
    ".xml", ".html", ".htm", ".css", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php",
    ".sh", ".bat", ".sql", ".ini", ".cfg", ".toml",
}


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in TEXT_EXTS:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")
    if ext == ".pdf":
        reader = pypdf.PdfReader(BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if ext == ".docx":
        doc = python_docx.Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    raise ValueError(
        f"Unsupported file type '{ext}'. Supported: .pdf, .docx, and text-like files."
    )


def message_to_text(msg: dict) -> str:
    """Flatten a stored message (with optional attachments) into a single string for Gemini."""
    blocks = []
    for att in msg.get("attachments") or []:
        blocks.append(
            f"[Attached file: {att['name']}]\n{att['text']}\n[End of {att['name']}]"
        )
    if msg.get("content"):
        blocks.append(msg["content"])
    return "\n\n".join(blocks) if blocks else (msg.get("content") or "")


def to_gemini(history):
    return [
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": message_to_text(m)}],
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
    # Strip large attachment bodies from the response — UI only needs filenames.
    history = load_memory()
    redacted = []
    for m in history:
        if m.get("attachments"):
            m = {**m, "attachments": [{"name": a["name"]} for a in m["attachments"]]}
        redacted.append(m)
    return jsonify({"history": redacted})


@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = ""
    attachments = []

    if request.content_type and request.content_type.startswith("multipart/"):
        user_message = (request.form.get("message") or "").strip()
        for f in request.files.getlist("files"):
            if not f.filename:
                continue
            data = f.read()
            try:
                text = extract_text(f.filename, data)
            except Exception as e:
                return jsonify({"error": f"Could not read '{f.filename}': {e}"}), 400
            if len(text) > PER_FILE_TEXT_LIMIT:
                text = text[:PER_FILE_TEXT_LIMIT] + "\n\n[truncated]"
            attachments.append({"name": f.filename, "text": text})
    else:
        body = request.get_json(silent=True) or {}
        user_message = (body.get("message") or "").strip()

    if not user_message and not attachments:
        return jsonify({"error": "Message or attachment required."}), 400

    history = load_memory()
    msg = {"role": "user", "content": user_message}
    if attachments:
        msg["attachments"] = attachments
    history.append(msg)

    # Trim to last MAX_TURNS messages so the prompt stays bounded.
    context = history[-MAX_TURNS:]

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=to_gemini(context),
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        reply = response.text
    except Exception as e:
        history.pop()
        save_memory(history)
        return jsonify({"error": f"LLM request failed: {e}"}), 502

    history.append({"role": "assistant", "content": reply})
    save_memory(history)
    return jsonify({
        "reply": reply,
        "attachments": [{"name": a["name"]} for a in attachments],
    })


@app.route("/api/clear", methods=["POST"])
def clear():
    save_memory([])
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
