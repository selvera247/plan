(() => {
  const money = (n) => {
    const abs = Math.abs(n);
    const formatted = abs.toLocaleString("en-US", {
      maximumFractionDigits: 0,
    });
    return n < 0 ? `(${formatted})` : formatted;
  };

  const moneyK = (n) => {
    const k = n / 1000;
    const sign = k < 0 ? "-" : "";
    return `${sign}$${Math.abs(k).toFixed(0)}k`;
  };

  // Week endings (Fridays) — illustrative sample as of week of Nov 10, 2026.
  const weeks = [
    "Nov 14",
    "Nov 21",
    "Nov 28",
    "Dec 5",
    "Dec 12",
    "Dec 19",
    "Dec 26",
    "Jan 2",
    "Jan 9",
    "Jan 16",
    "Jan 23",
    "Jan 30",
    "Feb 6",
  ];

  const openingCash = 485000;
  const buffer = 250000;

  // Tuned so cash gets tight under the buffer on a few weeks, then recovers —
  // the point of the artifact is to see those weeks before they hit.
  const lines = [
    {
      id: "ar-northwind",
      section: "in",
      label: "Collections · Northwind (T&M)",
      values: [95000, 0, 72000, 0, 88000, 0, 65000, 0, 78000, 0, 70000, 0, 82000],
    },
    {
      id: "ar-helix",
      section: "in",
      label: "Collections · Helix (milestone)",
      values: [0, 0, 0, 0, 175000, 0, 0, 0, 0, 0, 0, 0, 90000],
    },
    {
      id: "ar-retain",
      section: "in",
      label: "Retainer · Atlas monthly",
      values: [0, 0, 35000, 0, 0, 0, 35000, 0, 0, 0, 35000, 0, 0],
    },
    {
      id: "ar-other",
      section: "in",
      label: "Other receipts / late AR",
      values: [22000, 18000, 12000, 28000, 8000, 20000, 15000, 14000, 18000, 12000, 16000, 10000, 14000],
    },
    {
      id: "payroll",
      section: "out",
      label: "Payroll & benefits",
      values: [98000, 0, 98000, 0, 98000, 0, 98000, 0, 102000, 0, 102000, 0, 102000],
    },
    {
      id: "contractors",
      section: "out",
      label: "Contractors",
      values: [18000, 16000, 20000, 15000, 18000, 14000, 12000, 10000, 28000, 32000, 26000, 18000, 15000],
    },
    {
      id: "ai",
      section: "out",
      label: "LLM / API / cloud (AI delivery)",
      values: [8000, 9000, 8500, 10000, 11000, 10000, 7000, 8000, 28000, 32000, 22000, 12000, 9000],
    },
    {
      id: "saas",
      section: "out",
      label: "Software & tools",
      values: [5000, 3500, 3500, 14000, 3500, 3500, 3500, 3500, 3500, 3500, 3500, 14000, 3500],
    },
    {
      id: "ops",
      section: "out",
      label: "Rent, ops, insurance",
      values: [0, 0, 22000, 0, 0, 0, 22000, 0, 0, 0, 22000, 0, 0],
    },
    {
      id: "tax",
      section: "out",
      label: "Tax / estimated payments",
      values: [0, 0, 0, 38000, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {
      id: "other-ap",
      section: "out",
      label: "Other AP & expenses",
      values: [6000, 5000, 7000, 5000, 6000, 9000, 5000, 4000, 7000, 6000, 5000, 4500, 5000],
    },
  ];

  const sumSection = (section, weekIndex) =>
    lines
      .filter((line) => line.section === section)
      .reduce((acc, line) => acc + line.values[weekIndex], 0);

  const ending = [];
  let cursor = openingCash;
  for (let w = 0; w < weeks.length; w += 1) {
    const inflow = sumSection("in", w);
    const outflow = sumSection("out", w);
    cursor = cursor + inflow - outflow;
    ending.push(cursor);
  }

  const trough = Math.min(...ending);
  const troughWeek = weeks[ending.indexOf(trough)];
  const breaches = ending.filter((v) => v < buffer).length;

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setText("kpi-opening", moneyK(openingCash));
  setText("kpi-trough", `${moneyK(trough)} · ${troughWeek}`);
  setText("kpi-buffer", moneyK(buffer));
  setText("kpi-breach", breaches === 0 ? "None" : `${breaches} of 13`);
  const breachEl = document.getElementById("kpi-breach");
  if (breachEl && breaches > 0) breachEl.classList.add("is-warn");
  const troughEl = document.getElementById("kpi-trough");
  if (troughEl && trough < buffer) troughEl.classList.add("is-warn");

  const table = document.getElementById("cash-table");
  if (table) {
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");

    const headRow = document.createElement("tr");
    headRow.innerHTML = `<th scope="col" class="cash-table__sticky">Line item</th>${weeks
      .map((w, i) => `<th scope="col">W${i + 1}<span>${w}</span></th>`)
      .join("")}`;
    thead.appendChild(headRow);

    const addRow = (label, values, opts = {}) => {
      const tr = document.createElement("tr");
      if (opts.section) tr.classList.add(`is-${opts.section}`);
      if (opts.strong) tr.classList.add("is-strong");
      if (opts.muted) tr.classList.add("is-muted");
      const cells = values
        .map((v) => {
          const cls = [
            v < 0 ? "is-neg" : "",
            opts.warnBelow != null && v < opts.warnBelow ? "is-breach" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const shown = opts.blankZero && v === 0 ? "—" : money(v);
          return `<td class="${cls}">${shown}</td>`;
        })
        .join("");
      tr.innerHTML = `<th scope="row" class="cash-table__sticky">${label}</th>${cells}`;
      tbody.appendChild(tr);
    };

    addRow(
      "Opening cash",
      weeks.map((_, i) => (i === 0 ? openingCash : ending[i - 1])),
      { strong: true }
    );

    addRow("Cash receipts", weeks.map((_, i) => sumSection("in", i)), {
      section: "in",
      strong: true,
    });
    lines
      .filter((l) => l.section === "in")
      .forEach((line) =>
        addRow(line.label, line.values, {
          section: "in",
          muted: true,
          blankZero: true,
        })
      );

    addRow("Cash disbursements", weeks.map((_, i) => -sumSection("out", i)), {
      section: "out",
      strong: true,
    });
    lines
      .filter((l) => l.section === "out")
      .forEach((line) =>
        addRow(
          line.label,
          line.values.map((v) => -v),
          { section: "out", muted: true, blankZero: true }
        )
      );

    addRow(
      "Net weekly cash",
      weeks.map((_, i) => sumSection("in", i) - sumSection("out", i)),
      { strong: true }
    );
    addRow("Ending cash", ending, { strong: true, warnBelow: buffer });
    addRow(
      "vs $250k buffer",
      ending.map((v) => v - buffer),
      { muted: true }
    );
  }

  const svg = document.getElementById("cash-spark");
  if (svg) {
    const W = 720;
    const H = 220;
    const pad = { t: 24, r: 16, b: 36, l: 52 };
    const plotW = W - pad.l - pad.r;
    const plotH = H - pad.t - pad.b;
    const minY = Math.min(buffer * 0.85, ...ending) * 0.95;
    const maxY = Math.max(...ending, buffer) * 1.06;
    const xAt = (i) => pad.l + (i / (ending.length - 1)) * plotW;
    const yAt = (v) => pad.t + ((maxY - v) / (maxY - minY)) * plotH;

    const linePath = ending
      .map(
        (v, i) =>
          `${i === 0 ? "M" : "L"}${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`
      )
      .join(" ");

    const areaPath = `${linePath} L${xAt(ending.length - 1).toFixed(1)},${(
      pad.t + plotH
    ).toFixed(1)} L${xAt(0).toFixed(1)},${(pad.t + plotH).toFixed(1)} Z`;

    const bufferY = yAt(buffer);
    const ticks = [0, 3, 6, 9, 12];

    svg.innerHTML = `
      <defs>
        <linearGradient id="cashFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0b6a5a" stop-opacity="0.2"/>
          <stop offset="100%" stop-color="#0b6a5a" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <line x1="${pad.l}" y1="${bufferY}" x2="${W - pad.r}" y2="${bufferY}" class="chart-buffer"/>
      <text x="${W - pad.r}" y="${bufferY - 6}" text-anchor="end" class="chart-buffer-label">Buffer ${moneyK(buffer)}</text>
      <path d="${areaPath}" fill="url(#cashFill)"/>
      <path d="${linePath}" class="chart-line"/>
      ${ending
        .map((v, i) => {
          const breach = v < buffer;
          return `<circle cx="${xAt(i)}" cy="${yAt(v)}" r="3.5" class="chart-dot${
            breach ? " is-breach" : ""
          }"/>`;
        })
        .join("")}
      ${ticks
        .map((i) => {
          return `<text x="${xAt(i)}" y="${H - 10}" text-anchor="middle" class="chart-axis">W${
            i + 1
          }</text>`;
        })
        .join("")}
      <text x="${pad.l - 8}" y="${yAt(maxY) + 4}" text-anchor="end" class="chart-axis">${moneyK(
        Math.round(maxY / 1000) * 1000
      )}</text>
      <text x="${pad.l - 8}" y="${yAt(Math.min(...ending)) + 4}" text-anchor="end" class="chart-axis">${moneyK(
        Math.round(Math.min(...ending) / 1000) * 1000
      )}</text>
    `;
  }
})();
