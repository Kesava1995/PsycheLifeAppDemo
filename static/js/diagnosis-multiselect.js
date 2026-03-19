(function () {
  const catalogState = {
    promise: null,
    items: [],
  };

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
      code: "",
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

  async function loadCatalog() {
    if (!catalogState.promise) {
      catalogState.promise = fetch("/static/data/diagnosis_catalog.json")
        .then(response => response.json())
        .then(items => {
          catalogState.items = Array.isArray(items)
            ? items
              .map(entry => {
                const label = String(entry.label || "").trim();
                if (!label) return null;
                return {
                  label,
                  code: String(entry.code || "").trim(),
                  system: String(entry.system || "Custom").trim() || "Custom"
                };
              })
              .filter(Boolean)
            : [];
          return catalogState.items;
        })
        .catch(() => {
          catalogState.items = [];
          return catalogState.items;
        });
    }
    return catalogState.promise;
  }

  function serializeItems(items) {
    return JSON.stringify(items.map(item => ({
      label: item.label,
      code: "",
      system: item.system || "Custom"
    })));
  }

  function filterCatalogItems(items, query) {
    const trimmed = (query || "").trim().toLowerCase();
    if (!trimmed) return items.slice(0, 12);
    return items
      .filter(item => {
        const haystack = [item.label, item.code, item.system].join(" ").toLowerCase();
        return haystack.includes(trimmed);
      })
      .slice(0, 12);
  }

  function renderPicker(picker) {
    picker.chips.innerHTML = picker.items.map((item, index) => {
      const sys = escapeHtml(item.system || "Custom");
      return (
        `<span class="diagnosis-chip" title="${sys}">
        <span class="diagnosis-chip-label">${escapeHtml(item.label)}</span>
        <button type="button" class="diagnosis-chip-remove" data-index="${index}" aria-label="Remove diagnosis">×</button>
      </span>`
      );
    }).join("");

    picker.hiddenInput.value = serializeItems(picker.items);
    picker.root.dataset.hasItems = picker.items.length ? "true" : "false";
  }

  function renderSuggestions(picker, query) {
    const matches = filterCatalogItems(catalogState.items, query);
    if (!matches.length) {
      picker.dropdown.innerHTML = `<div class="diagnosis-option diagnosis-option-empty">No matching diagnosis found. Press Enter to add "${escapeHtml(query.trim())}"</div>`;
      picker.dropdown.style.display = query.trim() ? "block" : "none";
      return;
    }

    picker.dropdown.innerHTML = matches.map((item, index) => (
      `<button type="button" class="diagnosis-option" data-index="${index}">
        <span class="diagnosis-option-label">${escapeHtml(item.label)}</span>
        <span class="diagnosis-option-system">${escapeHtml(item.system || "Custom")}</span>
      </button>`
    )).join("");
    picker.visibleOptions = matches;
    picker.dropdown.style.display = "block";
  }

  function hideSuggestions(picker) {
    picker.dropdown.style.display = "none";
    picker.visibleOptions = [];
  }

  function addItem(picker, item) {
    const normalized = normalizeItem(item);
    if (!normalized) return;
    picker.items = dedupeItems(picker.items.concat([normalized]));
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

    const picker = {
      key: config.key,
      root,
      hiddenInput,
      chips: root.querySelector(".diagnosis-chip-list"),
      input: root.querySelector(".diagnosis-picker-input"),
      dropdown: root.querySelector(".diagnosis-options"),
      items: dedupeItems(normalizeStoredItems(config.initialItems || hiddenInput.value)),
      visibleOptions: []
    };

    pickers[config.key] = picker;
    renderPicker(picker);

    picker.input.addEventListener("focus", () => renderSuggestions(picker, picker.input.value));
    picker.input.addEventListener("input", () => renderSuggestions(picker, picker.input.value));
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
      const key = getCriteriaKey(item.label);
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
      try {
        const response = await fetch(`https://id.who.int/icd/release/11/2024-01/mms/search?q=${encodeURIComponent(item.label)}&flatResults=true`, {
          headers: {
            Authorization: "Bearer " + token,
            Accept: "application/json",
            "Accept-Language": "en",
            "API-Version": "v2"
          }
        });
        const data = await response.json();
        const entities = Array.isArray(data.destinationEntities) ? data.destinationEntities.slice(0, 10) : [];
        if (!entities.length) {
          setIcd11PanelHtml("icd11CriteriaModal", i, '<p style="margin:0; color:#666;">No ICD-11 search results for this term.</p>');
        } else {
          const content = `
            <div class="diagnosis-icd11-results">
              ${entities.map(entity => `
                <div class="diagnosis-icd11-result">
                  <div class="diagnosis-icd11-code">${escapeHtml(entity.theCode || "No code")}</div>
                  <div class="diagnosis-icd11-title">${icd11TitleToSafeHtml(entity.title || "")}</div>
                </div>
              `).join("")}
            </div>
          `;
          setIcd11PanelHtml("icd11CriteriaModal", i, content);
        }
      } catch (error) {
        setIcd11PanelHtml("icd11CriteriaModal", i, '<p style="margin:0; color:#c33;">Error fetching ICD-11 results for this diagnosis.</p>');
      }
    }
  }

  window.initializeDiagnosisPickers = async function initializeDiagnosisPickers(config) {
    await loadCatalog();
    initPicker(config.provisional);
    initPicker(config.differential);
    document.dispatchEvent(new CustomEvent("diagnosis-picker:initialized"));
  };

  window.getDiagnosisFieldText = getPickerText;
  window.getDiagnosisFieldItems = getPickerItems;
  window.showIcd10CriteriaTabs = function () { openStaticCriteria("ICD-10"); };
  window.showDsm5CriteriaTabs = function () { openStaticCriteria("DSM-5"); };
  window.showIcd11CriteriaTabs = openIcd11Criteria;
  window.closeDiagnosisModal = closeModal;
  window.mergeDiagnosisItemsForCriteria = mergeDiagnosisItemsForCriteria;
})();
