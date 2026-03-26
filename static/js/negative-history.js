export const NEGATIVE_HISTORY_LIST = [
  { id: "head_injury", label: "H/o Head injury" },
  { id: "seizures", label: "H/o Seizures" },
  { id: "fever_ams", label: "H/o fever with Altered Sensorium" },
  { id: "focal_deficit_headache", label: "H/o focal neurological deficits/headache" },
  { id: "hallucinations", label: "H/o Hallucinatory behaviour" },
  { id: "delusions", label: "H/o Delusions or suspicious" },
  { id: "mania_symptoms", label: "H/o Elated mood / decreased need for sleep" },
  { id: "depression", label: "H/o Persistent Low Mood" },
  { id: "ocd_symptoms", label: "H/o Repetitive thoughts or Behaviours" },
  { id: "suicidal_attempts", label: "H/o Suicidal attempts" },
  { id: "legal_issues", label: "H/o Legal Issues" }
];

export const SEQUELAE_LIST = [
  "Head injury",
  "Loss of consciousness",
  "Seizures",
  "Fever",
  "Delirium",
  "Coma",
  "Stroke",
  "Transient ischemic attacks",
  "CNS infections",
  "Meningitis",
  "Encephalitis",
  "Neurosyphilis",
  "HIV-related illness",
  "Substance use",
  "Alcohol use",
  "Drug abuse",
  "Withdrawal states",
  "Overdose history",
  "Chronic medical illness",
  "Diabetes mellitus",
  "Hypertension",
  "Thyroid disorders",
  "Renal disease",
  "Hepatic disease",
  "Malignancy",
  "Medication history",
  "Steroid use",
  "Neuroleptic use",
  "Antidepressant use",
  "Mood stabilizer use",
  "Past psychiatric illness",
  "Hospitalization history",
  "Suicide attempts",
  "Self-harm",
  "Violence history",
  "Forensic history",
  "Developmental delay",
  "Birth complications",
  "Intellectual disability",
  "Family history of psychiatric illness",
  "Family history of suicide",
  "Personality disorder traits",
  "Sleep disorders",
  "Sexual dysfunction",
  "Headache",
  "Visual disturbances",
  "Hearing impairment",
  "Memory impairment",
  "Cognitive decline"
];

function safeJsonParse(value, fallback) {
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" ? parsed : fallback;
  } catch (_e) {
    return fallback;
  }
}

