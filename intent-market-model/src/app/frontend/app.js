const tenantIdInput = document.getElementById("tenant-id");
const companyIdInput = document.getElementById("company-id");
const tenantStatus = document.getElementById("tenant-status");
const companyStatus = document.getElementById("company-status");
const ingestStatus = document.getElementById("ingest-status");
const backtestStatus = document.getElementById("backtest-status");
const dashboardEl = document.getElementById("intent-dashboard");
const feedEl = document.getElementById("intent-feed");
const backtestEl = document.getElementById("backtest-report");
const backtestScorecard = document.getElementById("backtest-scorecard");
const backtestChart = document.getElementById("backtest-chart");
const timelineEl = document.getElementById("intent-timeline");

const setStatus = (el, text, tone = "") => {
  el.textContent = text;
  el.style.color = tone;
};

const api = async (path, options = {}) => {
  const response = await fetch(path, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }
  return response.json();
};

const renderDashboard = (items) => {
  dashboardEl.innerHTML = "";
  if (!items.length) {
    dashboardEl.innerHTML = "<p>No intents yet. Ingest signals first.</p>";
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h4>${item.intent_type}</h4>
      <p>Confidence: ${(item.confidence * 100).toFixed(0)}%</p>
      <p>${item.explanation}</p>
    `;
    dashboardEl.appendChild(card);
  });
};

const renderFeed = (items) => {
  feedEl.innerHTML = "";
  if (!items.length) {
    feedEl.innerHTML = "<p>No evidence yet. Ingest signals to see why.</p>";
    return;
  }
  items.forEach((item) => {
    const evidence = item.evidence?.[0];
    if (!evidence) return;
    const feed = document.createElement("div");
    feed.className = "feed-item";
    feed.innerHTML = `
      <span>${item.intent_type}</span>
      <p>${evidence.snippet}</p>
      <p class="tiny">Triggers: ${(evidence.triggers || []).join(", ")}</p>
    `;
    feedEl.appendChild(feed);
  });
};

const loadDashboard = async (tenantId, companyId) => {
  const data = await api(`/tenants/${tenantId}/companies/${companyId}/intents/dashboard`);
  renderDashboard(data.items || []);
  renderFeed(data.items || []);
  await loadTimeline(tenantId, companyId);
};

const ensureTenantId = () => {
  const value = tenantIdInput.value.trim();
  if (!value) {
    throw new Error("Enter a tenant id first.");
  }
  return value;
};

const ensureCompanyId = () => {
  const value = companyIdInput.value.trim();
  if (!value) {
    throw new Error("Enter a company id first.");
  }
  return value;
};

const runDemo = async () => {
  setStatus(tenantStatus, "Creating demo tenant...");
  const tenant = await api("/tenants", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "Demo Workspace" }),
  });
  tenantIdInput.value = tenant.id;
  setStatus(tenantStatus, `Tenant ready (id ${tenant.id}).`);

  setStatus(companyStatus, "Creating demo company...");
  const company = await api(`/tenants/${tenant.id}/companies/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "Acme AI", domain: "acme-ai.com" }),
  });
  companyIdInput.value = company.id;
  setStatus(companyStatus, `Company ready (id ${company.id}).`, "#2f3440");

  setStatus(ingestStatus, "Ingesting job posts...");
  await api(`/tenants/${tenant.id}/companies/ingest/${company.id}?source=mock` , { method: "POST" });
  setStatus(ingestStatus, "Ingesting filings...");
  await api(`/tenants/${tenant.id}/companies/ingest/${company.id}?source=sec_mock`, { method: "POST" });

  setStatus(ingestStatus, "Loading intent dashboard...");
  await loadDashboard(tenant.id, company.id);
  await seedOutcomes();
  await runBacktest();
  setStatus(ingestStatus, "Done.");
};

