(function () {
  const steps = Array.from(document.querySelectorAll(".gvs-step"));
  const tabs = Array.from(document.querySelectorAll("[data-step-tab]"));
  const prev = document.getElementById("prev-btn");
  const next = document.getElementById("next-btn");
  const finish = document.getElementById("finish-btn");
  const form = document.getElementById("setup-form");
  const adminFields = document.getElementById("admin-fields");
  const resultBox = document.getElementById("self-test-result");
  let i = 0;
  let lastStepTested = false;

  function show(n) {
    i = n;
    steps.forEach((el, idx) => el.classList.toggle("is-active", idx === i));
    tabs.forEach((el, idx) => el.classList.toggle("is-active", idx === i));
    prev.hidden = i === 0;
    next.hidden = i === steps.length - 1;
    finish.hidden = i !== steps.length - 1;
    if (i === steps.length - 1) {
      runSelfTest();
    }
  }

  function runSelfTest() {
    if (!resultBox) {
      return Promise.resolve(false);
    }
    resultBox.hidden = false;
    resultBox.className = "gvs-self-test";
    resultBox.textContent = "Running self-test…";
    return fetch("/api/setup/self-test")
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok && data.ok, data: data };
        });
      })
      .then(function (result) {
        const data = result.data || {};
        const ok = Boolean(result.ok && data.green);
        resultBox.className = "gvs-self-test " + (ok ? "ok" : "fail");
        resultBox.dataset.green = ok ? "1" : "0";
        const heading = ok ? "Self-test passed" : "Self-test failed";
        const items = (data.checks || [])
          .map(function (check) {
            return "<li>" + (check.ok ? "✓ " : "✗ ") + check.name + "</li>";
          })
          .join("");
        resultBox.innerHTML = "<p>" + heading + "</p><ul>" + items + "</ul>";
        lastStepTested = true;
        return ok;
      })
      .catch(function () {
        resultBox.className = "gvs-self-test fail";
        resultBox.textContent = "Self-test failed";
        lastStepTested = true;
        return false;
      });
  }

  document.querySelectorAll("input[name=require_login]").forEach(function (el) {
    el.addEventListener("change", function () {
      adminFields.hidden = form.require_login.value !== "on";
    });
  });

  prev.addEventListener("click", function () { show(Math.max(0, i - 1)); });
  next.addEventListener("click", function () { show(Math.min(steps.length - 1, i + 1)); });

  form.addEventListener("submit", function (event) {
    if (form.dataset.selfTestRan === "1") {
      return;
    }
    event.preventDefault();
    const proceed = function () {
      form.dataset.selfTestRan = "1";
      form.submit();
    };
    if (lastStepTested) {
      proceed();
      return;
    }
    runSelfTest().finally(proceed);
  });

  show(0);
})();