function escapeHtml(text) {
  return String(text == null ? "" : text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildDurationOptions(raw) {
  const n = parseInt(raw, 10);
  if (Number.isNaN(n) || n <= 0) return [];
  return [
    `${n} day${n > 1 ? "s" : ""} ago`,
    `${n} week${n > 1 ? "s" : ""} ago`,
    `${n} month${n > 1 ? "s" : ""} ago`,
    `${n} year${n > 1 ? "s" : ""} ago`,
  ];
}

export function initNegativeHistory(options = {}) {
  const containerId = options.containerId || "negative-history-container";
  const hiddenInputId = options.hiddenInputId || "negative_history_data";
  const positiveData = options.positiveData && typeof options.positiveData === "object" ? options.positiveData : null;
  const readonlyPositive = !!options.readonlyPositive;
  const editToggleBtnId = options.editToggleBtnId || null;
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container) return;

  const defaults = {};
  NEGATIVE_HISTORY_LIST.forEach((item) => {
    defaults[item.id] = { status: "Unknown", severity: 5, duration: "", sequelae: "" };
  });
  const initial = hiddenInput ? safeJsonParse(hiddenInput.value || "{}", {}) : {};
  const state = { ...defaults };
  Object.keys(initial).forEach((key) => {
    if (!state[key]) return;
    const current = initial[key] || {};
    state[key] = {
      status: ["Yes", "No", "Unknown"].includes(current.status) ? current.status : state[key].status,
      severity: Number.isFinite(parseInt(current.severity, 10)) ? Math.min(10, Math.max(1, parseInt(current.severity, 10))) : state[key].severity,
      duration: current.duration || "",
      sequelae: current.sequelae || "",
    };
  });

  function syncHidden() {
    if (hiddenInput) hiddenInput.value = JSON.stringify(state);
  }

  function rowReadOnlySummary(item, current) {
    const wrap = document.createElement("div");
    wrap.className = "neg-row";
    wrap.innerHTML = `
      <div class="neg-row-top">
        <span class="neg-label">${escapeHtml(item.label)}</span>
        <span class="neg-readonly-pill">Yes</span>
      </div>
      <div class="neg-readonly-grid">
        <div><span class="neg-readonly-k">Severity</span><span class="neg-readonly-v">${escapeHtml(current.severity)}</span></div>
        <div><span class="neg-readonly-k">Duration</span><span class="neg-readonly-v">${escapeHtml(current.duration || "-")}</span></div>
        <div><span class="neg-readonly-k">Sequelae</span><span class="neg-readonly-v">${escapeHtml(current.sequelae || "-")}</span></div>
      </div>
    `;
    return wrap;
  }

  function renderRow(item) {
    const row = document.createElement("div");
    row.className = "neg-row";
    row.dataset.itemId = item.id;
    const current = state[item.id];
    row.innerHTML = `
      <div class="neg-row-top">
        <span class="neg-label">${escapeHtml(item.label)}</span>
        <div class="neg-toggle-group">
          <button type="button" class="neg-toggle-btn ${current.status === "Yes" ? "active" : ""}" data-value="Yes">Yes</button>
          <button type="button" class="neg-toggle-btn ${current.status === "No" ? "active" : ""}" data-value="No">No</button>
          <button type="button" class="neg-toggle-btn ${current.status === "Unknown" ? "active" : ""}" data-value="Unknown">Unknown</button>
        </div>
      </div>
      <div class="neg-expand ${current.status === "Yes" ? "" : "hidden"}">
        <div class="neg-two-col">
          <div>
            <label class="neg-mini-label">Severity</label>
            <div class="neg-slider-wrap">
              <input type="range" min="1" max="10" value="${current.severity}" class="neg-severity-slider">
              <span class="neg-severity-value">${current.severity}</span>
            </div>
          </div>
          <div class="neg-field-wrap">
            <label class="neg-mini-label">Duration</label>
            <input type="text" class="neg-duration-input" placeholder="Type number..." value="${escapeHtml(current.duration)}">
            <ul class="neg-duration-dropdown hidden"></ul>
          </div>
        </div>
        <div class="neg-field-wrap">
          <label class="neg-mini-label">Sequelae</label>
          <input type="text" class="neg-sequelae-input" placeholder="Search sequelae..." value="${escapeHtml(current.sequelae)}">
          <ul class="neg-sequelae-dropdown hidden"></ul>
        </div>
      </div>
    `;

    const expand = row.querySelector(".neg-expand");
    const toggleBtns = row.querySelectorAll(".neg-toggle-btn");
    const slider = row.querySelector(".neg-severity-slider");
    const sliderValue = row.querySelector(".neg-severity-value");
    const durInput = row.querySelector(".neg-duration-input");
    const durDropdown = row.querySelector(".neg-duration-dropdown");
    const seqInput = row.querySelector(".neg-sequelae-input");
    const seqDropdown = row.querySelector(".neg-sequelae-dropdown");

    toggleBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const val = btn.dataset.value;
        state[item.id].status = val;
        toggleBtns.forEach((b) => b.classList.toggle("active", b === btn));
        expand.classList.toggle("hidden", val !== "Yes");
        syncHidden();
      });
    });

    if (slider && sliderValue) {
      slider.addEventListener("input", () => {
        sliderValue.textContent = slider.value;
        state[item.id].severity = parseInt(slider.value, 10) || 5;
        syncHidden();
      });
    }

    if (durInput && durDropdown) {
      durInput.addEventListener("input", () => {
        const val = durInput.value.trim();
        state[item.id].duration = val;
        syncHidden();
        const options = buildDurationOptions(val);
        if (!options.length) {
          durDropdown.classList.add("hidden");
          durDropdown.innerHTML = "";
          return;
        }
        durDropdown.innerHTML = options.map((opt) => `<li>${escapeHtml(opt)}</li>`).join("");
        durDropdown.classList.remove("hidden");
      });
      durDropdown.addEventListener("click", (e) => {
        const li = e.target.closest("li");
        if (!li) return;
        durInput.value = li.textContent || "";
        state[item.id].duration = durInput.value;
        durDropdown.classList.add("hidden");
        syncHidden();
      });
      document.addEventListener("click", (e) => {
        if (!row.contains(e.target)) durDropdown.classList.add("hidden");
      });
    }

    if (seqInput && seqDropdown) {
      seqInput.addEventListener("input", () => {
        const val = seqInput.value.trim().toLowerCase();
        state[item.id].sequelae = seqInput.value;
        syncHidden();
        if (!val) {
          seqDropdown.classList.add("hidden");
          seqDropdown.innerHTML = "";
          return;
        }
        const filtered = SEQUELAE_LIST.filter((s) => s.toLowerCase().includes(val)).slice(0, 30);
        if (!filtered.length) {
          seqDropdown.classList.add("hidden");
          seqDropdown.innerHTML = "";
          return;
        }
        seqDropdown.innerHTML = filtered.map((itemText) => `<li>${escapeHtml(itemText)}</li>`).join("");
        seqDropdown.classList.remove("hidden");
      });
      seqDropdown.addEventListener("click", (e) => {
        const li = e.target.closest("li");
        if (!li) return;
        seqInput.value = li.textContent || "";
        state[item.id].sequelae = seqInput.value;
        seqDropdown.classList.add("hidden");
        syncHidden();
      });
      document.addEventListener("click", (e) => {
        if (!row.contains(e.target)) seqDropdown.classList.add("hidden");
      });
    }

    return row;
  }

  container.innerHTML = "";
  if (readonlyPositive) {
    const source = positiveData || filterPositiveFromState(state);
    const list = NEGATIVE_HISTORY_LIST
      .map((item) => ({ item, current: source[item.id] }))
      .filter((x) => x.current && x.current.status === "Yes");
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "neg-row";
      empty.innerHTML = '<div class="neg-label" style="font-weight:500;">No positive findings in previous/same visit.</div>';
      container.appendChild(empty);
    } else {
      list.forEach(({ item, current }) => container.appendChild(rowReadOnlySummary(item, current)));
    }
  } else {
    NEGATIVE_HISTORY_LIST.forEach((item) => container.appendChild(renderRow(item)));
  }
  syncHidden();

  const editBtn = editToggleBtnId ? document.getElementById(editToggleBtnId) : null;
  if (editBtn) {
    editBtn.style.display = readonlyPositive ? "inline-flex" : "none";
    editBtn.addEventListener("click", () => {
      container.innerHTML = "";
      NEGATIVE_HISTORY_LIST.forEach((item) => container.appendChild(renderRow(item)));
      editBtn.style.display = "none";
      syncHidden();
    });
  }
}

function filterPositiveFromState(state) {
  const out = {};
  Object.keys(state || {}).forEach((k) => {
    const item = state[k];
    if (item && item.status === "Yes") out[k] = item;
  });
  return out;
}