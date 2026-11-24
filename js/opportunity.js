(() => {
  const storageKey = "finance-ops-opportunity-v1";
  const winKey = "finance-ops-opportunity-win-checklist";

  const sample = {
    name: "Discovery — AI ops assessment",
    client: "New logo (TBD)",
    stage: "discovery",
    billing: "discovery-fixed",
    fee: 45000,
    probability: 35,
    closeDate: "",
    terms: "50-50",
    scope:
      "2–3 week discovery: current finance/ops workflow, AI deployment opportunities, recommended build vs buy. Deliverable = readout + proposal for phase 2.",
    risks:
      "Confirm whether LLM usage is billed as pass-through or absorbed. Need PO / vendor onboarding timeline before kickoff invoice.",
  };

  // Default close ~3 weeks out from "today" in local timezone.
  const defaultClose = () => {
    const d = new Date();
    d.setDate(d.getDate() + 21);
    return d.toISOString().slice(0, 10);
  };
  sample.closeDate = defaultClose();

  const money = (n) =>
    Number(n || 0).toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    });

  const moneyK = (n) => `$${Math.round(Number(n || 0) / 1000)}k`;

  const form = document.getElementById("opp-form");
  const status = document.getElementById("opp-status");
  const cashPanel = document.getElementById("cash-panel");

  const load = () => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return { ...sample };
      return { ...sample, ...JSON.parse(raw) };
    } catch {
      return { ...sample };
    }
  };

  const save = (data) => {
    localStorage.setItem(storageKey, JSON.stringify(data));
  };

  const readForm = () => {
    const fd = new FormData(form);
    return {
      name: String(fd.get("name") || "").trim(),
      client: String(fd.get("client") || "").trim(),
      stage: String(fd.get("stage") || "discovery"),
      billing: String(fd.get("billing") || "discovery-fixed"),
      fee: Number(fd.get("fee") || 0),
      probability: Number(fd.get("probability") || 0),
      closeDate: String(fd.get("closeDate") || ""),
      terms: String(fd.get("terms") || "net30"),
      scope: String(fd.get("scope") || "").trim(),
      risks: String(fd.get("risks") || "").trim(),
    };
  };

  const fillForm = (data) => {
    Object.entries(data).forEach(([key, value]) => {
      const el = form.elements.namedItem(key);
      if (el && "value" in el) el.value = value ?? "";
    });
  };

  const stageLabel = (stage) =>
    ({
      discovery: "Discovery",
      proposal: "Proposal",
      negotiation: "Negotiation",
      verbal: "Verbal commit",
      won: "Won",
      lost: "Lost",
    })[stage] || stage;

  const receiptPlan = (data) => {
    const fee = Number(data.fee) || 0;
    const close = data.closeDate ? new Date(`${data.closeDate}T12:00:00`) : null;
    const addDays = (base, days) => {
      if (!base) return null;
      const d = new Date(base);
      d.setDate(d.getDate() + days);
      return d;
    };
    const fmt = (d) =>
      d
        ? d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })
        : "TBD";

    if (data.stage === "lost") {
      return [{ label: "No receipts (lost)", amount: 0, when: "—" }];
    }

    if (data.terms === "50-50") {
      return [
        {
          label: "Kickoff invoice (50%)",
          amount: fee * 0.5,
          when: fmt(addDays(close, 7)),
          note: "Send within 48h of win; expect cash ~Net terms after invoice",
        },
        {
          label: "Completion invoice (50%)",
          amount: fee * 0.5,
          when: fmt(addDays(close, 28)),
          note: "Tie to acceptance of discovery readout",
        },
      ];
    }

    if (data.terms === "milestone") {
      return [
        {
          label: "Milestone 1",
          amount: fee * 0.4,
          when: fmt(addDays(close, 7)),
          note: "Kickoff / scoping complete",
        },
        {
          label: "Milestone 2",
          amount: fee * 0.6,
          when: fmt(addDays(close, 35)),
          note: "Final readout accepted",
        },
      ];
    }

    const netDays =
      data.terms === "net15" ? 15 : data.terms === "net45" ? 45 : 30;
    return [
      {
        label: `Single invoice · ${data.terms.toUpperCase()}`,
        amount: fee,
        when: fmt(addDays(close, 3 + netDays)),
        note: "Invoice shortly after win; cash after terms",
      },
    ];
  };

  const renderKpis = (data) => {
    const weighted =
      data.stage === "won"
        ? data.fee
        : data.stage === "lost"
          ? 0
          : (data.fee * data.probability) / 100;
    const plan = receiptPlan(data);
    const cashIn = plan.reduce((a, r) => a + r.amount, 0);

    const set = (id, text, warn) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      el.classList.toggle("is-warn", Boolean(warn));
    };

    set("kpi-fee", moneyK(data.fee));
    set("kpi-weighted", moneyK(weighted));
    set("kpi-cashin", data.stage === "lost" ? "$0" : moneyK(cashIn));
    set("kpi-stage", stageLabel(data.stage), data.stage === "discovery");
  };

  const renderCash = (data) => {
    if (!cashPanel) return;
    const plan = receiptPlan(data);
    const won = data.stage === "won";
    const lost = data.stage === "lost";

    cashPanel.innerHTML = `
      <p class="opp-cash__lead">
        ${
          lost
            ? "Opportunity marked lost — remove any tentative receipts from the 13-week."
            : won
              ? "Marked <strong>won</strong> — book these on the cash forecast and run the win checklist."
              : `At <strong>${data.probability}%</strong>, weighted pipeline is
                <strong>${money((data.fee * data.probability) / 100)}</strong>.
                Below is the receipt sketch <em>if won</em> (not weighted).`
        }
      </p>
      <div class="metrics__table-wrap" role="region" aria-label="Expected receipts if won">
        <table class="metrics__table">
          <thead>
            <tr>
              <th scope="col">Receipt</th>
              <th scope="col">Amount</th>
              <th scope="col">Target week</th>
              <th scope="col">Note</th>
            </tr>
          </thead>
          <tbody>
            ${plan
              .map(
                (row) => `
              <tr class="is-inview">
                <td>${row.label}</td>
                <td>${money(row.amount)}</td>
                <td>${row.when}</td>
                <td>${row.note || "—"}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  };

  const refresh = (data) => {
    renderKpis(data);
    renderCash(data);
  };

  let current = load();
  fillForm(current);
  refresh(current);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    current = readForm();
    save(current);
    refresh(current);
    if (status) {
      status.textContent = `Saved ${new Date().toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
      })} · local only`;
    }
  });

  form.addEventListener("change", () => {
    refresh(readForm());
  });

  document.getElementById("opp-reset")?.addEventListener("click", () => {
    const next = { ...sample, closeDate: defaultClose() };
    fillForm(next);
    save(next);
    current = next;
    refresh(next);
    if (status) status.textContent = "Reset to sample discovery card";
  });

  // Win checklist
  const checklist = document.getElementById("win-checklist");
  if (checklist) {
    const inputs = [...checklist.querySelectorAll('input[type="checkbox"]')];
    const doneEl = checklist.querySelector("[data-done]");
    const totalEl = checklist.querySelector("[data-total]");
    let saved = {};
    try {
      saved = JSON.parse(localStorage.getItem(winKey) || "{}") || {};
    } catch {
      saved = {};
    }
    const sync = () => {
      const done = inputs.filter((i) => i.checked).length;
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
          localStorage.setItem(winKey, JSON.stringify(saved));
        } catch {
          /* ignore */
        }
        sync();
      });
    });
    sync();
  }
})();
