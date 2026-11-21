(() => {
  const storageKey = "finance-ops-day1-checklist";
  const checklist = document.getElementById("day1-checklist");
  if (!checklist) return;

  const inputs = [...checklist.querySelectorAll('input[type="checkbox"]')];
  const doneEl = checklist.querySelector("[data-done]");
  const totalEl = checklist.querySelector("[data-total]");
  let saved = {};

  try {
    saved = JSON.parse(localStorage.getItem(storageKey) || "{}") || {};
  } catch {
    saved = {};
  }

  const syncProgress = () => {
    const done = inputs.filter((input) => input.checked).length;
    if (doneEl) doneEl.textContent = String(done);
    if (totalEl) totalEl.textContent = String(inputs.length);
  };

  inputs.forEach((input) => {
    const key = input.dataset.key;
    if (key && saved[key]) input.checked = true;
    input.addEventListener("change", () => {
      if (!key) return;
      saved[key] = input.checked;
      try {
        localStorage.setItem(storageKey, JSON.stringify(saved));
      } catch {
        /* ignore */
      }
      syncProgress();
    });
  });

  syncProgress();
})();
