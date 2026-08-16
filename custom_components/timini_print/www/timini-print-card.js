/**
 * TiMini Print Lovelace card.
 *
 * Bundled with the TiMini Print HACS integration and auto-registered
 * as a frontend resource (see __init__.py) - no manual "Add Resource"
 * step needed in most cases. Lets you print text or an image/PDF
 * straight from a dashboard, without visiting the add-on's own web UI
 * or creating any input_text/input_number helpers.
 *
 * Calls the integration's own services (timini_print.print_text,
 * timini_print.print_image_data) - never talks to the add-on directly.
 *
 * UI text is loaded from external JSON files under ./lang/ (e.g.
 * lang/en.json, lang/hu.json), fetched at runtime. Defaults to
 * English ("en") regardless of your Home Assistant language setting -
 * set `language: hu` (or de/pl/...) in the card's own YAML config to
 * pick a different one:
 *
 *   type: custom:timini-print-card
 *   language: hu
 *
 * A minimal English string set is embedded below purely as an
 * immediate-render placeholder (shown for the instant before the
 * fetch resolves) and as a last-resort fallback if the language file
 * can't be fetched at all - it is not meant to be edited to add
 * translations; add or edit files under lang/ instead.
 */

const EMBEDDED_EN_FALLBACK = {
  printer: "Printer",
  printerAuto: "Automatic (first found)",
  printerCustomPlaceholder: "or type it manually (e.g. TD-11308-ECF8)",
  printerModelPlaceholder: "force model (optional, e.g. for \"manual model required\" printers)",
  unsupportedLabel: "Unsupported / unrecognized device (let me pick its model manually)",
  modelSearchPlaceholderTemplate: "type to search {n} models...",
  noModelsFound: "no models found",
  scanBtn: "Scan for printers",
  haBluetoothBtn: "Use Home Assistant's Bluetooth list (no new scan)",
  loadingHaBluetooth: "Reading Home Assistant's Bluetooth cache...",
  foundHaBluetoothTemplate: "Added {added} new device(s) ({total} total known to Home Assistant)",
  scanning: "Scanning...",
  foundPrintersTemplate: "{n} printer(s) found",
  noPrintersFound: "No printers found.",
  printTextLabel: "Print text",
  textColumns: "Characters per line (fewer = bigger text)",
  autoPlaceholder: "auto",
  printDarkness: "Print darkness (1-5)",
  textPlaceholder: "Type something...",
  printTextBtn: "Print text",
  imageLabel: "Image (.png .jpg .jpeg .gif .bmp) or PDF",
  threshold: "Brightness adjustment (image preview)",
  pdfNoPreview: "PDF selected - no black/white preview, all pages print unchanged.",
  printImageBtn: "Print image/PDF",
  emptyTextError: "Type some text first.",
  noFileError: "Choose a file first.",
  printing: "Printing...",
  uploading: "Uploading and printing...",
  done: "Done!",
  error: "Error: ",
  fileReadError: "Could not read the file.",
};

const LANG_CACHE = {};

