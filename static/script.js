const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("message");
const sendBtn = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");

function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function addTyping() {
  const div = document.createElement("div");
  div.className = "bubble bot";
  div.innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    chat.innerHTML = "";
    if (!data.history.length) {
      addBubble("system", "No memory yet — say hi to start the conversation.");
      return;
    }
    for (const msg of data.history) {
      addBubble(msg.role === "user" ? "user" : "bot", msg.content);
    }
  } catch (e) {
    addBubble("error", "Failed to load history.");
  }
}

async function sendMessage(text) {
  addBubble("user", text);
  const typing = addTyping();
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    typing.remove();
    if (!res.ok) {
      addBubble("error", data.error || "Something went wrong.");
      return;
    }
    addBubble("bot", data.reply);
  } catch (e) {
    typing.remove();
    addBubble("error", "Network error: " + e.message);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendMessage(text);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

clearBtn.addEventListener("click", async () => {
  if (!confirm("Clear all conversation memory? This cannot be undone.")) return;
  try {
    const res = await fetch("/api/clear", { method: "POST" });
    if (!res.ok) throw new Error("Clear failed");
    chat.innerHTML = "";
    addBubble("system", "Memory cleared. Starting fresh.");
  } catch (e) {
    addBubble("error", "Failed to clear memory.");
  }
});

loadHistory();
