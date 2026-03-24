(function () {
  const criteriaDB = {
    depression: {
      "DSM-5": "DSM-5 Criteria for Major Depressive Disorder:\n\nA. Five (or more) symptoms during the same 2-week period; at least one is depressed mood or loss of interest/pleasure.\n1. Depressed mood most of the day.\n2. Markedly diminished interest or pleasure.\n3. Weight or appetite change.\n4. Insomnia or hypersomnia.\n5. Psychomotor agitation or retardation.\n6. Fatigue or loss of energy.\n7. Worthlessness or excessive guilt.\n8. Poor concentration or indecisiveness.\n9. Recurrent thoughts of death or suicide.\n\nB. Symptoms cause clinically significant distress or impairment.",
      "ICD-10": "ICD-10 Criteria for Depressive Episode (F32):\n\nKey symptoms: depressed mood, loss of interest, reduced energy.\nAssociated symptoms include reduced concentration, low self-esteem, guilt, pessimism, self-harm ideas, sleep disturbance, and appetite change."
    },
    schizophrenia: {
      "DSM-5": "DSM-5 Criteria for Schizophrenia:\n\nTwo or more symptoms for 1 month, with at least one of delusions, hallucinations, or disorganized speech. Functioning is markedly impaired, and continuous signs persist for at least 6 months.",
      "ICD-10": "ICD-10 Criteria for Schizophrenia (F20):\n\nAt least one clear first-rank symptom such as thought interference, delusions of control, running commentary voices, or bizarre persistent delusions, or two other characteristic symptoms such as persistent hallucinations, thought disorder, catatonia, or negative symptoms."
    },
    bipolar: {
      "DSM-5": "DSM-5 Criteria for Manic Episode:\n\nA distinct period of abnormally elevated, expansive, or irritable mood and increased activity or energy lasting at least 1 week, with three or more associated symptoms such as grandiosity, decreased need for sleep, pressured speech, racing thoughts, distractibility, increased goal-directed activity, or risky behavior.",
      "ICD-10": "ICD-10 Criteria for Manic Episode (F30):\n\nMood is elevated, expansive, or irritable, with at least three associated features such as increased activity, talkativeness, flight of ideas, reduced inhibitions, decreased need for sleep, grandiosity, distractibility, or reckless behavior."
    },
    anxiety: {
      "DSM-5": "DSM-5 Criteria for Generalized Anxiety Disorder:\n\nExcessive anxiety and worry occurring more days than not for at least 6 months, difficult to control, with at least three associated symptoms such as restlessness, fatigue, poor concentration, irritability, muscle tension, or sleep disturbance.",
      "ICD-10": "ICD-10 Criteria for Generalized Anxiety Disorder (F41.1):\n\nPrimary anxiety symptoms are present on most days for several weeks or months, usually involving apprehension, motor tension, and autonomic overactivity."
    }
  };

  /** Visit snapshot pills (under “Current Clinical State”) keyed by provisional label heuristics. */
  const clinicalStateSnapshotLists = {
    bipolar: ["Recovery", "Remission", "Partial Remission", "Depressive Episode", "Manic Episode", "Hypomanic Episode", "Mixed Episode", "Relapse", "Loss of Follow-up"],
    depress: ["Recovery", "Remission", "Partial Remission", "Mild Depressive Episode", "Moderate Depressive Episode", "Severe Depressive Episode", "Relapse", "Loss of Follow-up"],
    schizo: ["Recovery", "Remission", "Partial Remission", "Stable Phase", "Acute Psychotic Episode", "Residual Phase", "Relapse", "Loss of Follow-up"],
    ocd: ["Recovery", "Remission", "Partial Remission", "Active OCD", "Severe OCD", "Treatment Resistant Phase", "Relapse", "Loss of Follow-up"],
    anxiety: ["Recovery", "Remission", "Partial Remission", "Active Anxiety", "Acute Panic Phase", "Relapse", "Loss of Follow-up"],
    default: ["Loss of Follow-up", "Partial Remission", "Recovery", "Relapse", "Remission"]
  };

  const pickers = {};

  function safeJsonParse(value) {
    try {
      return JSON.parse(value);
    } catch (error) {
      return null;
    }
  }

  /**
   * Remove leading ICD-10 / ICD-11 style codes from the visible & stored label so
   * ICD-11 search uses plain terms (e.g. "Bipolar Disorder" not "F31 Bipolar Disorder").
   */
  function stripLeadingCodes(label, explicitCode) {
    let t = String(label || "").trim();
    if (!t) return t;
    const c = String(explicitCode || "").trim();
    if (c && t.toUpperCase().startsWith(c.toUpperCase() + " ")) {
      t = t.slice(c.length).trim();
    }
    let prev;
    let guard = 0;
    do {
      prev = t;
      t = t.replace(/^F\d{2}(?:\.\d+)?\s+/i, "").trim();
      t = t.replace(/^\d[A-Z]\d{2}(?:\.[0-9A-Za-z]+)?\s+/, "").trim();
      guard += 1;
    } while (t !== prev && t.length > 0 && guard < 5);
    return t;
  }

  function normalizeItem(item) {
    if (!item) return null;
    if (typeof item === "string") {
      const raw = item.trim();
      if (!raw) return null;
      const label = stripLeadingCodes(raw, "");
      return label ? { label, code: "", system: "Custom" } : null;
    }

    let label = String(item.label || item.title || item.name || item.value || "").trim();
    if (!label) return null;

    const code = String(item.code || "").trim();
    label = stripLeadingCodes(label, code);

    return {
      label,
      code,
      system: String(item.system || "Custom").trim() || "Custom"
    };
  }

  function normalizeStoredItems(value) {
    if (!value) return [];
    const parsed = Array.isArray(value) ? value : safeJsonParse(value);
    if (Array.isArray(parsed)) {
      return parsed.map(normalizeItem).filter(Boolean);
    }
    if (parsed && typeof parsed === "object") {
      const item = normalizeItem(parsed);
      return item ? [item] : [];
    }
    if (typeof value === "string") {
      return value
        .split(/[\r\n,]+/)
        .map(part => normalizeItem(part))
        .filter(Boolean);
    }
    return [];
  }

  function dedupeItems(items) {
    const seen = new Set();
    return items.filter(item => {
      const key = [item.label.toLowerCase(), item.system.toLowerCase()].join("|");
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const ICD11_HIT_START = "\uE000";
  const ICD11_HIT_END = "\uE001";

  /**
   * WHO ICD-11 search returns titles with <em class='found'>…</em> highlight markup.
   * Convert to safe HTML with <mark> so clinicians see readable text, not raw tags.
   */
  function icd11TitleToSafeHtml(raw) {
    let s = String(raw || "");
    s = s.replace(/<em\b[^>]*\bclass\s*=\s*['"]found['"][^>]*>/gi, ICD11_HIT_START);
    s = s.replace(/<\/em>/gi, ICD11_HIT_END);
    s = s.replace(/<[^>]+>/g, "");
    s = escapeHtml(s);
    s = s.split(ICD11_HIT_START).join('<mark class="icd11-found">');
    s = s.split(ICD11_HIT_END).join("</mark>");
    return s;
  }

  function serializeItems(items) {
    return JSON.stringify(items.map(item => ({
      label: item.label,
      code: item.code || "",
      system: item.system || "Custom"
    })));
  }

  function ensureDiagnosisPickerStyles() {
    if (document.getElementById("diagnosis-picker-extras-styles")) return;
    const style = document.createElement("style");
    style.id = "diagnosis-picker-extras-styles";
    style.textContent = `
      .diagnosis-picker-shell .diagnosis-option { align-items: center; }
      .diagnosis-option-code { font-weight: 600; color: #446688; font-size: 13px; min-width: 3.25em; flex-shrink: 0; }
      .diagnosis-picker-shell .diagnosis-option-label { flex: 1; min-width: 0; }
    `;
    document.head.appendChild(style);
  }

  function renderPicker(picker) {
    picker.chips.innerHTML = picker.items.map((item, index) => {
      const sys = escapeHtml(item.system || "Custom");
      const chipLabel = item.code && item.label
        ? `${escapeHtml(item.code)} — ${escapeHtml(item.label)}`
        : escapeHtml(item.label);
      return (
        `<span class="diagnosis-chip" title="${sys}">
        <span class="diagnosis-chip-label">${chipLabel}</span>
        <button type="button" class="diagnosis-chip-remove" data-index="${index}" aria-label="Remove diagnosis">×</button>
      </span>`
      );
    }).join("");

    picker.hiddenInput.value = serializeItems(picker.items);
    picker.root.dataset.hasItems = picker.items.length ? "true" : "false";
  }

  function renderSuggestions(picker, query) {
    const trimmed = (query || "").trim();
    if (trimmed.length < 2) {
      picker.dropdown.innerHTML = "";
      picker.dropdown.style.display = "none";
      picker.visibleOptions = [];
      return;
    }

    picker._searchSeq = (picker._searchSeq || 0) + 1;
    const seq = picker._searchSeq;
    picker.dropdown.style.display = "block";
    picker.dropdown.innerHTML = `<div class="diagnosis-option diagnosis-option-empty">Searching ICD-11…</div>`;

    fetch(`/api/search_icd11?q=${encodeURIComponent(trimmed)}`)
      .then(response => response.json())
      .then(data => {
        const results = Array.isArray(data) ? data : [];
        if (seq !== picker._searchSeq) return;
        if (!results.length) {
          picker.visibleOptions = [];
          picker.dropdown.innerHTML = `<div class="diagnosis-option diagnosis-option-empty">No matching diagnosis found. Press Enter to add "${escapeHtml(trimmed)}"</div>`;
          picker.dropdown.style.display = "block";
          return;
        }

        const matches = results
          .map(r => ({
            label: String(r.name || "").trim(),
            code: String(r.code || "").trim(),
            system: String(r.system || "ICD-11").trim() || "ICD-11"
          }))
          .filter(m => m.label);

        picker.visibleOptions = matches;
        picker.dropdown.innerHTML = matches.map((item, index) => {
          const codeHtml = item.code
            ? `<span class="diagnosis-option-code">${escapeHtml(item.code)}</span>`
            : "";
          return (
            `<button type="button" class="diagnosis-option" data-index="${index}">
        ${codeHtml}
        <span class="diagnosis-option-label">${escapeHtml(item.label)}</span>
        <span class="diagnosis-option-system">${escapeHtml(item.system || "ICD-11")}</span>
      </button>`
          );
        }).join("");
        picker.dropdown.style.display = "block";
      })
      .catch(() => {
        if (seq !== picker._searchSeq) return;
        picker.visibleOptions = [];
        picker.dropdown.innerHTML = `<div class="diagnosis-option diagnosis-option-empty">No matching diagnosis found. Press Enter to add "${escapeHtml(trimmed)}"</div>`;
        picker.dropdown.style.display = "block";
      });
  }

  function scheduleSuggestions(picker, query) {
    const trimmed = (query || "").trim();
    if (trimmed.length < 2) {
      if (picker._suggestTimer) clearTimeout(picker._suggestTimer);
      picker.dropdown.innerHTML = "";
      picker.dropdown.style.display = "none";
      picker.visibleOptions = [];
      return;
    }
    if (picker._suggestTimer) clearTimeout(picker._suggestTimer);
    picker._suggestTimer = setTimeout(() => renderSuggestions(picker, query), 300);
  }

  function hideSuggestions(picker) {
    picker.dropdown.style.display = "none";
    picker.visibleOptions = [];
  }

  function addItem(picker, item) {
    const normalized = normalizeItem(item);
    if (!normalized) return;
    if (picker.key === "provisional") {
      picker.items = [normalized];
    } else {
      picker.items = dedupeItems(picker.items.concat([normalized]));
    }
    renderPicker(picker);
    picker.input.value = "";
    hideSuggestions(picker);
    document.dispatchEvent(new CustomEvent("diagnosis-picker:changed", {
      detail: {
        key: picker.key,
        items: picker.items.slice()
      }
    }));
  }

  function removeItem(picker, index) {
    picker.items = picker.items.filter((_, itemIndex) => itemIndex !== index);
    renderPicker(picker);
    document.dispatchEvent(new CustomEvent("diagnosis-picker:changed", {
      detail: {
        key: picker.key,
        items: picker.items.slice()
      }
    }));
  }

  function initPicker(config) {
    const root = document.getElementById(config.rootId);
    const hiddenInput = document.getElementById(config.hiddenInputId);
    if (!root || !hiddenInput) return;

    root.innerHTML = `
      <div class="diagnosis-picker-shell">
        <div class="diagnosis-chip-list"></div>
        <div class="diagnosis-input-row">
          <input type="text" class="diagnosis-picker-input" placeholder="${escapeHtml(config.placeholder || "Type or select...")}">
        </div>
        <div class="diagnosis-options"></div>
      </div>
    `;

    let initialItems = normalizeStoredItems(config.initialItems || hiddenInput.value);
    if (config.key === "provisional" && initialItems.length > 1) {
      initialItems = [initialItems[0]];
    }

    const picker = {
      key: config.key,
      root,
      hiddenInput,
      chips: root.querySelector(".diagnosis-chip-list"),
      input: root.querySelector(".diagnosis-picker-input"),
      dropdown: root.querySelector(".diagnosis-options"),
      items: dedupeItems(initialItems),
      visibleOptions: []
    };

    pickers[config.key] = picker;
    renderPicker(picker);
    ensureDiagnosisPickerStyles();

    picker.input.addEventListener("focus", () => scheduleSuggestions(picker, picker.input.value));
    picker.input.addEventListener("input", () => scheduleSuggestions(picker, picker.input.value));
    picker.input.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        const query = picker.input.value.trim();
        if (!query) return;
        const qNorm = stripLeadingCodes(query, "").toLowerCase();
        const exactMatch = picker.visibleOptions.find(item => stripLeadingCodes(item.label, item.code).toLowerCase() === qNorm);
        addItem(picker, exactMatch || { label: stripLeadingCodes(query, ""), code: "", system: "Custom" });
      } else if (event.key === "Backspace" && !picker.input.value && picker.items.length) {
        removeItem(picker, picker.items.length - 1);
      }
    });

    picker.dropdown.addEventListener("click", event => {
      const option = event.target.closest(".diagnosis-option[data-index]");
      if (!option) return;
      const item = picker.visibleOptions[Number(option.dataset.index)];
      addItem(picker, item);
    });

    picker.chips.addEventListener("click", event => {
      const button = event.target.closest(".diagnosis-chip-remove[data-index]");
      if (!button) return;
      removeItem(picker, Number(button.dataset.index));
    });

    document.addEventListener("click", event => {
      if (!root.contains(event.target)) hideSuggestions(picker);
    });
  }

  /**
   * ICD-11 MMS search results as HTML (for inline criteria / modals).
   */
  async function fetchIcd11CriteriaHtmlForLabel(label, preloadedToken) {
    let token = preloadedToken || null;
    if (!token) {
      try {
        const tokenResponse = await fetch("/icd11token");
        const tokenPayload = await tokenResponse.json();
        if (tokenPayload.error) {
          return `<p style="margin:0;color:#c33;">${escapeHtml(tokenPayload.error)}</p>`;
        }
        token = tokenPayload.access_token;
      } catch (error) {
        return '<p style="margin:0;color:#c33;">Unable to get the ICD-11 access token.</p>';
      }
    }

    try {
      const response = await fetch(
        `https://id.who.int/icd/release/11/2024-01/mms/search?q=${encodeURIComponent(label)}&flatResults=true`,
        {
          headers: {
            Authorization: "Bearer " + token,
            Accept: "application/json",
            "Accept-Language": "en",
            "API-Version": "v2"
          }
        }
      );
      const data = await response.json();
      const entities = Array.isArray(data.destinationEntities) ? data.destinationEntities.slice(0, 10) : [];
      if (!entities.length) {
        return '<p style="margin:0;color:#666;">No ICD-11 search results for this term.</p>';
      }
      return (
        `<div class="diagnosis-icd11-results">
          ${entities.map(entity => `
                <div class="diagnosis-icd11-result">
                  <div class="diagnosis-icd11-code">${escapeHtml(entity.theCode || "No code")}</div>
                  <div class="diagnosis-icd11-title">${icd11TitleToSafeHtml(entity.title || "")}</div>
                </div>
              `).join("")}
        </div>`
      );
    } catch (error) {
      return '<p style="margin:0;color:#c33;">Error fetching ICD-11 results for this diagnosis.</p>';
    }
  }

  function getStatesForClinicalSnapshotLabel(label) {
    if (!label || !String(label).trim()) {
      return clinicalStateSnapshotLists.default.slice();
    }
    const lower = String(label).toLowerCase();
    if (lower.includes("bipolar") || /\bf31\b/i.test(label)) {
      return clinicalStateSnapshotLists.bipolar.slice();
    }
    if ((lower.includes("depress") || lower.includes("mdd") || /\bf32\b/i.test(label)) && !lower.includes("bipolar")) {
      return clinicalStateSnapshotLists.depress.slice();
    }
    if (lower.includes("schizo") || lower.includes("psychotic") || /\bf20\b/i.test(label)) {
      return clinicalStateSnapshotLists.schizo.slice();
    }
    if (lower.includes("obsess") || lower.includes("ocd") || /\bf42\b/i.test(label)) {
      return clinicalStateSnapshotLists.ocd.slice();
    }
    if (lower.includes("anxiet") || lower.includes("panic") || lower.includes("gad") || /\bf41\b/i.test(label) || /\bf40\b/i.test(label)) {
      return clinicalStateSnapshotLists.anxiety.slice();
    }
    return clinicalStateSnapshotLists.default.slice();
  }

  /** Parse visit snapshot clinical states from hidden input (JSON array or legacy plain string). */
  function parseClinicalStateSnapshotRaw(raw) {
    if (raw == null || raw === "") return [];
    const s = String(raw).trim();
    if (!s) return [];
    try {
      const parsed = JSON.parse(s);
      if (Array.isArray(parsed)) {
        return parsed.filter(x => typeof x === "string" && x.trim()).map(x => x.trim());
      }
    } catch (e) {
      /* legacy single label */
    }
    return [s];
  }

  /** Single source of truth: write JSON array to #clinicalStateInput and notify listeners. */
  function commitClinicalStateHiddenValue(arr) {
    const hiddenInput = document.getElementById("clinicalStateInput");
    if (!hiddenInput) return;
    const clean = [];
    const seen = new Set();
    arr.forEach(s => {
      if (typeof s !== "string" || !s.trim()) return;
      const t = s.trim();
      if (seen.has(t)) return;
      seen.add(t);
      clean.push(t);
    });
    hiddenInput.value = clean.length > 0 ? JSON.stringify(clean) : "";
    hiddenInput.dispatchEvent(new CustomEvent("stateSync", { bubbles: true }));
    hiddenInput.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /** Keep inline pills and modal checkboxes aligned with the hidden input. */
  function syncClinicalStateVisualsFromHidden() {
    const hiddenInput = document.getElementById("clinicalStateInput");
    if (!hiddenInput) return;
    const currentSelected = parseClinicalStateSnapshotRaw(hiddenInput.value);

    document.querySelectorAll(".clinical-state-pill").forEach(btn => {
      const val = btn.getAttribute("data-value");
      if (!val) return;
      btn.classList.toggle("active", currentSelected.includes(val));
    });

    document.querySelectorAll(".clinical-state-checkbox").forEach(cb => {
      cb.checked = currentSelected.includes(cb.value);
    });
  }

  /** Multi-select snapshot pills; hidden input stores JSON.stringify(string[]). */
  function syncClinicalStateSnapshotPills() {
    const container = document.getElementById("clinicalStateContainer");
    const hiddenInput = document.getElementById("clinicalStateInput");
    if (!container || !hiddenInput) return;

    const provItems = getPickerItems("provisional");
    const refLabel = provItems.length ? provItems[provItems.length - 1].label : null;
    const states = getStatesForClinicalSnapshotLabel(refLabel);

    let currentSelected = parseClinicalStateSnapshotRaw(hiddenInput.value);
    currentSelected = currentSelected.filter(s => states.includes(s));
    hiddenInput.value = currentSelected.length > 0 ? JSON.stringify(currentSelected) : "";

    container.innerHTML = states.map(state => {
      const isActive = currentSelected.includes(state);
      return (
        `<button type="button" class="clinical-state-pill${isActive ? " active" : ""}" data-value="${escapeHtml(state)}">${escapeHtml(state)}</button>`
      );
    }).join("");

    container.querySelectorAll(".clinical-state-pill").forEach(btn => {
      btn.addEventListener("click", () => {
        const stateValue = btn.getAttribute("data-value");
        if (!stateValue) return;

        let selectedArray = parseClinicalStateSnapshotRaw(hiddenInput.value);
        if (selectedArray.includes(stateValue)) {
          selectedArray = selectedArray.filter(s => s !== stateValue);
        } else {
          selectedArray = selectedArray.concat([stateValue]);
        }

        commitClinicalStateHiddenValue(selectedArray);
      });
    });

    syncClinicalStateVisualsFromHidden();
    hiddenInput.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function initProvisionalInline(config) {
    const root = config.rootId ? document.getElementById(config.rootId) : null;
    const hiddenInput = document.getElementById(config.hiddenInputId);
    const searchInput = document.getElementById("provisionalSearch");
    const dropdown = document.getElementById("provisionalDropdown");
    const chipsEl = document.getElementById("provisionalChips");
    const criteriaBlock = document.getElementById("inlineCriteriaBlock");
    const criteriaContent = document.getElementById("inlineCriteriaContent");
    const activeLabel = document.getElementById("activeDiagnosisLabel");
    if (!root || !hiddenInput || !searchInput || !dropdown || !chipsEl || !criteriaBlock || !criteriaContent || !activeLabel) {
      return;
    }

    let items = dedupeItems(normalizeStoredItems(config.initialItems || hiddenInput.value));
    let activeIndex = items.length ? items.length - 1 : -1;
    let activeSystem = "ICD-11";
    let visibleOptions = [];
    let _searchSeq = 0;
    let _criteriaSeq = 0;

    function hideDropdown() {
      dropdown.innerHTML = "";
      dropdown.style.display = "none";
      visibleOptions = [];
    }

    function renderInlineSuggestions(query) {
      const trimmed = (query || "").trim();
      if (trimmed.length < 2) {
        hideDropdown();
        return;
      }

      _searchSeq += 1;
      const seq = _searchSeq;
      dropdown.style.display = "block";
      dropdown.innerHTML = `<div class="diagnosis-option diagnosis-option-empty">Searching ICD-11…</div>`;

      fetch(`/api/search_icd11?q=${encodeURIComponent(trimmed)}`)
        .then(response => response.json())
        .then(data => {
          const results = Array.isArray(data) ? data : [];
          if (seq !== _searchSeq) return;
          if (!results.length) {
            visibleOptions = [];
            dropdown.innerHTML = `<div class="diagnosis-option diagnosis-option-empty">No matching diagnosis found. Press Enter to add "${escapeHtml(trimmed)}"</div>`;
            dropdown.style.display = "block";
            return;
          }

          const matches = results
            .map(r => ({
              label: String(r.name || "").trim(),
              code: String(r.code || "").trim(),
              system: String(r.system || "ICD-11").trim() || "ICD-11"
            }))
            .filter(m => m.label);

          visibleOptions = matches;
          dropdown.innerHTML = matches.map((item, index) => {
            const codeHtml = item.code
              ? `<span class="diagnosis-option-code">${escapeHtml(item.code)}</span>`
              : "";
            return (
              `<button type="button" class="diagnosis-option" data-index="${index}">
        ${codeHtml}
        <span class="diagnosis-option-label">${escapeHtml(item.label)}</span>
        <span class="diagnosis-option-system">${escapeHtml(item.system || "ICD-11")}</span>
      </button>`
            );
          }).join("");
          dropdown.style.display = "block";
        })
        .catch(() => {
          if (seq !== _searchSeq) return;
          visibleOptions = [];
          dropdown.innerHTML = `<div class="diagnosis-option diagnosis-option-empty">No matching diagnosis found. Press Enter to add "${escapeHtml(trimmed)}"</div>`;
          dropdown.style.display = "block";
        });
    }

    let _suggestTimer = null;
    function scheduleInlineSuggestions(query) {
      const trimmed = (query || "").trim();
      if (trimmed.length < 2) {
        if (_suggestTimer) clearTimeout(_suggestTimer);
        hideDropdown();
        return;
      }
      if (_suggestTimer) clearTimeout(_suggestTimer);
      _suggestTimer = setTimeout(() => renderInlineSuggestions(query), 300);
    }

    function renderChips() {
      chipsEl.innerHTML = items.map((item, index) => {
        const chipLabel = item.code && item.label
          ? `${escapeHtml(item.code)} — ${escapeHtml(item.label)}`
          : escapeHtml(item.label);
        const activeClass = index === activeIndex ? " provisional-chip-active" : "";
        return (
          `<span class="diagnosis-chip${activeClass}" data-index="${index}" role="button" tabindex="0">
        <span class="diagnosis-chip-label">${chipLabel}</span>
        <button type="button" class="diagnosis-chip-remove" data-index="${index}" aria-label="Remove diagnosis">×</button>
      </span>`
        );
      }).join("");

      hiddenInput.value = serializeItems(items);
      pickers.provisional = { key: "provisional", items: items.slice() };
    }

    function emitProvisionalChanged() {
      syncClinicalStateSnapshotPills();
      document.dispatchEvent(new CustomEvent("diagnosis-picker:changed", {
        detail: {
          key: "provisional",
          items: items.slice()
        }
      }));
    }

    async function refreshCriteriaPanel() {
      _criteriaSeq += 1;
      const seq = _criteriaSeq;

      if (activeIndex < 0 || !items[activeIndex]) {
        criteriaBlock.classList.add("is-hidden");
        return;
      }

      criteriaBlock.classList.remove("is-hidden");
      const item = items[activeIndex];
      activeLabel.textContent = item.label;

      if (activeSystem === "ICD-11") {
        criteriaContent.innerHTML = '<p style="margin:0;color:#666;font-style:italic;">Loading ICD-11 reference…</p>';
        let token = null;
        try {
          const tokenResponse = await fetch("/icd11token");
          const tokenPayload = await tokenResponse.json();
          if (!tokenPayload.error && tokenPayload.access_token) {
            token = tokenPayload.access_token;
          }
        } catch (e) {
          token = null;
        }
        const html = await fetchIcd11CriteriaHtmlForLabel(item.label, token);
        if (seq !== _criteriaSeq) return;
        criteriaContent.innerHTML = html;
        return;
      }

      const key = resolveCriteriaDbKey(item.label);
      const field = activeSystem;
      const text = key && criteriaDB[key] && criteriaDB[key][field]
        ? criteriaDB[key][field]
        : null;
      if (seq !== _criteriaSeq) return;
      if (text) {
        criteriaContent.innerHTML = `<div class="diagnosis-criteria-body">${escapeHtml(text).replace(/\n/g, "<br>")}</div>`;
      } else {
        criteriaContent.innerHTML = `<p style="margin:0;color:#888;font-style:italic;">No curated ${escapeHtml(field)} criteria for "${escapeHtml(item.label)}". Try ICD-11 or the criteria modals below.</p>`;
      }
    }

    function setCriteriaToggleUi() {
      root.querySelectorAll(".provisional-criteria-toggle").forEach(btn => {
        const sys = btn.getAttribute("data-system");
        const on = sys === activeSystem;
        btn.classList.toggle("active", on);
        btn.setAttribute("aria-selected", on ? "true" : "false");
      });
    }

    function addProvisionalItem(raw) {
      const normalized = normalizeItem(raw);
      if (!normalized) return;
      const isDup = items.some(d => {
        if (normalized.code && d.code) return d.code === normalized.code;
        return d.label.toLowerCase() === normalized.label.toLowerCase();
      });
      if (isDup) return;

      items = dedupeItems(items.concat([normalized]));
      activeIndex = items.length - 1;
      searchInput.value = "";
      hideDropdown();
      renderChips();
      setCriteriaToggleUi();
      refreshCriteriaPanel();
      emitProvisionalChanged();
    }

    searchInput.addEventListener("focus", () => scheduleInlineSuggestions(searchInput.value));
    searchInput.addEventListener("input", () => scheduleInlineSuggestions(searchInput.value));
    searchInput.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        const query = searchInput.value.trim();
        if (!query) return;
        const qNorm = stripLeadingCodes(query, "").toLowerCase();
        const exactMatch = visibleOptions.find(opt => stripLeadingCodes(opt.label, opt.code).toLowerCase() === qNorm);
        addProvisionalItem(exactMatch || { label: stripLeadingCodes(query, ""), code: "", system: "Custom" });
      } else if (event.key === "Backspace" && !searchInput.value && items.length) {
        items.pop();
        activeIndex = items.length ? items.length - 1 : -1;
        renderChips();
        refreshCriteriaPanel();
        emitProvisionalChanged();
      }
    });

    dropdown.addEventListener("click", event => {
      const option = event.target.closest(".diagnosis-option[data-index]");
      if (!option || option.classList.contains("diagnosis-option-empty")) return;
      const item = visibleOptions[Number(option.dataset.index)];
      if (item) addProvisionalItem(item);
    });

    chipsEl.addEventListener("click", event => {
      const removeBtn = event.target.closest(".diagnosis-chip-remove");
      if (removeBtn) {
        event.stopPropagation();
        const removedIdx = Number(removeBtn.dataset.index);
        items.splice(removedIdx, 1);
        if (!items.length) activeIndex = -1;
        else if (activeIndex > removedIdx) activeIndex -= 1;
        else if (activeIndex === removedIdx) activeIndex = Math.min(removedIdx, items.length - 1);
        renderChips();
        refreshCriteriaPanel();
        emitProvisionalChanged();
        return;
      }
      const chip = event.target.closest(".diagnosis-chip[data-index]");
      if (!chip) return;
      activeIndex = Number(chip.dataset.index);
      renderChips();
      refreshCriteriaPanel();
    });

    root.querySelectorAll(".provisional-criteria-toggle").forEach(btn => {
      btn.addEventListener("click", () => {
        const sys = btn.getAttribute("data-system");
        if (!sys || sys === activeSystem) return;
        activeSystem = sys;
        setCriteriaToggleUi();
        refreshCriteriaPanel();
      });
    });

    document.addEventListener("click", event => {
      if (!root.contains(event.target)) hideDropdown();
    });

    ensureDiagnosisPickerStyles();
    pickers.provisional = { key: "provisional", items: items.slice() };
    renderChips();
    setCriteriaToggleUi();
    refreshCriteriaPanel();
    syncClinicalStateSnapshotPills();

    window.resyncProvisionalInlineFromHidden = function resyncProvisionalInlineFromHidden() {
      items = dedupeItems(normalizeStoredItems(hiddenInput.value));
      activeIndex = items.length ? items.length - 1 : -1;
      renderChips();
      setCriteriaToggleUi();
      refreshCriteriaPanel();
      syncClinicalStateSnapshotPills();
      document.dispatchEvent(new CustomEvent("diagnosis-picker:changed", {
        detail: { key: "provisional", items: items.slice() }
      }));
    };
  }

  function getPickerItems(key) {
    return pickers[key] ? pickers[key].items.slice() : [];
  }

  function getPickerText(key) {
    return getPickerItems(key).map(item => item.label).join(", ");
  }

  /** Provisional + differential, de-duplicated (for criteria modals & ICD-11). */
  function mergeDiagnosisItemsForCriteria() {
    return dedupeItems(getPickerItems("provisional").concat(getPickerItems("differential")));
  }

  function tabLabelForDiagnosis(label) {
    const s = String(label || "");
    return s.length > 36 ? s.slice(0, 34) + "…" : s;
  }

  function getCriteriaKey(label) {
    const text = String(label || "").toLowerCase();
    if (text.includes("depress") || text.includes("mdd")) return "depression";
    if (text.includes("schizo") || text.includes("f20")) return "schizophrenia";
    if (text.includes("bipolar") || text.includes("manic") || text.includes("mania") || text.includes("f31")) return "bipolar";
    if (text.includes("anxiet") || text.includes("gad") || text.includes("panic") || text.includes("f41") || text.includes("f40")) return "anxiety";
    return null;
  }

  function resolveCriteriaDbKey(label) {
    const direct = getCriteriaKey(label);
    if (direct) return direct;
    const lower = String(label || "").toLowerCase();
    return Object.keys(criteriaDB).find(dbk => lower.includes(dbk)) || null;
  }

  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = "block";
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = "none";
  }

  function renderTabs(modalId, title, tabs) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    const tabList = modal.querySelector(".diagnosis-modal-tabs");
    const body = modal.querySelector(".diagnosis-modal-panels");
    const titleEl = modal.querySelector(".diagnosis-modal-title");

    titleEl.textContent = title;
    tabList.innerHTML = "";
    body.innerHTML = "";

    if (!tabs.length) {
      tabList.innerHTML = '<button type="button" class="diagnosis-tab-button active">No diagnoses</button>';
      body.innerHTML = '<div class="diagnosis-tab-panel active"><p style="margin:0; color:#666;">No matching diagnoses available for this view.</p></div>';
      openModal(modalId);
      return;
    }

    tabs.forEach((tab, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `diagnosis-tab-button${index === 0 ? " active" : ""}`;
      button.textContent = tab.label;
      button.dataset.tabId = `${modalId}-tab-${index}`;

      const panel = document.createElement("div");
      panel.className = `diagnosis-tab-panel${index === 0 ? " active" : ""}`;
      panel.id = `${modalId}-tab-${index}`;
      panel.innerHTML = tab.content;

      button.addEventListener("click", () => {
        tabList.querySelectorAll(".diagnosis-tab-button").forEach(el => el.classList.remove("active"));
        body.querySelectorAll(".diagnosis-tab-panel").forEach(el => el.classList.remove("active"));
        button.classList.add("active");
        panel.classList.add("active");
      });

      tabList.appendChild(button);
      body.appendChild(panel);
    });

    openModal(modalId);
  }

  function openStaticCriteria(system) {
    const selected = mergeDiagnosisItemsForCriteria();
    const fieldKey = system === "ICD-10" ? "ICD-10" : "DSM-5";
    const tabs = selected.map(item => {
      const key = resolveCriteriaDbKey(item.label);
      const text = key && criteriaDB[key] && criteriaDB[key][fieldKey]
        ? criteriaDB[key][fieldKey]
        : `No curated ${system} criteria snippet is available for "${item.label}". Use ICD-11 search or your clinical reference.`;
      return {
        label: tabLabelForDiagnosis(item.label),
        content: `<div class="diagnosis-criteria-body">${escapeHtml(text).replace(/\n/g, "<br>")}</div>`
      };
    });

    const modalId = system === "ICD-10" ? "icd10CriteriaModal" : "dsm5CriteriaModal";
    renderTabs(modalId, `${system} Diagnostic View`, tabs);
  }

  function setIcd11PanelHtml(modalId, index, html) {
    const panel = document.getElementById(`${modalId}-tab-${index}`);
    if (panel) panel.innerHTML = html;
  }

  async function openIcd11Criteria() {
    const selected = mergeDiagnosisItemsForCriteria();
    if (!selected.length) {
      renderTabs("icd11CriteriaModal", "ICD-11 Diagnostic View", []);
      return;
    }

    const loadingTabs = selected.map(item => ({
      label: tabLabelForDiagnosis(item.label),
      content: '<p class="icd11-seq-status" style="margin:0; color:#666;">Waiting…</p>'
    }));
    renderTabs("icd11CriteriaModal", "ICD-11 Diagnostic View", loadingTabs);

    let token = null;
    try {
      const tokenResponse = await fetch("/icd11token");
      const tokenPayload = await tokenResponse.json();
      if (tokenPayload.error) {
        selected.forEach((_, i) => {
          setIcd11PanelHtml("icd11CriteriaModal", i, `<p style="margin:0; color:#c33;">${escapeHtml(tokenPayload.error)}</p>`);
        });
        return;
      }
      token = tokenPayload.access_token;
    } catch (error) {
      selected.forEach((_, i) => {
        setIcd11PanelHtml("icd11CriteriaModal", i, '<p style="margin:0; color:#c33;">Unable to get the ICD-11 access token.</p>');
      });
      return;
    }

    for (let i = 0; i < selected.length; i += 1) {
      const item = selected[i];
      setIcd11PanelHtml("icd11CriteriaModal", i, '<p class="icd11-seq-status" style="margin:0; color:#666;">Searching ICD-11…</p>');
      const html = await fetchIcd11CriteriaHtmlForLabel(item.label, token);
      setIcd11PanelHtml("icd11CriteriaModal", i, html);
    }
  }

  window.initializeDiagnosisPickers = function initializeDiagnosisPickers(config) {
    if (config.provisional) {
      if (config.provisional.inline) {
        initProvisionalInline(config.provisional);
      } else {
        initPicker(config.provisional);
      }
    }
    if (config.differential) {
      initPicker(config.differential);
    }
    document.dispatchEvent(new CustomEvent("diagnosis-picker:initialized"));
  };

  window.getDiagnosisFieldText = getPickerText;
  window.getDiagnosisFieldItems = getPickerItems;
  window.showIcd10CriteriaTabs = function () { openStaticCriteria("ICD-10"); };
  window.showDsm5CriteriaTabs = function () { openStaticCriteria("DSM-5"); };
  window.showIcd11CriteriaTabs = openIcd11Criteria;
  window.closeDiagnosisModal = closeModal;
  window.mergeDiagnosisItemsForCriteria = mergeDiagnosisItemsForCriteria;
  window.syncClinicalStateVisualsFromHidden = syncClinicalStateVisualsFromHidden;
  window.handleClinicalStateModalCheckbox = function handleClinicalStateModalCheckbox(cb) {
    if (!cb || !cb.value) return;
    const hiddenInput = document.getElementById("clinicalStateInput");
    if (!hiddenInput) return;
    let arr = parseClinicalStateSnapshotRaw(hiddenInput.value);
    if (cb.checked) {
      if (!arr.includes(cb.value)) arr = arr.concat([cb.value]);
    } else {
      arr = arr.filter(s => s !== cb.value);
    }
    commitClinicalStateHiddenValue(arr);
  };
  window.handlePopupCheckboxClick = window.handleClinicalStateModalCheckbox;

  document.addEventListener("DOMContentLoaded", () => {
    const hi = document.getElementById("clinicalStateInput");
    if (!hi) return;
    hi.addEventListener("stateSync", syncClinicalStateVisualsFromHidden);
    hi.addEventListener("change", syncClinicalStateVisualsFromHidden);
  });
})();
