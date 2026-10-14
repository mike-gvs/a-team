(function () {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const log = document.getElementById("chat-log");
  if (!form) return;

  function add(text, kind) {
    const el = document.createElement("div");
    el.className = "gvs-msg gvs-msg-" + kind;
    el.textContent = text;
    log.appendChild(el);
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const prompt = input.value.trim();
    if (!prompt) return;
    add(prompt, "user");
    input.value = "";
    const res = await fetch("/api/agents/inbox-clerk/messages", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await res.json();
    add(data.text || data.detail || "No reply", "agent");
  });
})();
