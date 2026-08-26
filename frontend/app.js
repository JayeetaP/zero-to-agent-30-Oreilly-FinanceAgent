const state = {
  mode: "fixture",
  plan: null,
  research: null,
  briefing: null,
  proposal: null,
  preferences: null,
  busy: false,
};

const questions = {
  sustainable: "What material sustainability developments happened in the last seven days?",
  consumer: "What changed in consumer demand, pricing, and company outlooks this week?",
  "private-credit": "What should a private-credit analyst investigate from the last seven days?",
};

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
  return {
    focus: $("#focus").value,
    question: $("#question").value.trim(),
    time_window_days: Number($("#time-window").value),
    preferred_sources: $$('.source-options input:checked').map((input) => input.value),
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

function setBusy(busy) {
  state.busy = busy;
  $("#run-all").disabled = busy;
  $("#run-feedback").disabled = busy || !state.briefing;
  $$('[data-run]').forEach((button) => { button.disabled = busy; });
}

async function plannerStage() {
  resetFrom("planner");
  setStage("planner", "running");
  addTrace([`Planner started in ${state.mode} mode.`]);
  try {
    const response = await api("/api/plan", requestPayload());
    state.plan = response.result;
    $("#planner-output").innerHTML = state.plan.sections
      .map((section, index) => `<span>${index + 1}. ${escapeHtml(section.title)}</span>`).join("");
    addTrace(response.trace);
    setStage("planner", "complete");
  } catch (error) {
    setStage("planner", "attention");
    addTrace([error.message]);
    throw error;
  }
}

async function researcherStage() {
  if (!state.plan) throw new Error("Run the Planner first.");
  resetFrom("researcher");
  setStage("researcher", "running");
  addTrace(["Researcher started 3 section searches."]);
  try {
    const response = await api("/api/research", { request: requestPayload(), plan: state.plan });
    state.research = response.result;
    const count = state.research.sections.reduce((total, section) => total + section.candidates.length, 0);
    $("#researcher-output").innerHTML = `<span>3 searches</span><span>${count} candidates</span><span>URLs validated</span>`;
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
  addTrace(["Editor started from the supplied research bundle."]);
  try {
    const response = await api("/api/edit", {
      request: requestPayload(),
      plan: state.plan,
      research: state.research,
    });
    state.briefing = response.result;
    $("#editor-output").innerHTML = "<span>3 sections</span><span>9 items</span><span>3 × 3 validated</span>";
    addTrace(response.trace);
    setStage("editor", "complete");
    renderBriefing();
    $("#run-feedback").disabled = false;
  } catch (error) {
    setStage("editor", "attention");
    addTrace([error.message]);
    throw error;
  }
}

async function feedbackStage() {
  if (!state.briefing) throw new Error("Create a briefing before running feedback.");
  setStage("feedback", "running");
  addTrace(["Feedback Agent started. No memory has been written."]);
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
    $("#feedback-output").innerHTML = "<span>Typed patch ready</span><span>Approval required</span>";
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
    // The stage already displayed the useful error.
  } finally {
    setBusy(false);
  }
}

async function runAll() {
  if (state.busy) return;
  setBusy(true);
  clearTrace(`Full ${state.mode} workflow started.`);
  try {
    await plannerStage();
    await researcherStage();
    await editorStage();
  } catch (error) {
    // Stop on the first failed handoff and keep its visible message.
  } finally {
    setBusy(false);
  }
}

function formatted(value) {
  if (state.preferences?.display?.currency_style !== "$4.2bn") return value;
  return value
    .replaceAll("USD 4.2 billion", "$4.2bn")
    .replaceAll("USD 950 million", "$950mn")
    .replaceAll("USD 1.1 billion", "$1.1bn")
    .replaceAll("USD 6.5 billion", "$6.5bn");
}

function renderBriefing() {
  const grid = $("#briefing-grid");
  if (!state.briefing) {
    grid.innerHTML = "";
    $("#briefing-empty").hidden = false;
    $("#contract-badge").hidden = true;
    return;
  }
  $("#briefing-empty").hidden = true;
  $("#contract-badge").hidden = false;
  grid.innerHTML = state.briefing.sections.map((section, sectionIndex) => `
    <article class="briefing-column">
      <span>Section ${sectionIndex + 1}</span>
      <h3>${escapeHtml(section.title)}</h3>
      <p>${escapeHtml(section.purpose)}</p>
      <div class="news-list">
        ${section.items.map((item) => `
          <article class="news-item ${item.status === "insufficient_evidence" ? "insufficient" : ""}">
            <h4>${escapeHtml(item.headline)}</h4>
            <p><strong>What happened:</strong> ${escapeHtml(formatted(item.what_happened))}</p>
            <p><strong>Why it matters:</strong> ${escapeHtml(item.why_it_matters)}</p>
            <p><strong>Watch next:</strong> ${escapeHtml(item.watch_next)}</p>
            ${item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.source)} · ${escapeHtml(item.publication_date || "date unavailable")} ↗</a>` : `<p>${escapeHtml(item.source)}</p>`}
          </article>
        `).join("")}
      </div>
    </article>
  `).join("");
}

function renderProposal() {
  if (!state.proposal) return;
  $("#proposal").innerHTML = `
    <div><b>Research</b>${escapeHtml((state.proposal.research.preferred_sources || []).join(", ") || "No source change")}</div>
    <div><b>Editorial</b>${escapeHtml(state.proposal.editorial.tone)} · lead with implication: ${state.proposal.editorial.lead_with_implication}</div>
    <div><b>Display</b>${escapeHtml(state.proposal.display.currency_style)}</div>
    <button id="approve-memory" type="button">Approve and save memory</button>
  `;
  $("#approve-memory").addEventListener("click", approveMemory);
}

async function approveMemory() {
  if (!state.proposal) return;
  const saved = await api("/api/memory/approve", { patch: state.proposal });
  state.preferences = saved.preferences;
  $("#memory-state").textContent = `Memory v${saved.version} approved at ${new Date(saved.approved_at).toLocaleString()}.`;
  $("#proposal").innerHTML = "";
  state.proposal = null;
  addTrace([`Human approved memory v${saved.version}.`]);
  renderBriefing();
}

function setMode(mode) {
  state.mode = mode;
  $$("[data-mode]").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  const live = mode === "live";
  $("#mode-explainer").innerHTML = live
    ? "<strong>Live mode</strong><span>Agno + local Ollama + public web search. No paid API.</span>"
    : "<strong>Fixture mode</strong><span>Deterministic sample data. No model or internet call.</span>";
  $("#data-badge").textContent = live ? "Live · local Ollama" : "Fixture · no model call";
  $("#data-badge").classList.toggle("live", live);
  $("#run-mode-title").textContent = live ? "Current-news mode" : "Reliable teaching mode";
  $("#run-mode-copy").textContent = live
    ? "Uses your local open model and searches the public web."
    : "Uses the bundled fixture and never needs a model.";
  resetFrom("planner");
  clearTrace(`Switched to ${mode} mode.`);
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    const badge = $("#server-state");
    if (health.model_ready) {
      badge.textContent = `${health.configured_model} ready`;
      badge.className = "server-state ready";
    } else if (health.ollama_running) {
      badge.textContent = `${health.configured_model} not downloaded`;
      badge.className = "server-state warning";
    } else {
      badge.textContent = "Ollama is not running";
      badge.className = "server-state warning";
    }
  } catch (error) {
    $("#server-state").textContent = "Backend unavailable";
    $("#server-state").className = "server-state warning";
  }
}

async function loadMemory() {
  try {
    const memory = await api("/api/memory");
    state.preferences = memory.preferences;
    if (memory.version) $("#memory-state").textContent = `Memory v${memory.version} is active.`;
  } catch (error) {
    // The default preference object remains sufficient for the demo.
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
