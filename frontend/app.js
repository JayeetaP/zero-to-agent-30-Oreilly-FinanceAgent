const state = {
  mode: "live",
  liveReady: false,
  plan: null,
  research: null,
  briefing: null,
  proposal: null,
  preferences: null,
  memory: null,
  busy: false,
};

const questions = {
  "global-markets": "What moved global financial markets this week, and what should investors watch next?",
  stocks: "Which company, earnings, valuation, and sector developments mattered most this week?",
  "private-credit": "What changed in direct lending, deal activity, fundraising, borrower stress, and credit terms?",
  "rates-bonds": "Which economic data, central-bank decisions, and market moves changed the rates outlook?",
  "banking-deals": "What significant banking, financing, M&A, IPO, and regulatory developments occurred?",
  "commodities-currencies": "What moved commodities, currencies, and digital assets, and why does it matter?",
};

const sampleQuestion = questions["global-markets"];
const stages = ["planner", "researcher", "editor", "feedback"];
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: payload ? "POST" : "GET",
    headers: payload ? { "Content-Type": "application/json" } : {},
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function requestPayload() {
  const selectedSources = $$('.source-options input:checked').map((input) => input.value);
  const rememberedSources = state.preferences?.research?.preferred_sources || [];
  return {
    focus: state.mode === "sample" ? "global-markets" : $("#focus").value,
    question: state.mode === "sample" ? sampleQuestion : $("#question").value.trim(),
    time_window_days: Number($("#time-window").value),
    preferred_sources: [...new Set([...selectedSources, ...rememberedSources])],
    custom_domains: $("#custom-domains").value.split(",").map((item) => item.trim()).filter(Boolean),
    broader_web: $("#broader-web").checked,
    mode: state.mode,
  };
}

function addTrace(lines) {
  const trace = $("#trace");
  for (const line of lines) {
    const number = trace.children.length + 1;
    const item = document.createElement("li");
    item.innerHTML = `<span>${String(number).padStart(2, "0")}</span><p>${escapeHtml(line)}</p>`;
    trace.append(item);
  }
  trace.scrollTop = trace.scrollHeight;
}

function clearTrace(message = "Activity cleared.") {
  $("#trace").innerHTML = `<li><span>01</span><p>${escapeHtml(message)}</p></li>`;
}

function setStage(stage, status) {
  const card = document.querySelector(`[data-card="${stage}"]`);
  card.classList.remove("running", "complete", "attention");
  if (status !== "waiting") card.classList.add(status);
  document.querySelector(`[data-status="${stage}"]`).textContent =
    status === "attention" ? "Needs attention" : status[0].toUpperCase() + status.slice(1);
}

function resetFrom(stage) {
  const start = stages.indexOf(stage);
  stages.slice(start).forEach((name) => {
    setStage(name, "waiting");
    $(`#${name}-output`).innerHTML = "";
  });
  if (start <= 0) state.plan = null;
  if (start <= 1) state.research = null;
  if (start <= 2) {
    state.briefing = null;
    renderBriefing();
  }
  if (start <= 3) {
    state.proposal = null;
    $("#proposal").innerHTML = "";
  }
}

function applyAvailability() {
  const liveUnavailable = state.mode === "live" && !state.liveReady;
  $("#run-all").disabled = state.busy || liveUnavailable;
  $$('[data-run]').forEach((button) => {
    button.disabled = state.busy || liveUnavailable || (button.dataset.run === "feedback" && !state.briefing);
  });
  $("#run-feedback").disabled = state.busy || liveUnavailable || !state.briefing;
}

function setBusy(busy) {
  state.busy = busy;
  applyAvailability();
}

async function plannerStage() {
  resetFrom("planner");
  setStage("planner", "running");
  addTrace([`Coverage Planner started in ${state.mode} mode.`]);
  try {
    const response = await api("/api/plan", requestPayload());
    state.plan = response.result;
    $("#planner-output").innerHTML = state.plan.sections
      .map((section, index) => `<span>${index + 1}. ${escapeHtml(section.title)}</span>`).join("");
    if (state.memory?.active_version) {
      $("#planner-output").insertAdjacentHTML("beforeend", `<span>Memory v${state.memory.active_version}</span>`);
    }
    addTrace(response.trace);
    setStage("planner", "complete");
  } catch (error) {
    setStage("planner", "attention");
    addTrace([error.message]);
    throw error;
  }
}

