const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("message");
const sendBtn = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");
const fileInput = document.getElementById("file-input");
const pendingEl = document.getElementById("pending-attachments");

let pendingFiles = [];

function fileChip(name, onRemove) {
  const chip = document.createElement("span");
  chip.className = "chip";
  const label = document.createElement("span");
  label.className = "name";
  label.textContent = `📄 ${name}`;
  chip.appendChild(label);
  if (onRemove) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "×";
    btn.title = "Remove";
    btn.onclick = onRemove;
    chip.appendChild(btn);
  }
  return chip;
}

function renderPending() {
  pendingEl.innerHTML = "";
  pendingFiles.forEach((f, i) => {
    pendingEl.appendChild(
      fileChip(f.name, () => {
        pendingFiles.splice(i, 1);
        renderPending();
      })
    );
  });
}

function addBubble(role, text, attachmentNames) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  if (attachmentNames && attachmentNames.length) {
    const wrap = document.createElement("div");
    wrap.className = "attachments";
    attachmentNames.forEach((n) => wrap.appendChild(fileChip(n)));
    div.appendChild(wrap);
  }
  if (text) {
    const p = document.createElement("div");
    p.textContent = text;
    div.appendChild(p);
  }
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

function addSystem(text) {
  const div = document.createElement("div");
  div.className = "bubble system";
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    chat.innerHTML = "";
    if (!data.history.length) {
      addSystem("No memory yet — say hi or attach a doc to start.");
      return;
    }
    for (const msg of data.history) {
      const role = msg.role === "user" ? "user" : "bot";
      const names = (msg.attachments || []).map((a) => a.name);
      addBubble(role, msg.content, names);
    }
  } catch (e) {
    addBubble("error", "Failed to load history.");
  }
}

async function sendMessage(text, files) {
  const fileNames = files.map((f) => f.name);
  addBubble("user", text, fileNames);
  const typing = addTyping();
  sendBtn.disabled = true;

  try {
    let res;
    if (files.length === 0) {
      res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
    } else {
      const fd = new FormData();
      fd.append("message", text);
      files.forEach((f) => fd.append("files", f));
      res = await fetch("/api/chat", { method: "POST", body: fd });
    }
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

fileInput.addEventListener("change", () => {
  pendingFiles = [...pendingFiles, ...Array.from(fileInput.files)];
  fileInput.value = "";
  renderPending();
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text && pendingFiles.length === 0) return;
  const files = pendingFiles;
  pendingFiles = [];
  renderPending();
  input.value = "";
  sendMessage(text, files);
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
    addSystem("Memory cleared. Starting fresh.");
  } catch (e) {
    addBubble("error", "Failed to clear memory.");
  }
});

loadHistory();
