(() => {
  const money = (n) =>
    n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

  const moneyK = (n) => `$${Math.round(n / 1000)}k`;

  // Median stage days from a sample of recent engagements (illustrative).
  const stages = [
    {
      id: "deliver",
      name: "Work delivered",
      detail: "Timesheets / milestone accepted by delivery lead",
      days: 0,
      kind: "start",
    },
    {
      id: "wip",
      name: "Ready to bill",
      detail: "WIP reviewed, expenses & AI usage coded to the job",
      days: 6,
      kind: "work-to-bill",
    },
    {
      id: "invoice",
      name: "Invoice issued",
      detail: "Draft → client-ready invoice in the billing system",
      days: 4,
      kind: "work-to-bill",
    },
    {
      id: "terms",
      name: "Sitting in terms",
      detail: "Net 30 clock; reminders start at day 25",
      days: 30,
      kind: "bill-to-cash",
    },
    {
      id: "collect",
      name: "Cash received",
      detail: "Extra lag after due date on average",
      days: 9,
      kind: "bill-to-cash",
    },
  ];

  const workToBill = stages
    .filter((s) => s.kind === "work-to-bill")
    .reduce((a, s) => a + s.days, 0);
  const billToCash = stages
    .filter((s) => s.kind === "bill-to-cash")
    .reduce((a, s) => a + s.days, 0);
  const o2cTotal = workToBill + billToCash;

  // Count-back DSO inputs (ending AR and recent billed credit sales).
  const endingAR = 412000;
  const monthlySales = [
    { month: "Oct 2026", days: 31, sales: 248000 },
    { month: "Sep 2026", days: 30, sales: 226000 },
    { month: "Aug 2026", days: 31, sales: 198000 },
  ];

  // Count-back: peel recent months from AR.
  let remaining = endingAR;
  let dso = 0;
  const usage = monthlySales.map((row) => {
    if (remaining <= 0) {
      return { ...row, used: 0, fraction: 0 };
    }
    if (remaining >= row.sales) {
      remaining -= row.sales;
      dso += row.days;
      return { ...row, used: row.sales, fraction: 1 };
    }
    const fraction = remaining / row.sales;
    const days = fraction * row.days;
    dso += days;
    const used = remaining;
    remaining = 0;
    return { ...row, used, fraction };
  });

  const dsoRounded = Math.round(dso * 10) / 10;
  const dsoTarget = 38;
  const dsoGap = Math.max(0, Math.round((dsoRounded - dsoTarget) * 10) / 10);

  const wip = [
    {
      engagement: "Northwind · RAG ops platform",
      type: "T&M",
      amount: 64000,
      daysSinceBill: 18,
      blocker: "Oct hours still in draft timesheets",
    },
    {
      engagement: "Helix · Eval harness (m2)",
      type: "Milestone",
      amount: 87500,
      daysSinceBill: 12,
      blocker: "Acceptance sign-off pending",
    },
    {
      engagement: "Atlas · Retainer (Nov)",
      type: "Retainer",
      amount: 35000,
      daysSinceBill: 9,
      blocker: "Invoice batch runs on the 15th",
    },
    {
      engagement: "Brightline · Agent pilot",
      type: "T&M",
      amount: 28500,
      daysSinceBill: 26,
      blocker: "LLM usage not yet coded to job",
    },
  ];

  const wipTotal = wip.reduce((a, r) => a + r.amount, 0);

  // Aging: Current = not yet due; 1–30+ = days past due.
  const ar = [
    {
      client: "Northwind",
      current: 120000,
      d1: 42000,
      d31: 18000,
      d61: 0,
      d90: 0,
    },
    {
      client: "Helix",
      current: 0,
      d1: 0,
      d31: 0,
      d61: 45000,
      d90: 0,
    },
    {
      client: "Atlas",
      current: 35000,
      d1: 0,
      d31: 0,
      d61: 0,
      d90: 0,
    },
    {
      client: "Brightline",
      current: 52000,
      d1: 21000,
      d31: 12000,
      d61: 8000,
      d90: 15000,
    },
    {
      client: "Cobalt Labs",
      current: 28000,
      d1: 16000,
      d31: 0,
      d61: 0,
      d90: 0,
    },
  ].map((row) => {
    const total = row.current + row.d1 + row.d31 + row.d61 + row.d90;
    const overdue = row.d1 + row.d31 + row.d61 + row.d90;
    return { ...row, total, overdue };
  });

  const overdueTotal = ar.reduce((a, r) => a + r.overdue, 0);
  const arTotal = ar.reduce((a, r) => a + r.total, 0);

  // Sanity: AR total should match endingAR used in DSO.
  // Soft check only in console for authors.
  if (Math.abs(arTotal - endingAR) > 1) {
    console.warn("AR aging total !== ending AR", arTotal, endingAR);
  }

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setText("kpi-dso", `${dsoRounded} days`);
  setText("kpi-wip", moneyK(wipTotal));
  setText("kpi-overdue", moneyK(overdueTotal));
  setText("kpi-o2c", `${o2cTotal} days`);

  const dsoEl = document.getElementById("kpi-dso");
  if (dsoEl && dsoRounded > dsoTarget) dsoEl.classList.add("is-warn");
  const overdueEl = document.getElementById("kpi-overdue");
  if (overdueEl && overdueTotal > 0) overdueEl.classList.add("is-warn");

  setText("dso-gap", `${dsoGap} days above target`);

  // Flow
  const flow = document.getElementById("o2c-flow");
  if (flow) {
    stages.forEach((stage, i) => {
      const li = document.createElement("li");
      li.className = `o2c-step o2c-step--${stage.kind}`;
      li.innerHTML = `
        <span class="o2c-step__idx">${String(i + 1).padStart(2, "0")}</span>
        <h3>${stage.name}</h3>
        <p>${stage.detail}</p>
        <p class="o2c-step__days">${
          stage.days === 0 ? "Start" : `+${stage.days}d median`
        }</p>
      `;
      flow.appendChild(li);
    });
  }

  // Stacked bar
  const bar = document.getElementById("o2c-bar");
  if (bar) {
    const segments = [
      { label: "Work → bill", days: workToBill, cls: "is-wip" },
      { label: "Bill → cash", days: billToCash, cls: "is-ar" },
    ];
    bar.innerHTML = segments
      .map((seg) => {
        const pct = (seg.days / o2cTotal) * 100;
        return `<div class="o2c-bar__seg ${seg.cls}" style="flex:${seg.days}" title="${seg.label}: ${seg.days}d">
          <span>${seg.label}</span>
          <strong>${seg.days}d</strong>
        </div>`;
      })
      .join("");
    setText(
      "o2c-bar-caption",
      `Median work→cash ${o2cTotal} days · work-to-bill ${workToBill}d · bill-to-cash ${billToCash}d (≈ DSO drivers)`
    );
  }

  // DSO math
  const math = document.getElementById("dso-math");
  if (math) {
    math.innerHTML = `
      <div><dt>Ending AR</dt><dd>${money(endingAR)}</dd></div>
      <div><dt>Count-back DSO</dt><dd>${dsoRounded} days</dd></div>
      <div><dt>Simple check</dt><dd>${Math.round(
        (endingAR / (monthlySales[0].sales / monthlySales[0].days)) * 10
      ) / 10} days <span class="dso-math__hint">(AR ÷ Oct daily sales)</span></dd></div>
    `;
  }

  const salesBody = document.querySelector("#sales-table tbody");
  if (salesBody) {
    usage.forEach((row) => {
      const tr = document.createElement("tr");
      const pct = row.fraction ? `${Math.round(row.fraction * 100)}% of month` : "—";
      tr.innerHTML = `
        <td>${row.month}</td>
        <td>${money(row.sales)}</td>
        <td>${row.used ? `${money(row.used)} · ${pct}` : "—"}</td>
      `;
      if (row.used) tr.classList.add("is-inview");
      salesBody.appendChild(tr);
    });
  }

  const wipBody = document.querySelector("#wip-table tbody");
  if (wipBody) {
    wip.forEach((row) => {
      const tr = document.createElement("tr");
      const hot = row.daysSinceBill >= 21;
      tr.innerHTML = `
        <th scope="row" class="cash-table__sticky">${row.engagement}</th>
        <td>${row.type}</td>
        <td>${money(row.amount)}</td>
        <td class="${hot ? "is-breach" : ""}">${row.daysSinceBill}</td>
        <td class="o2c-blocker">${row.blocker}</td>
      `;
      wipBody.appendChild(tr);
    });
    const total = document.createElement("tr");
    total.className = "is-strong";
    total.innerHTML = `
      <th scope="row" class="cash-table__sticky">Total unbilled WIP</th>
      <td></td>
      <td>${money(wipTotal)}</td>
      <td></td>
      <td></td>
    `;
    wipBody.appendChild(total);
  }

  const arBody = document.querySelector("#ar-table tbody");
  if (arBody) {
    const cell = (n, warn) =>
      `<td class="${warn && n > 0 ? "is-breach" : n === 0 ? "is-zero" : ""}">${
        n === 0 ? "—" : money(n)
      }</td>`;

    ar.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <th scope="row" class="cash-table__sticky">${row.client}</th>
        ${cell(row.current, false)}
        ${cell(row.d1, true)}
        ${cell(row.d31, true)}
        ${cell(row.d61, true)}
        ${cell(row.d90, true)}
        <td>${money(row.total)}</td>
        <td class="${row.overdue ? "is-breach" : ""}">${
          row.overdue ? money(row.overdue) : "—"
        }</td>
      `;
      arBody.appendChild(tr);
    });

    const total = document.createElement("tr");
    total.className = "is-strong";
    const sum = (key) => ar.reduce((a, r) => a + r[key], 0);
    total.innerHTML = `
      <th scope="row" class="cash-table__sticky">Total</th>
      <td>${money(sum("current"))}</td>
      <td>${money(sum("d1"))}</td>
      <td>${money(sum("d31"))}</td>
      <td>${money(sum("d61"))}</td>
      <td>${money(sum("d90"))}</td>
      <td>${money(arTotal)}</td>
      <td class="is-breach">${money(overdueTotal)}</td>
    `;
    arBody.appendChild(total);
  }

  setText(
    "ar-caption",
    `Ending AR ${money(arTotal)} · overdue ${money(
      overdueTotal
    )} (${Math.round((overdueTotal / arTotal) * 100)}%) · Net 30 terms on most contracts`
  );
})();