async function researcherStage() {
  if (!state.plan) throw new Error("Run the Coverage Planner first.");
  resetFrom("researcher");
  setStage("researcher", "running");
  addTrace(["News Researcher started 3 independent coverage searches."]);
  try {
    const response = await api("/api/research", { request: requestPayload(), plan: state.plan });
    state.research = response.result;
    const count = state.research.sections.reduce((total, section) => total + section.candidates.length, 0);
    $("#researcher-output").innerHTML = `<span>3 searches</span><span>${count} dated articles</span><span>Links validated</span>${state.memory?.active_version ? `<span>Memory v${state.memory.active_version}</span>` : ""}`;
    addTrace(response.trace);
    setStage("researcher", "complete");
  } catch (error) {
    setStage("researcher", "attention");
    addTrace([error.message]);
    throw error;
  }
}

async function editorStage() {
  if (!state.plan || !state.research) throw new Error("Run the Planner and Researcher first.");
  resetFrom("editor");
  setStage("editor", "running");
  addTrace(["Briefing Writer started from the validated research bundle."]);
  try {
    const response = await api("/api/edit", {
      request: requestPayload(),
      plan: state.plan,
      research: state.research,
    });
    state.briefing = response.result;
    const itemCount = state.briefing.sections.reduce((total, section) => total + section.items.length, 0);
    $("#editor-output").innerHTML = `<span>Executive summary</span><span>${itemCount} developments</span><span>${state.briefing.sources.length} sources</span>${state.memory?.active_version ? `<span>Memory v${state.memory.active_version}</span>` : ""}`;
    addTrace(response.trace);
    setStage("editor", "complete");
    renderBriefing();
  } catch (error) {
    setStage("editor", "attention");
    addTrace([error.message]);
    throw error;
  }
}

async function feedbackStage() {
  if (!state.briefing) throw new Error("Create a briefing before reviewing feedback.");
  setStage("feedback", "running");
  addTrace(["Feedback Agent started. No preference has been saved."]);
  try {
    const response = await api("/api/feedback", {
      mode: state.mode,
      feedback: $("#feedback").value.trim(),
      briefing: state.briefing,
      current_preferences: state.preferences || {},
    });
    state.proposal = response.result;
    addTrace(response.trace);
    setStage("feedback", "complete");
    renderProposal();
    $("#feedback-output").innerHTML = "<span>Preference proposal ready</span><span>Approval required</span>";
  } catch (error) {
    setStage("feedback", "attention");
    addTrace([error.message]);
    throw error;
  }
}

async function runOne(stage) {
  if (state.busy) return;
  setBusy(true);
  try {
    if (stage === "planner") await plannerStage();
    if (stage === "researcher") await researcherStage();
    if (stage === "editor") await editorStage();
    if (stage === "feedback") await feedbackStage();
  } catch (error) {
    // The active stage already displayed the useful error.
  } finally {
    setBusy(false);
  }
}

async function runAll() {
  if (state.busy) return;
  setBusy(true);
  clearTrace(`${state.mode === "live" ? "Live briefing" : "Sample Run"} started.`);
  try {
    await plannerStage();
    await researcherStage();
    await editorStage();
  } catch (error) {
    // Stop at the first failed handoff and keep its visible message.
  } finally {
    setBusy(false);
  }
}

function formatted(value) {
  if (state.preferences?.display?.currency_style !== "$4.2bn") return value;
  return String(value)
    .replaceAll("USD 4.2 billion", "$4.2bn")
    .replaceAll("USD 950 million", "$950mn")
    .replaceAll("USD 1.1 billion", "$1.1bn")
    .replaceAll("USD 6.5 billion", "$6.5bn");
}

function formatDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(value.includes("T") ? value : `${value}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;
  const style = state.preferences?.display?.date_style || "August 25, 2026";
  if (style.includes("25 Aug")) {
    return new Intl.DateTimeFormat("en-GB", { year: "numeric", month: "short", day: "numeric" }).format(date);
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: style.includes("August") ? "long" : "short",
    day: "numeric",
  }).format(date);
}

function sourceMap() {
  return new Map((state.briefing?.sources || []).map((source) => [source.id, source]));
}

function citationLinks(ids, compact = false) {
  const sources = sourceMap();
  const links = ids.map((id) => {
    const source = sources.get(id);
    if (!source) return "";
    const label = compact ? id : `${source.publisher} · ${formatDate(source.publication_date)}`;
    return `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
  }).filter(Boolean);
  return links.join("<span>·</span>");
}

