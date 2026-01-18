const tenantIdInput = document.getElementById("tenant-id");
const companyIdInput = document.getElementById("company-id");
const apiKeyInput = document.getElementById("api-key");
const apiKeyStatus = document.getElementById("api-key-status");
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
const backtestPortfolioSummary = document.getElementById("backtest-portfolio-summary");
const backtestPortfolioTable = document.getElementById("backtest-portfolio-table");
const watchlistTable = document.getElementById("watchlist-table");
const readinessTimeline = document.getElementById("readiness-timeline");
const explainPanel = document.getElementById("explain-panel");

const setStatus = (el, text, tone = "") => {
  el.textContent = text;
  el.style.color = tone;
};

const getApiKey = () => {
  return apiKeyInput.value.trim() || localStorage.getItem("apiKey") || "";
};

const saveApiKey = (value, tenantId = null) => {
  const trimmed = value.trim();
  if (trimmed) {
    localStorage.setItem("apiKey", trimmed);
    if (tenantId) {
      localStorage.setItem("apiKeyTenantId", String(tenantId));
    }
  } else {
    localStorage.removeItem("apiKey");
    localStorage.removeItem("apiKeyTenantId");
  }
  apiKeyInput.value = trimmed;
};

const api = async (path, options = {}) => {
  const headers = { ...(options.headers || {}) };
  const apiKey = getApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  const response = await fetch(path, { ...options, headers });
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
    const triggers = evidence.triggers || [];
    const triggerLine = triggers.length
      ? `Triggers: ${triggers.join(", ")}`
      : "No explicit rule hits; drift-based signal.";
    feed.innerHTML = `
      <span>${item.intent_type}</span>
      <p>${evidence.snippet}</p>
      <p class="tiny">${triggerLine}</p>
    `;
    feedEl.appendChild(feed);
  });
};

const loadDashboard = async (tenantId, companyId) => {
  const data = await api(`/tenants/${tenantId}/companies/${companyId}/intents/dashboard`);
  renderDashboard(data.items || []);
  renderFeed(data.items || []);
  await loadTimeline(tenantId, companyId);
  await loadReadinessTimeline(tenantId, companyId);
  await loadExplainability(tenantId, companyId);
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

  setStatus(apiKeyStatus, "Creating API key...");
  const apiKey = await api(`/tenants/${tenant.id}/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "demo-key", rate_limit_per_min: 120 }),
  });
  saveApiKey(apiKey.key, tenant.id);
  setStatus(apiKeyStatus, "API key saved for this browser.");

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
  await loadWatchlist(tenant.id);
  await loadBacktestPortfolio(tenant.id);
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
  await generateApiKey();
};

const loadTenant = async () => {
  const tenantId = ensureTenantId();
  const storedTenant = localStorage.getItem("apiKeyTenantId");
  if (storedTenant && storedTenant !== tenantId) {
    setStatus(
      tenantStatus,
      `API key belongs to tenant ${storedTenant}. Generate a new key for tenant ${tenantId}.`,
      "#d84845"
    );
    return;
  }
  setStatus(tenantStatus, `Using tenant ${tenantId}.`);
  await loadWatchlist(tenantId);
  await loadBacktestPortfolio(tenantId);
};

const generateApiKey = async () => {
  const tenantId = ensureTenantId();
  setStatus(apiKeyStatus, "Creating API key...");
  const apiKey = await api(`/tenants/${tenantId}/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "browser-key", rate_limit_per_min: 120 }),
  });
  saveApiKey(apiKey.key, tenantId);
  setStatus(apiKeyStatus, "API key saved for this browser.");
};

