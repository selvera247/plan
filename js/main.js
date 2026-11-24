(() => {
  const storageKey = "finance-ops-30-checklist";

  const checklist = document.getElementById("checklist-30");
  if (checklist) {
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
          /* ignore quota / private mode */
        }
        syncProgress();
      });
    });

    syncProgress();
  }

  const phaseSections = [...document.querySelectorAll(".phase[data-phase]")];
  const railLinks = [...document.querySelectorAll(".phase-rail a[data-phase]")];

  const setActivePhase = (id) => {
    railLinks.forEach((link) => {
      link.classList.toggle("is-active", link.dataset.phase === id);
    });
  };

  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-inview");
          revealObserver.unobserve(entry.target);
        });
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" }
    );

    document
      .querySelectorAll(
        ".phase, .checklist, .metrics__table tbody tr, .risk-list li"
      )
      .forEach((el) => revealObserver.observe(el));

    const spyObserver = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.dataset?.phase) {
          setActivePhase(visible.target.dataset.phase);
        }
      },
      { threshold: [0.25, 0.45, 0.65], rootMargin: "-20% 0px -45% 0px" }
    );

    phaseSections.forEach((section) => spyObserver.observe(section));
  } else {
    document
      .querySelectorAll(
        ".phase, .checklist, .metrics__table tbody tr, .risk-list li"
      )
      .forEach((el) => el.classList.add("is-inview"));
    if (phaseSections[0]) setActivePhase(phaseSections[0].dataset.phase);
  }
})();