const createTenant = async () => {
  const name = document.getElementById("tenant-name").value.trim();
  setStatus(tenantStatus, "Creating tenant...");
  const tenant = await api("/tenants", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  tenantIdInput.value = tenant.id;
  setStatus(tenantStatus, `Created ${tenant.name} (id ${tenant.id}).`);
};

const loadTenant = async () => {
  const tenantId = ensureTenantId();
  setStatus(tenantStatus, `Using tenant ${tenantId}.`);
};

const createCompany = async () => {
  const tenantId = ensureTenantId();
  const name = document.getElementById("company-name").value.trim();
  const domain = document.getElementById("company-domain").value.trim();
  setStatus(companyStatus, "Creating company...");
  const company = await api(`/tenants/${tenantId}/companies/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, domain }),
  });
  companyIdInput.value = company.id;
  setStatus(companyStatus, `Created ${company.name} (id ${company.id}).`);
};

const loadCompany = async () => {
  const tenantId = ensureTenantId();
  const companyId = ensureCompanyId();
  setStatus(companyStatus, `Loading company ${companyId}...`);
  await loadDashboard(tenantId, companyId);
  setStatus(companyStatus, `Loaded company ${companyId}.`);
};

const ingestSource = async (source) => {
  const tenantId = ensureTenantId();
  const companyId = ensureCompanyId();
  setStatus(ingestStatus, `Ingesting ${source}...`);
  await api(`/tenants/${tenantId}/companies/ingest/${companyId}?source=${source}`, { method: "POST" });
  await loadDashboard(tenantId, companyId);
  setStatus(ingestStatus, `Ingested ${source}.`);
};

const runPipeline = async () => {
  const tenantId = ensureTenantId();
  setStatus(ingestStatus, "Running pipeline...");
  await api(`/tenants/${tenantId}/pipeline/run?source=mock,sec_mock`, { method: "POST" });
  if (companyIdInput.value.trim()) {
    await loadDashboard(tenantId, companyIdInput.value.trim());
  }
  setStatus(ingestStatus, "Pipeline complete.");
};

const seedOutcomes = async () => {
  const tenantId = ensureTenantId();
  const companyId = ensureCompanyId();
  setStatus(backtestStatus, "Adding sample outcomes...");
  const payloads = [
    { outcome_type: "IPO", timestamp: daysAheadIso(90), source: "demo" },
    { outcome_type: "LAYOFF", timestamp: daysAheadIso(60), source: "demo" },
    { outcome_type: "FUNDING", timestamp: daysAheadIso(30), source: "demo" },
  ];
  for (const payload of payloads) {
    await api(`/tenants/${tenantId}/companies/${companyId}/outcomes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
  setStatus(backtestStatus, "Sample outcomes added (future dates for demo).");
};

const runBacktest = async () => {
  const tenantId = ensureTenantId();
  const companyId = ensureCompanyId();
  setStatus(backtestStatus, "Running backtest...");
  await api(`/tenants/${tenantId}/companies/${companyId}/backtest/run?lookback_days=365`, {
    method: "POST",
  });
  const report = await api(`/tenants/${tenantId}/companies/${companyId}/backtest/report`);
  renderBacktest(report.metrics || []);
  setStatus(backtestStatus, "Backtest complete.");
};

const renderBacktest = (metrics) => {
  backtestEl.innerHTML = "";
  backtestScorecard.innerHTML = "";
  backtestChart.innerHTML = "";
  if (!metrics.length) {
    backtestEl.innerHTML = "<p>No backtest yet. Add outcomes and run it.</p>";
    return;
  }
  renderScorecard(metrics);
  renderChart(metrics);
  metrics.forEach((metric) => {
    const card = document.createElement("div");
    card.className = "card";
    const rate = Math.round(metric.match_rate * 100);
    const lag = metric.avg_lag_days ? `${metric.avg_lag_days.toFixed(1)} days` : "n/a";
    card.innerHTML = `
      <h4>${metric.outcome_type}</h4>
      <p>Matched: ${metric.matched}/${metric.outcomes} (${rate}%)</p>
      <p>Avg lead time: ${lag}</p>
    `;
    backtestEl.appendChild(card);
  });
};

const renderScorecard = (metrics) => {
  const totalOutcomes = metrics.reduce((sum, m) => sum + m.outcomes, 0);
  const totalMatched = metrics.reduce((sum, m) => sum + m.matched, 0);
  const matchRate = totalOutcomes ? Math.round((totalMatched / totalOutcomes) * 100) : 0;
  const avgLag = averageLag(metrics);

  const cards = [
    { title: "Outcomes checked", value: totalOutcomes },
    { title: "Matched intents", value: totalMatched },
    { title: "Match rate", value: `${matchRate}%` },
    { title: "Avg lead time", value: avgLag ? `${avgLag.toFixed(1)} days` : "n/a" },
  ];

  cards.forEach((card) => {
    const node = document.createElement("div");
    node.className = "card";
    node.innerHTML = `<h4>${card.title}</h4><p>${card.value}</p>`;
    backtestScorecard.appendChild(node);
  });
};

const renderChart = (metrics) => {
  metrics.forEach((metric) => {
    const row = document.createElement("div");
    row.className = "bar-row";
    const percent = Math.round(metric.match_rate * 100);
    row.innerHTML = `
      <div>${metric.outcome_type}</div>
      <div class="bar"><span style="width:${percent}%"></span></div>
      <div>${percent}%</div>
    `;
    backtestChart.appendChild(row);
  });
};

const averageLag = (metrics) => {
  let sum = 0;
  let count = 0;
  metrics.forEach((metric) => {
    if (metric.avg_lag_days !== null && metric.avg_lag_days !== undefined) {
      sum += metric.avg_lag_days;
      count += 1;
    }
  });
  return count ? sum / count : null;
};

const daysAgoIso = (days) => {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString();
};

const daysAheadIso = (days) => {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString();
};

const loadTimeline = async (tenantId, companyId) => {
  const data = await api(`/tenants/${tenantId}/companies/${companyId}/intents/timeline`);
  timelineEl.innerHTML = "";
  if (!data.series || !data.series.length) {
    timelineEl.innerHTML = "<p>No timeline yet. Ingest signals first.</p>";
    return;
  }
  data.series.forEach((series) => {
    const block = document.createElement("div");
    block.className = "feed-item";
    const recent = series.points.slice(-3);
    block.innerHTML = `
      <span>${series.intent_type}</span>
      <p>${recent.map((p) => `${new Date(p.timestamp).toLocaleDateString()}: ${(p.confidence * 100).toFixed(0)}%`).join("<br/>")}</p>
    `;
    timelineEl.appendChild(block);
  });
};

const bind = () => {
  document.getElementById("run-demo").addEventListener("click", () => {
    runDemo().catch((err) => setStatus(ingestStatus, err.message, "#d84845"));
  });
  document.getElementById("create-tenant").addEventListener("click", () => {
    createTenant().catch((err) => setStatus(tenantStatus, err.message, "#d84845"));
  });
  document.getElementById("load-tenant").addEventListener("click", () => {
    loadTenant().catch((err) => setStatus(tenantStatus, err.message, "#d84845"));
  });
  document.getElementById("create-company").addEventListener("click", () => {
    createCompany().catch((err) => setStatus(companyStatus, err.message, "#d84845"));
  });
  document.getElementById("load-company").addEventListener("click", () => {
    loadCompany().catch((err) => setStatus(companyStatus, err.message, "#d84845"));
  });
  document.querySelectorAll(".ingest").forEach((button) => {
    button.addEventListener("click", () => {
      ingestSource(button.dataset.source).catch((err) =>
        setStatus(ingestStatus, err.message, "#d84845")
      );
    });
  });
  document.getElementById("run-pipeline").addEventListener("click", () => {
    runPipeline().catch((err) => setStatus(ingestStatus, err.message, "#d84845"));
  });
  document.getElementById("seed-outcomes").addEventListener("click", () => {
    seedOutcomes().catch((err) => setStatus(backtestStatus, err.message, "#d84845"));
  });
  document.getElementById("run-backtest").addEventListener("click", () => {
    runBacktest().catch((err) => setStatus(backtestStatus, err.message, "#d84845"));
  });
};

bind();
