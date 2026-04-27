# Personal Chatbot with Memory

A small web chatbot that **remembers** the conversation across turns — because raw LLM APIs are stateless. The full conversation history is persisted to a local JSON file and replayed back to the model on every turn, so the assistant stays in context.

Powered by [Google Gemini](https://aistudio.google.com/) (free, no credit card needed) + Flask, with a clean dark-mode UI and a one-click **Clear Memory** button to reset the session.

## Features

- Persistent conversation memory in `memory.json` (swap for Redis if you scale up)
- Full history sent back to the LLM on each turn so it remembers earlier messages
- Configurable history window (`MAX_TURNS`) to keep prompts bounded
- One-click **Clear Memory** button with a confirm dialog
- Reloads previous chat on page refresh
- Minimal, dependency-light stack (Flask + vanilla JS, no frontend build)

## Stack

| Layer    | Tech                                |
| -------- | ----------------------------------- |
| Backend  | Python 3.10+, Flask                 |
| LLM      | Google Gemini (`gemini-1.5-flash` by default — free tier) |
| Storage  | Local JSON file (`memory.json`)     |
| Frontend | HTML + CSS + vanilla JavaScript     |

## Getting Started

### 1. Clone & install

```bash
git clone https://github.com/Hari-Vignesh214/personal-chatbot.git
cd personal-chatbot
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Add your API key

```bash
cp .env.example .env
```

Get a **free** key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — just sign in with a Google account, click *Create API key*, copy it. No credit card required. Then open `.env` and paste it:

```
GOOGLE_API_KEY=your-key-here
```

### 3. Run

```bash
python app.py
```

Visit **http://127.0.0.1:5000** and start chatting.

## How the memory works

1. Every user message is appended to `memory.json` as `{role, content}`.
2. Before each call, the last `MAX_TURNS` messages are loaded and sent as `messages=[...]` to Claude.
3. The assistant's reply is appended to the same file.
4. **Clear Memory** writes an empty array back to `memory.json`.

That's it — there's no vector DB, no summarization. Simple full-history replay, which works great for short and medium conversations.

## Project structure

```
personal-chatbot/
├── app.py              # Flask backend (chat, clear, history endpoints)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```

## Swapping JSON for Redis

To use Redis instead of JSON, replace `load_memory` and `save_memory` in `app.py`:

```python
import redis, json
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
KEY = "chat:default"

def load_memory():
    raw = r.get(KEY)
    return json.loads(raw) if raw else []

def save_memory(history):
    r.set(KEY, json.dumps(history))
```

For multi-user support, key by session/user ID instead of a single `KEY`.

## Configuration

Override defaults via `.env`:

| Variable          | Default              | Purpose                           |
| ----------------- | -------------------- | --------------------------------- |
| `GOOGLE_API_KEY`  | _(required)_         | Your Gemini API key (free)        |
| `CHAT_MODEL`      | `gemini-1.5-flash`   | Any Gemini model ID               |
| `MAX_TURNS`       | `40`                 | Max history messages sent per call|

## Other free LLM options

If you'd rather use a different free provider, swap the LLM call in `app.py`:

- **[Groq](https://console.groq.com/keys)** — fast inference of open models (Llama 3.3, Mixtral). Free, no credit card.
- **[OpenRouter](https://openrouter.ai/)** — has a `:free` tier on several models.
- **[Ollama](https://ollama.com/)** — run models entirely on your own machine, no API needed.

## License

MIT