async function loadLang(lang) {
  if (LANG_CACHE[lang]) return LANG_CACHE[lang];
  try {
    const resp = await fetch(`/timini_print_frontend/lang/${lang}.json`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    LANG_CACHE[lang] = data;
    return data;
  } catch (err) {
    console.warn(`timini-print-card: could not load language '${lang}':`, err);
    if (lang !== "en") return loadLang("en");
    return EMBEDDED_EN_FALLBACK;
  }
}

class TiminiPrintCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._selectedFile = null;
    this._strings = EMBEDDED_EN_FALLBACK;
    this._render();
    const lang = (this._config.language || "en").toLowerCase();
    loadLang(lang).then((strings) => {
      this._strings = strings;
      this._render();
    });
  }

  set hass(hass) {
    this._hass = hass;
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return { title: "TiMini Print" };
  }

  _t() {
    return this._strings;
  }

  _render() {
    const t = this._t();
    const title = this._config.title || "TiMini Print";
    this.innerHTML = `
      <ha-card header="${title}">
        <style>
          .timini-body { padding: 0 16px 16px; }
          .timini-row { margin-bottom: 10px; }
          .timini-row label {
            display: block; font-size: 0.85em; margin-bottom: 4px;
            color: var(--secondary-text-color);
          }
          .timini-row textarea, .timini-row input[type="text"], .timini-row input[type="number"] {
            width: 100%; box-sizing: border-box; padding: 8px;
            border-radius: 6px; border: 1px solid var(--divider-color, #ccc);
            background: var(--card-background-color); color: var(--primary-text-color);
            font-family: inherit; font-size: 0.95em;
          }
          .timini-inline { display: flex; gap: 10px; align-items: flex-end; }
          .timini-inline > div { flex: 1; }
          .timini-inline .timini-fontsize { flex: 0 0 90px; }
          .timini-btn {
            display: inline-block; margin-top: 6px; padding: 8px 16px;
            border-radius: 8px; border: none; cursor: pointer;
            background: var(--primary-color); color: var(--text-primary-color, #fff);
            font-size: 0.9em; font-weight: 500;
          }
          .timini-btn:active { opacity: .85; }
          .timini-status {
            margin-top: 10px; font-size: 0.85em; color: var(--secondary-text-color);
            white-space: pre-wrap; word-break: break-word;
          }
          .timini-status.error { color: var(--error-color, #db4437); }
          hr { border: none; border-top: 1px solid var(--divider-color, #ccc); margin: 16px 0; }
        </style>
        <div class="timini-body">
          <div class="timini-row">
            <label for="timini-printer-select">${t.printer}</label>
            <div style="display:flex; gap:8px; margin-bottom:6px;">
              <select id="timini-printer-select" style="flex:1; min-width:0; padding:8px; border-radius:6px; border:1px solid var(--divider-color,#ccc); background:var(--card-background-color); color:var(--primary-text-color); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                <option value="">${t.printerAuto}</option>
              </select>
              <button class="timini-btn" id="timini-scan-btn" style="margin-top:0; flex:0 0 auto;">${t.scanBtn}</button>
            </div>
            <button class="timini-btn" id="timini-ha-bt-btn" style="width:100%; margin-bottom:6px;">${t.haBluetoothBtn}</button>
            <input type="text" id="timini-printer" placeholder="${t.printerCustomPlaceholder}">
            <label style="display:flex; align-items:center; gap:6px; font-size:0.82em; color:var(--secondary-text-color); margin-top:8px; cursor:pointer;">
              <input type="checkbox" id="timini-unsupported-checkbox">
              ${t.unsupportedLabel}
            </label>
            <div id="timini-model-row" style="display:none; margin-top:6px;">
              <input type="text" id="timini-printer-model" list="timini-model-list" placeholder="${t.printerModelPlaceholder}">
              <datalist id="timini-model-list"></datalist>
            </div>
          </div>

          <div class="timini-row">
            <label for="timini-text">${t.printTextLabel}</label>
            <textarea id="timini-text" rows="3" placeholder="${t.textPlaceholder}"></textarea>
          </div>
          <div class="timini-row timini-inline">
            <div class="timini-fontsize">
              <label for="timini-columns">${t.textColumns}</label>
              <input type="number" id="timini-columns" min="1" max="200" step="1" placeholder="${t.autoPlaceholder}">
            </div>
            <div class="timini-fontsize">
              <label for="timini-darkness-text">${t.printDarkness}</label>
              <input type="number" id="timini-darkness-text" min="1" max="5" step="1" value="3">
            </div>
          </div>
          <button class="timini-btn" id="timini-print-text-btn">${t.printTextBtn}</button>

          <hr>

          <div class="timini-row">
            <label for="timini-file">${t.imageLabel}</label>
            <input type="file" id="timini-file" accept=".png,.jpg,.jpeg,.gif,.bmp,.pdf">
          </div>
          <canvas id="timini-preview-canvas" style="max-width:100%; border-radius:8px; display:none; margin-bottom:8px;"></canvas>
          <div id="timini-pdf-label" class="hint" style="display:none;">${t.pdfNoPreview}</div>
          <div id="timini-darkness-row" style="display:none; margin-bottom:10px;">
            <label for="timini-darkness">${t.threshold}: <span id="timini-darkness-value">0</span></label>
            <input type="range" id="timini-darkness" min="-120" max="120" step="5" value="0" style="width:100%;">
          </div>
          <div class="timini-row timini-fontsize">
            <label for="timini-darkness-image">${t.printDarkness}</label>
            <input type="number" id="timini-darkness-image" min="1" max="5" step="1" value="3">
          </div>
          <button class="timini-btn" id="timini-print-image-btn">${t.printImageBtn}</button>

          <div class="timini-status" id="timini-status"></div>
        </div>
      </ha-card>
    `;

    this.querySelector("#timini-print-text-btn").addEventListener("click", () => this._printText());
    this.querySelector("#timini-print-image-btn").addEventListener("click", () => this._printImage());
    this.querySelector("#timini-darkness").addEventListener("input", (e) => {
      this.querySelector("#timini-darkness-value").innerText = e.target.value;
      this._applyThreshold();
    });
    this.querySelector("#timini-file").addEventListener("change", (e) => this._onFileChosen(e));
    this.querySelector("#timini-scan-btn").addEventListener("click", () => this._scan());
    this.querySelector("#timini-ha-bt-btn").addEventListener("click", () => this._loadHaBluetoothDevices());
    this.querySelector("#timini-printer-select").addEventListener("change", (e) => {
      this.querySelector("#timini-printer").value = e.target.value;
    });
    this.querySelector("#timini-unsupported-checkbox").addEventListener("change", () => this._onUnsupportedToggle());
  }

  _setStatus(msg, isError) {
    const el = this.querySelector("#timini-status");
    if (!el) return;
    el.innerText = msg;
    el.classList.toggle("error", !!isError);
  }

  _onFileChosen(event) {
    const file = event.target.files[0];
    this._selectedFile = file || null;
    this._selectedImg = null;
    this._isPdf = false;
    const canvas = this.querySelector("#timini-preview-canvas");
    const pdfLabel = this.querySelector("#timini-pdf-label");
    const darknessRow = this.querySelector("#timini-darkness-row");
    canvas.style.display = "none";
    pdfLabel.style.display = "none";
    darknessRow.style.display = "none";
    if (!file) return;
    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
      this._isPdf = true;
      pdfLabel.style.display = "block";
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        this._selectedImg = img;
        darknessRow.style.display = "block";
        this._applyThreshold();
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }

  _ditherImageData(imgData, brightnessOffset) {
    const w = imgData.width, h = imgData.height;
    const d = imgData.data;
    const gray = new Float32Array(w * h);
    for (let i = 0; i < w * h; i++) {
      const r = d[i * 4], g = d[i * 4 + 1], b = d[i * 4 + 2];
      let v = 0.299 * r + 0.587 * g + 0.114 * b + brightnessOffset;
      gray[i] = Math.max(0, Math.min(255, v));
    }
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = y * w + x;
        const old = gray[idx];
        const newVal = old < 128 ? 0 : 255;
        const err = old - newVal;
        gray[idx] = newVal;
        if (x + 1 < w) gray[idx + 1] += err * 7 / 16;
        if (y + 1 < h) {
          if (x > 0) gray[idx + w - 1] += err * 3 / 16;
          gray[idx + w] += err * 5 / 16;
          if (x + 1 < w) gray[idx + w + 1] += err * 1 / 16;
        }
      }
    }
    for (let i = 0; i < w * h; i++) {
      d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = gray[i];
    }
  }

  _applyThreshold() {
    if (!this._selectedImg) return;
    const canvas = this.querySelector("#timini-preview-canvas");
    const brightnessOffset = parseInt(this.querySelector("#timini-darkness").value, 10);
    const maxWidth = 400;
    const scale = Math.min(1, maxWidth / this._selectedImg.naturalWidth);
    const w = Math.round(this._selectedImg.naturalWidth * scale);
    const h = Math.round(this._selectedImg.naturalHeight * scale);
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(this._selectedImg, 0, 0, w, h);
    const imgData = ctx.getImageData(0, 0, w, h);
    this._ditherImageData(imgData, brightnessOffset);
    ctx.putImageData(imgData, 0, 0);
    canvas.style.display = "block";
  }

  async _scan() {
    const t = this._t();
    this._setStatus(t.scanning);
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "call_service",
        domain: "timini_print",
        service: "scan",
        service_data: {},
        return_response: true,
      });
      const printers = (result && result.response && result.response.printers) || [];
      const select = this.querySelector("#timini-printer-select");
      while (select.options.length > 1) select.remove(1);
      printers.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        const shortLabel = p.label.length > 40 ? p.label.slice(0, 40) + "…" : p.label;
        opt.textContent = shortLabel;
        opt.title = p.label;
        select.appendChild(opt);
      });
      const foundMsg = t.foundPrintersTemplate.replace("{n}", printers.length);
      this._setStatus(printers.length ? foundMsg : t.noPrintersFound);
    } catch (err) {
      this._setStatus(t.error + (err.message || err), true);
    }
  }

  async _loadHaBluetoothDevices() {
    const t = this._t();
    this._setStatus(t.loadingHaBluetooth);
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "call_service",
        domain: "timini_print",
        service: "list_ha_bluetooth_devices",
        service_data: {},
        return_response: true,
      });
      const response = (result && result.response) || {};
      if (response.error) {
        this._setStatus(t.error + response.error, true);
        return;
      }
      const devices = response.devices || [];
      const select = this.querySelector("#timini-printer-select");
      const existing = new Set(Array.from(select.options).map((o) => o.value));
      let added = 0;
      devices.forEach((d) => {
        if (existing.has(d.address)) return;
        const opt = document.createElement("option");
        opt.value = d.address;
        const label = `[HA] ${d.name} (${d.address}) ${d.rssi}dBm`;
        opt.textContent = label.length > 40 ? label.slice(0, 40) + "…" : label;
        opt.title = label;
        select.appendChild(opt);
        existing.add(d.address);
        added += 1;
      });
      const foundMsg = t.foundHaBluetoothTemplate
        .replace("{added}", added)
        .replace("{total}", devices.length);
      this._setStatus(devices.length ? foundMsg : t.noPrintersFound);
    } catch (err) {
      this._setStatus(t.error + (err.message || err), true);
    }
  }

  async _ensureModelListLoaded() {
    if (this._modelListCache) return this._modelListCache;
    const result = await this._hass.connection.sendMessagePromise({
      type: "call_service",
      domain: "timini_print",
      service: "list_models",
      service_data: {},
      return_response: true,
    });
    const models = (result && result.response && result.response.models) || [];
    this._modelListCache = models;
    const datalist = this.querySelector("#timini-model-list");
    datalist.innerHTML = "";
    models.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.key;
      opt.label = m.label;
      datalist.appendChild(opt);
    });
    return models;
  }

  async _onUnsupportedToggle() {
    const t = this._t();
    const checked = this.querySelector("#timini-unsupported-checkbox").checked;
    const row = this.querySelector("#timini-model-row");
    row.style.display = checked ? "block" : "none";
    if (checked) {
      const input = this.querySelector("#timini-printer-model");
      try {
        const models = await this._ensureModelListLoaded();
        input.placeholder = models.length
          ? t.modelSearchPlaceholderTemplate.replace("{n}", models.length)
          : t.noModelsFound;
      } catch (err) {
        this._setStatus(t.error + (err.message || err), true);
      }
    }
  }

  async _printText() {
    const t = this._t();
    const text = this.querySelector("#timini-text").value;
    if (!text) {
      this._setStatus(t.emptyTextError, true);
      return;
    }
    const columnsRaw = this.querySelector("#timini-columns").value;
    const darknessRaw = this.querySelector("#timini-darkness-text").value;
    const printer = this.querySelector("#timini-printer").value;
    const printerModel = this.querySelector("#timini-printer-model").value;
    const data = { message: text };
    if (columnsRaw) data.text_columns = parseInt(columnsRaw, 10);
    if (darknessRaw) data.darkness = parseInt(darknessRaw, 10);
    if (printer) data.printer = printer;
    if (printerModel) data.printer_model = printerModel;

    this._setStatus(t.printing);
    try {
      await this._hass.callService("timini_print", "print_text", data);
      this._setStatus(t.done);
    } catch (err) {
      this._setStatus(t.error + (err.message || err), true);
    }
  }

  async _printImage() {
    const t = this._t();
    if (!this._selectedFile) {
      this._setStatus(t.noFileError, true);
      return;
    }
    const printer = this.querySelector("#timini-printer").value;
    const file = this._selectedFile;

    const send = (base64, filename) => {
      const data = { image_b64: base64, filename };
      if (printer) data.printer = printer;
      const darknessRaw = this.querySelector("#timini-darkness-image").value;
      if (darknessRaw) data.darkness = parseInt(darknessRaw, 10);
      const printerModel = this.querySelector("#timini-printer-model").value;
      if (printerModel) data.printer_model = printerModel;
      this._hass
        .callService("timini_print", "print_image_data", data)
        .then(() => this._setStatus(t.done))
        .catch((err) => this._setStatus(t.error + (err.message || err), true));
    };

    this._setStatus(t.uploading);
    if (this._isPdf) {
      const reader = new FileReader();
      reader.onload = (e) => send(String(e.target.result).split(",")[1], file.name);
      reader.onerror = () => this._setStatus(t.fileReadError, true);
      reader.readAsDataURL(file);
    } else {
      const canvas = this.querySelector("#timini-preview-canvas");
      const dataUrl = canvas.toDataURL("image/png");
      const base64 = dataUrl.split(",")[1];
      send(base64, file.name.replace(/\.[^.]+$/, "") + ".png");
    }
  }
}

customElements.define("timini-print-card", TiminiPrintCard);

// Register in the card picker's "Manual"/custom card list.
window.customCards = window.customCards || [];
window.customCards.push({
  type: "timini-print-card",
  name: "TiMini Print",
  description: "Print text or an image/PDF via the TiMini Print add-on.",
});