function renderBriefing() {
  const documentNode = $("#briefing-document");
  if (!state.briefing) {
    documentNode.hidden = true;
    documentNode.innerHTML = "";
    $("#briefing-empty").hidden = false;
    $("#briefing-badge").hidden = true;
    return;
  }

  const briefing = state.briefing;
  const itemCount = briefing.sections.reduce((total, section) => total + section.items.length, 0);
  const publisherCount = new Set(briefing.sources.map((source) => source.publisher)).size;
  $("#briefing-empty").hidden = true;
  $("#briefing-badge").hidden = false;
  $("#briefing-badge").textContent = `${itemCount} developments · ${briefing.sources.length} sources · ${publisherCount} publishers`;
  documentNode.hidden = false;

  documentNode.innerHTML = `
    <header class="document-header">
      <p class="document-kicker">${briefing.mode === "sample" ? "Real Sample Run" : "Live Briefing"}</p>
      <h3>${escapeHtml(briefing.title)}</h3>
      <p class="document-question">${escapeHtml(briefing.question)}</p>
      <dl class="document-meta">
        <div><dt>As of</dt><dd>${escapeHtml(formatDate(briefing.generated_at))}</dd></div>
        <div><dt>Coverage</dt><dd>${escapeHtml(briefing.coverage_window)}</dd></div>
        <div><dt>Sources</dt><dd>${briefing.sources.length} dated links</dd></div>
        ${briefing.sample_captured_at ? `<div><dt>Recorded</dt><dd>${escapeHtml(formatDate(briefing.sample_captured_at))}</dd></div>` : ""}
      </dl>
    </header>

    <section class="executive-summary">
      <p class="document-label">Executive summary</p>
      <p class="summary-copy">${escapeHtml(formatted(briefing.executive_summary))}</p>
      <div class="inline-citations">${citationLinks(briefing.executive_source_ids, true)}</div>
      <h4>Key takeaways</h4>
      <ol>
        ${briefing.key_takeaways.map((takeaway) => `
          <li><span>${escapeHtml(formatted(takeaway.text))}</span><span class="inline-citations">${citationLinks(takeaway.source_ids, true)}</span></li>
        `).join("")}
      </ol>
    </section>

    <nav class="document-contents" aria-label="Briefing contents">
      <span>In this briefing</span>
      ${briefing.sections.map((section, index) => `<a href="#briefing-section-${index + 1}">${index + 1}. ${escapeHtml(section.title)}</a>`).join("")}
      ${briefing.upcoming_events.length ? '<a href="#upcoming-events">Upcoming events</a>' : ""}
      <a href="#briefing-sources">Sources</a>
    </nav>

    <div class="document-sections">
      ${briefing.sections.map((section, sectionIndex) => `
        <section class="document-section" id="briefing-section-${sectionIndex + 1}">
          <div class="section-number">${String(sectionIndex + 1).padStart(2, "0")}</div>
          <div>
            <h3>${escapeHtml(section.title)}</h3>
            <p class="section-summary">${escapeHtml(formatted(section.summary))}</p>
            <div class="inline-citations section-citations">${citationLinks(section.source_ids, true)}</div>
            <div class="developments">
              ${section.items.map((item) => `
                <article class="development">
                  <h4>${escapeHtml(item.headline)}</h4>
                  <div class="source-line">${citationLinks(item.source_ids)}</div>
                  <p>${escapeHtml(formatted(item.summary))}</p>
                  <dl>
                    <div><dt>Analyst implication</dt><dd>${escapeHtml(formatted(item.analyst_implication))}</dd></div>
                    <div><dt>Watch next</dt><dd>${escapeHtml(formatted(item.watch_next))}</dd></div>
                  </dl>
                </article>
              `).join("")}
            </div>
            ${section.coverage_note ? `<p class="coverage-note"><strong>Coverage note:</strong> ${escapeHtml(section.coverage_note)}</p>` : ""}
          </div>
        </section>
      `).join("")}
    </div>

    ${briefing.upcoming_events.length ? `
      <section class="upcoming-events" id="upcoming-events">
        <p class="document-label">Upcoming events</p>
        ${briefing.upcoming_events.map((event) => `
          <article>
            <time>${escapeHtml(formatDate(event.date))}</time>
            <div><h4>${escapeHtml(event.event)}</h4><p>${escapeHtml(event.why_it_matters)}</p><div class="inline-citations">${citationLinks(event.source_ids, true)}</div></div>
          </article>
        `).join("")}
      </section>
    ` : ""}

    <section class="source-appendix" id="briefing-sources">
      <p class="document-label">Sources</p>
      <ol>
        ${briefing.sources.map((source) => `
          <li id="source-${escapeHtml(source.id)}">
            <span>${escapeHtml(source.id)}</span>
            <div><a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)}</a><p>${escapeHtml(source.publisher)} · ${escapeHtml(formatDate(source.publication_date))}</p></div>
          </li>
        `).join("")}
      </ol>
    </section>
  `;
}