const createCompany = async () => {
  const tenantId = ensureTenantId();
  const name = document.getElementById("company-name").value.trim();
  const domain = document.getElementById("company-domain").value.trim();
  const greenhouseBoard = document.getElementById("company-greenhouse").value.trim();
  setStatus(companyStatus, "Creating company...");
  const company = await api(`/tenants/${tenantId}/companies/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      domain,
      greenhouse_board: greenhouseBoard || null,
    }),
  });
  companyIdInput.value = company.id;
  setStatus(companyStatus, `Created ${company.name} (id ${company.id}).`);
};

const loadCompany = async () => {
  const tenantId = ensureTenantId();
  const companyId = ensureCompanyId();
  setStatus(companyStatus, `Loading company ${companyId}...`);
  await loadDashboard(tenantId, companyId);
  await loadWatchlist(tenantId);
  setStatus(companyStatus, `Loaded company ${companyId}.`);
};

const ingestSource = async (source) => {
  const tenantId = ensureTenantId();
  const companyId = ensureCompanyId();
  setStatus(ingestStatus, `Ingesting ${source}...`);
  await api(`/tenants/${tenantId}/companies/ingest/${companyId}?source=${source}`, { method: "POST" });
  await loadDashboard(tenantId, companyId);
  await loadWatchlist(tenantId);
  setStatus(ingestStatus, `Ingested ${source}.`);
};

const runPipeline = async () => {
  const tenantId = ensureTenantId();
  setStatus(ingestStatus, "Running pipeline...");
  await api(`/tenants/${tenantId}/pipeline/run?source=mock,sec_mock`, { method: "POST" });
  if (companyIdInput.value.trim()) {
    await loadDashboard(tenantId, companyIdInput.value.trim());
  }
  await loadWatchlist(tenantId);
  setStatus(ingestStatus, "Pipeline complete.");
};

const seedOutcomes = async () => {
  const tenantId = ensureTenantId();
  const companyId = ensureCompanyId();
  setStatus(backtestStatus, "Adding sample outcomes...");
  let baseDate = new Date();
  try {
    const signals = await api(`/tenants/${tenantId}/companies/${companyId}/signals/recent`);
    if (signals && signals.length) {
      baseDate = new Date(signals[0].timestamp);
    }
  } catch (err) {
    baseDate = new Date();
  }
  const baseIso = (days) => {
    const date = new Date(baseDate);
    date.setUTCDate(date.getUTCDate() + days);
    return date.toISOString();
  };
  const payloads = [
    { outcome_type: "IPO", timestamp: baseIso(90), source: "demo" },
    { outcome_type: "LAYOFF", timestamp: baseIso(60), source: "demo" },
    { outcome_type: "FUNDING", timestamp: baseIso(30), source: "demo" },
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
  await api(`/tenants/${tenantId}/companies/${companyId}/backtest/run?lookback_days=1095`, {
    method: "POST",
  });
  const report = await api(`/tenants/${tenantId}/companies/${companyId}/backtest/report`);
  const kpis = await api(`/tenants/${tenantId}/companies/${companyId}/backtest/kpis`);
  renderBacktest(report.metrics || [], kpis.kpis);
  await loadBacktestPortfolio(tenantId);
  setStatus(backtestStatus, "Backtest complete.");
};

const renderBacktest = (metrics, kpis) => {
  backtestEl.innerHTML = "";
  backtestScorecard.innerHTML = "";
  backtestChart.innerHTML = "";
  if (!metrics.length) {
    backtestEl.innerHTML = "<p>No backtest yet. Add outcomes and run it.</p>";
    return;
  }
  renderScorecard(metrics, kpis);
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

const renderScorecard = (metrics, kpis) => {
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
  if (kpis) {
    cards.push({
      title: `Precision@${kpis.k}`,
      value: `${Math.round(kpis.precision_at_k * 100)}%`,
    });
    cards.push({
      title: "Median lead time",
      value: kpis.median_lead_time_months ? `${kpis.median_lead_time_months} months` : "n/a",
    });
    cards.push({ title: "False positives", value: kpis.false_positives });
  }

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
  const data = await api(
    `/tenants/${tenantId}/companies/${companyId}/intents/timeline?days=1095`
  );
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

const loadBacktestPortfolio = async (tenantId) => {
  backtestPortfolioSummary.innerHTML = "";
  backtestPortfolioTable.innerHTML = "";
  let data;
  try {
    data = await api(`/tenants/${tenantId}/backtest/ipo_report`);
  } catch (err) {
    backtestPortfolioTable.innerHTML =
      "<p>No portfolio report yet. Run scripts/run_backtest_report.py.</p>";
    return;
  }
  const summary = document.createElement("div");
  summary.className = "card";
  summary.innerHTML = `
    <h4>Summary</h4>
    <p>Companies: ${data.summary.companies}</p>
    <p>Precision@20: ${
      data.summary.precision_at_k_avg !== null
        ? Math.round(data.summary.precision_at_k_avg * 100) + "%"
        : "n/a"
    }</p>
    <p>Median lead time: ${
      data.summary.median_lead_time_months !== null
        ? data.summary.median_lead_time_months + " months"
        : "n/a"
    }</p>
  `;
  backtestPortfolioSummary.appendChild(summary);

  const header = document.createElement("div");
  header.className = "table-row header";
  header.innerHTML = `
    <div>Company</div>
    <div>S-1</div>
    <div>Precision@20</div>
    <div>Lead time</div>
    <div>Status</div>
  `;
  backtestPortfolioTable.appendChild(header);
  data.rows.forEach((row) => {
    const node = document.createElement("div");
    node.className = "table-row";
    node.innerHTML = `
      <div>${row.company_name}</div>
      <div>${row.s1_date || "—"}</div>
      <div>${row.precision_at_k !== null ? Math.round(row.precision_at_k * 100) + "%" : "—"}</div>
      <div>${row.median_lead_time_months !== null ? row.median_lead_time_months + " mo" : "—"}</div>
      <div>${row.status}</div>
    `;
    backtestPortfolioTable.appendChild(node);
  });
};

const loadWatchlist = async (tenantId) => {
  const data = await api(`/tenants/${tenantId}/watchlist`);
  watchlistTable.innerHTML = "";
  if (!data.items || !data.items.length) {
    watchlistTable.innerHTML = "<p>No companies yet. Add a company to get started.</p>";
    return;
  }
  const unique = new Map();
  data.items.forEach((item) => {
    unique.set(item.company_id, item);
  });
  const header = document.createElement("div");
  header.className = "table-row header";
  header.innerHTML = `
    <div>Company</div>
    <div>Readiness</div>
    <div>Delta</div>
    <div>Confidence</div>
    <div>Alert</div>
    <div>Top rules</div>
  `;
  watchlistTable.appendChild(header);
  Array.from(unique.values()).forEach((item) => {
    const row = document.createElement("div");
    row.className = "table-row";
    const readiness = item.readiness_score ? item.readiness_score.toFixed(1) : "—";
    const delta = item.score_delta ? item.score_delta.toFixed(1) : "—";
    const confidence = item.confidence ? `${(item.confidence * 100).toFixed(0)}%` : "—";
    const alert = item.alert_eligible ? "Eligible" : "Hold";
    row.innerHTML = `
      <div>${item.company_name} <span class="tiny">#${item.company_id}</span></div>
      <div>${readiness}</div>
      <div>${delta}</div>
      <div>${confidence}</div>
      <div>${alert}</div>
      <div>${(item.top_rule_hits || []).join(", ") || "—"}</div>
    `;
    watchlistTable.appendChild(row);
  });
};

const loadReadinessTimeline = async (tenantId, companyId) => {
  const data = await api(
    `/tenants/${tenantId}/companies/${companyId}/timeline/ipo_prep?days=1095`
  );
  readinessTimeline.innerHTML = "";
  if (!data.points || !data.points.length) {
    readinessTimeline.innerHTML = "<p>No IPO readiness history yet.</p>";
    return;
  }
  data.points.slice(-8).forEach((point) => {
    const row = document.createElement("div");
    row.className = "timeline-row";
    const score = point.readiness_score ? point.readiness_score.toFixed(1) : "—";
    const drift = point.drift_score ? point.drift_score.toFixed(2) : "—";
    row.innerHTML = `
      <div>${new Date(point.timestamp).toLocaleDateString()}</div>
      <div class="score">${score}</div>
      <div>Drift ${drift}</div>
      <div>${point.rule_hits} rules</div>
    `;
    readinessTimeline.appendChild(row);
  });
};

const loadExplainability = async (tenantId, companyId) => {
  let data;
  try {
    data = await api(`/tenants/${tenantId}/companies/${companyId}/explain`);
  } catch (err) {
    explainPanel.innerHTML = "<p>No IPO_PREP intent found yet. Ingest signals first.</p>";
    return;
  }
  explainPanel.innerHTML = "";
  const header = document.createElement("div");
  header.className = "feed-item";
  const alertStatus = data.alert_eligible ? "Alert eligible" : "Not alert eligible";
  header.innerHTML = `
    <span>IPO readiness ${data.readiness_score ? data.readiness_score.toFixed(1) : "—"}</span>
    <p>Confidence ${(data.confidence * 100).toFixed(0)}% · ${alertStatus}</p>
    <p class="tiny">${data.alert_reason || ""}</p>
  `;
  explainPanel.appendChild(header);
  (data.rule_hits || []).forEach((hit) => {
    const card = document.createElement("div");
    card.className = "feed-item";
    card.innerHTML = `
      <span>${hit.rule_name}</span>
      <p>${hit.snippet}</p>
      <p class="tiny">${hit.source_snippet}</p>
    `;
    explainPanel.appendChild(card);
  });
  if (data.source_snippets && data.source_snippets.length) {
    const block = document.createElement("div");
    block.className = "feed-item";
    block.innerHTML = `
      <span>Source evidence</span>
      <p>${data.source_snippets.map((s) => s.snippet).join("<br/>")}</p>
    `;
    explainPanel.appendChild(block);
  }
};

const bind = () => {
  apiKeyInput.value = localStorage.getItem("apiKey") || "";
  document.getElementById("set-api-key").addEventListener("click", () => {
    saveApiKey(apiKeyInput.value);
    setStatus(apiKeyStatus, apiKeyInput.value ? "API key saved." : "API key cleared.");
  });
  document.getElementById("generate-api-key").addEventListener("click", () => {
    generateApiKey().catch((err) => setStatus(apiKeyStatus, err.message, "#d84845"));
  });
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
