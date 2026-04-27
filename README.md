# Personal Chatbot with Memory

A small web chatbot that **remembers** the conversation across turns — because raw LLM APIs are stateless. The full conversation history is persisted to a local JSON file and replayed back to the model on every turn, so the assistant stays in context.

Powered by [Anthropic Claude](https://www.anthropic.com/) + Flask, with a clean dark-mode UI and a one-click **Clear Memory** button to reset the session.

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
| LLM      | Anthropic Claude (`claude-sonnet-4-5` by default) |
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

Open `.env` and paste your key from [console.anthropic.com](https://console.anthropic.com/):

```
ANTHROPIC_API_KEY=sk-ant-...
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

| Variable            | Default              | Purpose                           |
| ------------------- | -------------------- | --------------------------------- |
| `ANTHROPIC_API_KEY` | _(required)_         | Your Claude API key               |
| `CHAT_MODEL`        | `claude-sonnet-4-5`  | Any Claude model ID               |
| `MAX_TURNS`         | `40`                 | Max history messages sent per call|

## License

MIT
