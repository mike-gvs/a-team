(function () {
  const key = "gvs-ui-theme";
  const root = document.documentElement;
  const saved = localStorage.getItem(key);
  if (saved === "dark" || saved === "light") {
    root.setAttribute("data-theme", saved);
  }
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem(key, next);
    });
  });
})();
