(function () {
  const steps = Array.from(document.querySelectorAll(".gvs-step"));
  const tabs = Array.from(document.querySelectorAll("[data-step-tab]"));
  const prev = document.getElementById("prev-btn");
  const next = document.getElementById("next-btn");
  const finish = document.getElementById("finish-btn");
  const form = document.getElementById("setup-form");
  const adminFields = document.getElementById("admin-fields");
  let i = 0;

  function show(n) {
    i = n;
    steps.forEach((el, idx) => el.classList.toggle("is-active", idx === i));
    tabs.forEach((el, idx) => el.classList.toggle("is-active", idx === i));
    prev.hidden = i === 0;
    next.hidden = i === steps.length - 1;
    finish.hidden = i !== steps.length - 1;
  }

  document.querySelectorAll("input[name=require_login]").forEach(function (el) {
    el.addEventListener("change", function () {
      adminFields.hidden = form.require_login.value !== "on";
    });
  });

  prev.addEventListener("click", function () { show(Math.max(0, i - 1)); });
  next.addEventListener("click", function () { show(Math.min(steps.length - 1, i + 1)); });
  show(0);
})();
