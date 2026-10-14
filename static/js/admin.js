(function () {
  const userForm = document.getElementById("user-form");
  const keyForm = document.getElementById("key-form");
  const keyOnce = document.getElementById("key-once");

  if (userForm) {
    userForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      const body = Object.fromEntries(new FormData(userForm).entries());
      const res = await fetch("/api/admin/users", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) location.reload();
      else alert((await res.json()).detail || "Could not add user");
    });
  }

  if (keyForm) {
    keyForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      const body = Object.fromEntries(new FormData(keyForm).entries());
      const res = await fetch("/api/admin/api-keys", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        keyOnce.hidden = false;
        keyOnce.textContent = "Copy this key now; it is not shown again: " + data.key;
      } else {
        alert(data.detail || "Could not create key");
      }
    });
  }
})();