function renderProposal() {
  if (!state.proposal) return;
  const fields = [
    ["Research", "Preferred sources", "research", "preferred_sources"],
    ["Research", "Excluded topics", "research", "excluded_topics"],
    ["Editorial", "Tone", "editorial", "tone"],
    ["Editorial", "Lead with implication", "editorial", "lead_with_implication"],
    ["Editorial", "Jargon level", "editorial", "jargon_level"],
    ["Display", "Currency style", "display", "currency_style"],
    ["Display", "Date style", "display", "date_style"],
  ];
  const changes = fields.filter(([, , group, key]) => {
    return JSON.stringify(state.preferences?.[group]?.[key]) !== JSON.stringify(state.proposal[group][key]);
  });
  const changeMarkup = changes.length
    ? changes.map(([groupLabel, label, group, key]) => `
        <div class="proposal-change">
          <b>${escapeHtml(groupLabel)} · ${escapeHtml(label)}</b>
          <span class="old-value">${escapeHtml(displayValue(state.preferences?.[group]?.[key]))}</span>
          <span class="change-arrow">to</span>
          <span class="new-value">${escapeHtml(displayValue(state.proposal[group][key]))}</span>
        </div>
      `).join("")
    : '<p class="no-change">The feedback did not create a durable preference change.</p>';
  $("#proposal").innerHTML = `
    <div class="proposal-heading"><strong>Proposed memory update</strong><span>${changes.length} changed field${changes.length === 1 ? "" : "s"}</span></div>
    ${changeMarkup}
    <div class="proposal-actions">
      <button id="approve-memory" type="button" ${changes.length ? "" : "disabled"}>Approve as new version</button>
      <button id="reject-memory" class="secondary-button" type="button">Reject proposal</button>
    </div>
  `;
  $("#approve-memory").addEventListener("click", approveMemory);
  $("#reject-memory").addEventListener("click", rejectProposal);
}

async function approveMemory() {
  if (!state.proposal) return;
  const saved = await api("/api/memory/approve", {
    patch: state.proposal,
    feedback: $("#feedback").value.trim() || "Approved preference update",
  });
  state.memory = saved;
  state.preferences = saved.preferences;
  $("#proposal").innerHTML = "";
  state.proposal = null;
  addTrace([`Human approved preferences v${saved.version}.`]);
  syncMemoryToInputs();
  renderMemory();
  renderBriefing();
}

function rejectProposal() {
  state.proposal = null;
  $("#proposal").innerHTML = "";
  $("#feedback-output").innerHTML = "<span>Proposal rejected</span><span>Memory unchanged</span>";
  addTrace(["Human rejected the proposal. Approved memory did not change."]);
}

function displayValue(value) {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === undefined || value === null || value === "") return "None";
  return String(value);
}

function memoryGroup(title, preferences) {
  const rows = title === "Research"
    ? [["Preferred sources", preferences.preferred_sources], ["Excluded topics", preferences.excluded_topics]]
    : title === "Editorial"
      ? [["Tone", preferences.tone], ["Lead with implication", preferences.lead_with_implication], ["Jargon", preferences.jargon_level]]
      : [["Currency", preferences.currency_style], ["Dates", preferences.date_style]];
  return `<section class="memory-group"><h4>${title}</h4>${rows.map(([label, value]) => `
    <div><span>${escapeHtml(label)}</span><strong>${escapeHtml(displayValue(value))}</strong></div>
  `).join("")}</section>`;
}

