/* ==========================================================================
   Unit Converter — front-end logic
   Talks to the Flask API (/api/categories, /api/units/<cat>, /api/convert),
   manages the two readout ports, the swap dial, the conversion log, and
   all client-side error handling.
   ========================================================================== */

(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // DOM references
  // ---------------------------------------------------------------------
  const categoryRail = document.getElementById("categoryRail");
  const fromSelect = document.getElementById("fromUnit");
  const toSelect = document.getElementById("toUnit");
  const inputValue = document.getElementById("inputValue");
  const swapBtn = document.getElementById("swapBtn");
  const readout = document.getElementById("resultReadout");
  const resultText = document.getElementById("resultText");
  const copyBtn = document.getElementById("copyBtn");
  const formulaLine = document.getElementById("formulaLine");
  const errorLine = document.getElementById("errorLine");
  const historyList = document.getElementById("historyList");
  const historyEmpty = document.getElementById("historyEmpty");
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");

  // ---------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------
  let currentCategory = "length";
  let history = [];
  let debounceTimer = null;

  const HISTORY_KEY = "unitConverterHistory.v1";
  const MAX_HISTORY = 10;

  // Sensible starting unit pairs per category, purely for a nicer first
  // impression — any pair can be picked afterwards.
  const DEFAULT_PAIRS = {
    length: ["m", "ft"],
    weight: ["kg", "lb"],
    temperature: ["c", "f"],
    volume: ["l", "gal"],
    area: ["m2", "ft2"],
    speed: ["kph", "mph"],
    time: ["hr", "min"],
    data: ["mb", "gb"],
    energy: ["kcal", "kj"],
    pressure: ["bar", "psi"],
  };

  // ---------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------

  function debounce(fn, delay) {
    return function (...args) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => fn.apply(null, args), delay);
    };
  }

  function formatNumber(n) {
    if (typeof n !== "number" || !isFinite(n)) return "—";
    if (n === 0) return "0";

    const abs = Math.abs(n);
    if (abs < 1e-6 || abs >= 1e12) {
      return n.toExponential(6);
    }

    let rounded = parseFloat(n.toPrecision(10));
    let str = String(rounded);

    if (!str.includes("e")) {
      const parts = str.split(".");
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
      str = parts.join(".");
    }
    return str;
  }

  function showError(message) {
    errorLine.textContent = message || "";
  }

  function clearError() {
    errorLine.textContent = "";
  }

  function setLoading(isLoading) {
    readout.classList.toggle("is-loading", isLoading);
  }

  async function fetchJSON(url, options) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (networkErr) {
      throw new Error("Could not reach the server. Make sure app.py is running.");
    }
    let data;
    try {
      data = await response.json();
    } catch (parseErr) {
      throw new Error("The server returned an unexpected response.");
    }
    if (!response.ok) {
      throw new Error(data.error || "Something went wrong.");
    }
    return data;
  }

  // ---------------------------------------------------------------------
  // Categories
  // ---------------------------------------------------------------------

  async function loadCategories() {
    try {
      const data = await fetchJSON("/api/categories");
      renderCategories(data.categories);
      await selectCategory(currentCategory, { skipRailUpdate: true });
      highlightActiveCategory();
    } catch (err) {
      showError(err.message);
    }
  }

  function renderCategories(categories) {
    categoryRail.innerHTML = "";
    categories.forEach((cat) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "category-pill";
      btn.dataset.key = cat.key;
      btn.textContent = cat.label;
      btn.addEventListener("click", () => selectCategory(cat.key));
      categoryRail.appendChild(btn);
    });
  }

  function highlightActiveCategory() {
    const pills = categoryRail.querySelectorAll(".category-pill");
    pills.forEach((p) => {
      p.classList.toggle("active", p.dataset.key === currentCategory);
    });
  }

  async function selectCategory(key, opts) {
    currentCategory = key;
    if (!opts || !opts.skipRailUpdate) {
      highlightActiveCategory();
    }
    clearError();
    await loadUnits(key);
    highlightActiveCategory();
    doConvert();
  }

  // ---------------------------------------------------------------------
  // Units
  // ---------------------------------------------------------------------

  async function loadUnits(category) {
    try {
      const data = await fetchJSON(`/api/units/${encodeURIComponent(category)}`);
      populateUnitSelect(fromSelect, data.units);
      populateUnitSelect(toSelect, data.units);

      const defaults = DEFAULT_PAIRS[category];
      if (defaults && unitExists(data.units, defaults[0]) && unitExists(data.units, defaults[1])) {
        fromSelect.value = defaults[0];
        toSelect.value = defaults[1];
      } else if (data.units.length > 1) {
        fromSelect.value = data.units[0].key;
        toSelect.value = data.units[1].key;
      }
    } catch (err) {
      showError(err.message);
    }
  }

  function unitExists(units, key) {
    return units.some((u) => u.key === key);
  }

  function populateUnitSelect(select, units) {
    select.innerHTML = "";
    units.forEach((u) => {
      const opt = document.createElement("option");
      opt.value = u.key;
      opt.textContent = u.label;
      select.appendChild(opt);
    });
  }

  // ---------------------------------------------------------------------
  // Conversion
  // ---------------------------------------------------------------------

  const debouncedConvert = debounce(doConvert, 300);

  async function doConvert() {
    clearError();
    const rawValue = inputValue.value.trim();

    if (rawValue === "") {
      resultText.textContent = "—";
      formulaLine.innerHTML = "&nbsp;";
      return;
    }

    if (isNaN(Number(rawValue))) {
      showError("Please enter a valid number.");
      resultText.textContent = "—";
      return;
    }

    const fromUnit = fromSelect.value;
    const toUnit = toSelect.value;
    if (!fromUnit || !toUnit) return;

    setLoading(true);
    try {
      const data = await fetchJSON("/api/convert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: currentCategory,
          from_unit: fromUnit,
          to_unit: toUnit,
          value: rawValue,
        }),
      });

      resultText.textContent = formatNumber(data.result);
      updateFormulaLine(data);
      addHistoryEntry(data);
    } catch (err) {
      showError(err.message);
      resultText.textContent = "—";
    } finally {
      setLoading(false);
    }
  }

  function currentLabel(select) {
    const opt = select.options[select.selectedIndex];
    return opt ? opt.textContent : select.value;
  }

  function updateFormulaLine(data) {
    if (currentCategory === "temperature") {
      formulaLine.textContent = "Temperature scales are offset, not simple multiples of one another.";
      return;
    }
    if (data.input === 0) {
      formulaLine.innerHTML = "&nbsp;";
      return;
    }
    const rate = data.result / data.input;
    formulaLine.textContent = `1 ${currentLabel(fromSelect)} = ${formatNumber(rate)} ${currentLabel(toSelect)}`;
  }

  // ---------------------------------------------------------------------
  // Swap
  // ---------------------------------------------------------------------

  function swapUnits() {
    const tmp = fromSelect.value;
    fromSelect.value = toSelect.value;
    toSelect.value = tmp;
    doConvert();
  }

  // ---------------------------------------------------------------------
  // Copy
  // ---------------------------------------------------------------------

  async function copyResult() {
    const text = resultText.textContent;
    if (!text || text === "—") return;

    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      // Fallback for browsers/contexts without Clipboard API access.
      const helper = document.createElement("textarea");
      helper.value = text;
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.appendChild(helper);
      helper.select();
      try {
        document.execCommand("copy");
      } catch (fallbackErr) {
        showError("Could not copy to clipboard.");
      }
      document.body.removeChild(helper);
    }

    copyBtn.textContent = "Copied!";
    copyBtn.classList.add("copied");
    setTimeout(() => {
      copyBtn.textContent = "Copy";
      copyBtn.classList.remove("copied");
    }, 1400);
  }

  // ---------------------------------------------------------------------
  // History
  // ---------------------------------------------------------------------

  function loadHistory() {
    try {
      const stored = localStorage.getItem(HISTORY_KEY);
      history = stored ? JSON.parse(stored) : [];
      if (!Array.isArray(history)) history = [];
    } catch (err) {
      history = [];
    }
    renderHistory();
  }

  function saveHistory() {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch (err) {
      // Storage may be unavailable (private browsing, quota). Fail silently;
      // history simply won't persist across reloads.
    }
  }

  function addHistoryEntry(data) {
    const entry = {
      category: currentCategory,
      fromLabel: currentLabel(fromSelect),
      toLabel: currentLabel(toSelect),
      input: data.input,
      result: data.result,
      time: new Date().toISOString(),
    };
    history.unshift(entry);
    if (history.length > MAX_HISTORY) history.length = MAX_HISTORY;
    saveHistory();
    renderHistory();
  }

  function renderHistory() {
    historyList.querySelectorAll(".history-entry").forEach((el) => el.remove());

    if (history.length === 0) {
      historyEmpty.style.display = "";
      return;
    }
    historyEmpty.style.display = "none";

    history.forEach((entry) => {
      const li = document.createElement("li");
      li.className = "history-entry";

      const left = document.createElement("span");
      left.className = "h-convert";
      left.textContent = `${formatNumber(entry.input)} ${entry.fromLabel} → ${formatNumber(entry.result)} ${entry.toLabel}`;

      const right = document.createElement("span");
      right.className = "h-time";
      right.textContent = formatTime(entry.time);

      li.appendChild(left);
      li.appendChild(right);
      historyList.appendChild(li);
    });
  }

  function formatTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch (err) {
      return "";
    }
  }

  function clearHistory() {
    history = [];
    saveHistory();
    renderHistory();
  }

  // ---------------------------------------------------------------------
  // Events
  // ---------------------------------------------------------------------

  inputValue.addEventListener("input", debouncedConvert);
  inputValue.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      clearTimeout(debounceTimer);
      doConvert();
    } else if (e.key === "Escape") {
      inputValue.value = "";
      resultText.textContent = "—";
      formulaLine.innerHTML = "&nbsp;";
      clearError();
    }
  });

  fromSelect.addEventListener("change", doConvert);
  toSelect.addEventListener("change", doConvert);
  swapBtn.addEventListener("click", swapUnits);
  copyBtn.addEventListener("click", copyResult);
  clearHistoryBtn.addEventListener("click", clearHistory);

  // ---------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------

  loadHistory();
  loadCategories();
})();