function renderMemory() {
  const memory = state.memory;
  const preferences = state.preferences;
  if (!preferences) return;

  $("#memory-version").textContent = memory?.active_version ? `Active v${memory.active_version}` : "Defaults";
  $("#active-memory").innerHTML = `
    ${memoryGroup("Research", preferences.research)}
    ${memoryGroup("Editorial", preferences.editorial)}
    ${memoryGroup("Display", preferences.display)}
  `;

  const history = memory?.history || [];
  $("#memory-history").innerHTML = history.length ? history.map((entry) => `
    <article class="memory-version-card ${entry.version === memory.active_version ? "active" : ""}">
      <div class="memory-version-title">
        <strong>Version ${entry.version}</strong>
        ${entry.version === memory.active_version ? "<span>Active</span>" : `<button type="button" data-activate-memory="${entry.version}">Make active</button>`}
      </div>
      <time>${escapeHtml(formatDate(entry.approved_at))}</time>
      <p>${escapeHtml(entry.feedback || "Approved preference update")}</p>
      <ul>${(entry.changes || []).map((change) => `
        <li><b>${escapeHtml(change.label)}</b><span>${escapeHtml(displayValue(change.before))} to ${escapeHtml(displayValue(change.after))}</span></li>
      `).join("") || "<li><span>No field changes recorded.</span></li>"}</ul>
    </article>
  `).join("") : '<p class="empty-memory-history">Approve feedback to create the first memory version.</p>';

  $$('[data-activate-memory]').forEach((button) => {
    button.addEventListener("click", () => activateMemory(Number(button.dataset.activateMemory)));
  });
  $("#memory-state").textContent = memory?.active_version
    ? `Version ${memory.active_version} is active. ${history.length} approved version${history.length === 1 ? "" : "s"} stored locally.`
    : "Default preferences are active. No approved local versions yet.";
}

async function activateMemory(version) {
  const memory = await api("/api/memory/activate", { version });
  state.memory = memory;
  state.preferences = memory.preferences;
  syncMemoryToInputs();
  renderMemory();
  renderBriefing();
  addTrace([`Human activated approved preferences v${version}.`]);
}

function syncMemoryToInputs() {
  const remembered = new Set(state.preferences?.research?.preferred_sources || []);
  $$('.source-options input').forEach((input) => {
    if (remembered.has(input.value)) input.checked = true;
  });
}

function lockSampleInputs(locked) {
  ["#focus", "#question", "#time-window", "#custom-domains", "#broader-web"].forEach((selector) => {
    $(selector).disabled = locked;
  });
  $$('.source-options input').forEach((input) => { input.disabled = locked; });
}

function setMode(mode) {
  state.mode = mode;
  $$('[data-mode]').forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  const live = mode === "live";
  lockSampleInputs(!live);
  if (!live) {
    $("#focus").value = "global-markets";
    $("#question").value = sampleQuestion;
    $("#time-window").value = "7";
  }
  $("#mode-explainer").innerHTML = live
    ? "<strong>Live briefing</strong><span>Uses the local Ollama model and current public search results.</span>"
    : "<strong>Real Sample Run</strong><span>Recorded August 25, 2026 with real articles, dates, and source links.</span>";
  $("#data-badge").textContent = live ? "Live news" : "Real sample · Aug 25, 2026";
  $("#data-badge").classList.toggle("live", live);
  $("#run-mode-title").textContent = live ? "Current news" : "Recorded Global Markets briefing";
  $("#run-mode-copy").textContent = live
    ? "The first live run can take several minutes on a local model."
    : "Loads a reliable, sourced run without model or network calls.";
  $("#run-all").textContent = live ? "Create live briefing" : "Load Sample Run";
  resetFrom("planner");
  clearTrace(`Switched to ${live ? "Live Briefing" : "Sample Run"}.`);
  applyAvailability();
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    const badge = $("#server-state");
    state.liveReady = health.model_ready;
    if (health.model_ready) {
      badge.textContent = `${health.configured_model} ready`;
      badge.className = "server-state ready";
    } else if (health.ollama_running) {
      badge.textContent = `${health.configured_model} not installed`;
      badge.className = "server-state warning";
    } else {
      badge.textContent = "Ollama is not running";
      badge.className = "server-state warning";
    }
  } catch (error) {
    state.liveReady = false;
    $("#server-state").textContent = "Backend unavailable";
    $("#server-state").className = "server-state warning";
  }
  applyAvailability();
}

async function loadMemory() {
  try {
    const memory = await api("/api/memory");
    state.memory = memory;
    state.preferences = memory.preferences;
    syncMemoryToInputs();
    renderMemory();
  } catch (error) {
    $("#memory-state").textContent = "Memory is unavailable. Default preferences will be used.";
  }
}

$("#focus").addEventListener("change", (event) => {
  $("#question").value = questions[event.target.value];
  resetFrom("planner");
});
$$('[data-mode]').forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
$$('[data-run]').forEach((button) => button.addEventListener("click", () => runOne(button.dataset.run)));
$("#run-all").addEventListener("click", runAll);
$("#run-feedback").addEventListener("click", () => runOne("feedback"));
$("#clear-trace").addEventListener("click", () => clearTrace());

loadHealth();
loadMemory();
applyAvailability();
