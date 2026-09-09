// All document/OCR content is inserted with textContent, never HTML.
let firstPhoto = null;
let secondPhoto = null;
let manualRegions = [];
let selectingArea = false;
let selectionStart = null;
let selectedBox = null;
let exportUrls = [];
const recoverySection = document.createElement("section");
recoverySection.id = "recovery";
recoverySection.className = "recovery";
recoverySection.hidden = true;
recoverySection.setAttribute("aria-labelledby", "recovery-title");
recoverySection.innerHTML = `
  <div class="recovery-heading"><div><span class="section-label">BUKTI / PEMULIHAN TEKS</span><h2 id="recovery-title">Ada sumbernya. Bisa diperiksa.</h2></div><p id="recovery-summary" aria-live="polite"></p></div>
  <div class="evidence-layout">
    <div class="evidence-page-panel">
      <div class="evidence-toolbar"><span>HALAMAN &amp; AREA PEMULIHAN</span><button id="mark-area" aria-pressed="false">Tandai area</button></div>
      <p id="selection-help">Klik area berwarna untuk melihat sumbernya. Ada yang terlewat? Tandai sendiri.</p>
      <div id="evidence-page"><img id="evidence-image" alt="Halaman dengan penanda area pemulihan" draggable="false"><svg id="evidence-overlay" aria-label="Area pada dokumen"></svg></div>
      <div class="area-legend"><span class="unresolved-dot">Perlu bukti</span><span class="recovered-dot">Dari foto kedua</span><span class="selected-dot">Pilihanmu</span></div>
      <div id="region-list" class="region-list" aria-label="Daftar area dokumen"></div>
      <details class="coordinate-select"><summary>Tandai dengan keyboard</summary><p>Persentase posisi dan ukuran pada halaman (0 sampai 100).</p><div class="coordinate-fields"><label>Kiri %<input id="area-x" type="number" min="0" max="99" value="50"></label><label>Atas %<input id="area-y" type="number" min="0" max="99" value="65"></label><label>Lebar %<input id="area-w" type="number" min="1" max="100" value="45"></label><label>Tinggi %<input id="area-h" type="number" min="1" max="100" value="15"></label></div><button id="add-coordinates">Tambahkan area</button></details>
    </div>
    <div class="evidence-reading">
      <section class="second-step"><span class="section-label">LANGKAH BERIKUTNYA</span><h3 id="second-title">Satu sudut pandang lagi.</h3><p id="second-instruction">Buka bagian yang tertutup. Foto halaman yang sama dengan teks di sekeliling area tetap terlihat.</p><div class="second-actions"><button id="add-photo" class="primary">Tambahkan foto kedua</button><button id="demo-recovery" class="text-action" hidden>Gunakan foto kedua contoh &rarr;</button></div><p id="second-name" class="technical-note"></p></section>
      <section class="source-inspect" id="source-inspect" hidden><div class="reading-heading"><h3 id="source-title">Sumber area</h3><button id="close-source" aria-label="Tutup sumber area">&times;</button></div><p id="source-note"></p><div class="source-crops"><figure><canvas id="source-one"></canvas><figcaption>Foto 1 / halaman sejajar</figcaption></figure><figure id="source-two-figure" hidden><canvas id="source-two"></canvas><figcaption>Foto 2 / dipetakan ke halaman</figcaption></figure></div><details id="original-evidence" hidden><summary>Lihat foto kedua asli</summary><img id="second-original" alt="Foto tambahan sebelum pemetaan"></details></section>
      <section class="reading-section"><div class="reading-heading"><h3>Teks yang terbaca</h3><span id="line-count"></span></div><p class="reading-explainer">Klik baris untuk melihat bukti gambar. Skor OCR adalah keyakinan model; periksa ulang nama dan angka.</p><div id="ocr-lines" class="ocr-lines" aria-label="Baris teks hasil OCR"></div></section>
      <section class="export-section"><h3>Simpan untuk ditinjau</h3><p id="export-note"></p><div class="export-links"><button id="export-text">Teks .txt</button><button id="export-report">Laporan .json</button><button id="export-pdf">Halaman .pdf</button></div></section>
    </div>
  </div><input id="second-input" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden>`;
$("about").before(recoverySection);
const readingChoice = document.createElement("select");
readingChoice.id = "reading-view";
readingChoice.setAttribute("aria-label", "Bandingkan bacaan OCR");
readingChoice.innerHTML =
  '<option value="result">OCR hasil</option><option value="first">OCR foto 1 / sejajar</option>';
$("ocr-lines").before(readingChoice);
readingChoice.addEventListener("change", () =>
  renderRecovery(
    readingChoice.value === "first"
      ? { ...currentData, lines: currentData.before_lines || [] }
      : currentData,
    true,
  ),
);
const continueRecovery = document.createElement("button");
continueRecovery.id = "continue-recovery";
continueRecovery.className = "primary";
continueRecovery.textContent = "Lanjutkan pemulihan";
continueRecovery.hidden = true;
continueRecovery.addEventListener("click", () => {
  recoverySection.scrollIntoView({ block: "start" });
  $("add-photo").focus({ preventScroll: true });
});
$("result-actions").prepend(continueRecovery);

function recoveryBusy(value) {
  recoverySection
    .querySelectorAll("button,input,select")
    .forEach((el) => (el.disabled = value));
  continueRecovery.disabled = value;
}
function registerFirstPhoto(file, isSample) {
  firstPhoto = file;
  secondPhoto = null;
  manualRegions = [];
  selectingArea = false;
  selectionStart = null;
  selectedBox = null;
  $("mark-area").setAttribute("aria-pressed", "false");
  $("evidence-page").classList.remove("selecting");
  $("demo-recovery").hidden = !isSample;
  $("second-name").textContent = "";
}
function rectangle(box, status, label, onActivate) {
  const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  ["x", "y", "width", "height"].forEach((name, i) =>
    r.setAttribute(name, box[i]),
  );
  r.dataset.status = status;
  r.setAttribute("aria-label", label);
  if (onActivate) {
    r.setAttribute("tabindex", "0");
    r.setAttribute("role", "button");
    r.addEventListener("click", () => {
      if (!selectingArea) onActivate();
    });
    r.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onActivate();
      }
    });
  }
  return r;
}
function drawRegions() {
  const overlay = $("evidence-overlay");
  overlay.replaceChildren();
  overlay.setAttribute(
    "viewBox",
    `0 0 ${currentData.width} ${currentData.height}`,
  );
  $("region-list").replaceChildren();
  (currentData.regions || []).forEach((region, i) => {
    const label = `Area ${i + 1}: ${region.status === "recovered" ? "Dari foto 2" : "Perlu bukti"}`;
    overlay.append(
      rectangle(region.box, region.status, label, () =>
        showSource(region.box, label, region.note || region.label),
      ),
    );
    const button = document.createElement("button");
    button.className = "region-item";
    button.dataset.status = region.status;
    button.textContent = label;
    button.addEventListener("click", () =>
      showSource(region.box, label, region.note || region.label),
    );
    $("region-list").append(button);
  });
  manualRegions.forEach((box, i) => {
    const pixels = [
      box[0] * currentData.width,
      box[1] * currentData.height,
      box[2] * currentData.width,
      box[3] * currentData.height,
    ];
    overlay.append(rectangle(pixels, "selected", `Pilihan ${i + 1}`));
    const button = document.createElement("button");
    button.className = "region-item";
    button.textContent = `Hapus pilihan ${i + 1}`;
    button.addEventListener("click", () => {
      manualRegions.splice(i, 1);
      drawRegions();
    });
    $("region-list").append(button);
  });
  if (selectedBox)
    overlay.append(rectangle(selectedBox, "focus", "Baris yang dipilih"));
}
async function drawCrop(canvasId, url, box) {
  const img = new Image();
  img.src = url;
  await img.decode();
  if (selectedBox !== box) return;
  const [x, y, w, h] = box;
  const pad = 14;
  const left = Math.max(0, x - pad),
    top = Math.max(0, y - pad);
  const width = Math.min(img.width - left, w + pad * 2),
    height = Math.min(img.height - top, h + pad * 2);
  const canvas = $(canvasId);
  canvas.width = width;
  canvas.height = height;
  canvas
    .getContext("2d")
    .drawImage(img, left, top, width, height, 0, 0, width, height);
}
function showSource(box, title, note) {
  selectedBox = box;
  drawRegions();
  $("source-inspect").hidden = false;
  $("source-title").textContent = title;
  $("source-note").textContent = note;
  drawCrop("source-one", currentData.aligned, box).catch(() =>
    showError("Pratinjau sumber belum dapat dibaca."),
  );
  $("source-two-figure").hidden = !currentData.second_aligned;
  if (currentData.second_aligned)
    drawCrop("source-two", currentData.second_aligned, box).catch(() =>
      showError("Pratinjau foto kedua belum dapat dibaca."),
    );
  $("source-inspect").scrollIntoView({ block: "nearest" });
}
function renderRecovery(data, readingOnly = false) {
  if (!data.ocr_available) return;
  if (!readingOnly) readingChoice.value = "result";
  recoverySection.hidden = false;
  selectedBox = null;
  $("source-inspect").hidden = true;
  $("evidence-image").src = data.result;
  drawRegions();
  const unresolved = data.regions.filter(
    (r) => r.status === "unresolved",
  ).length;
  continueRecovery.hidden = !unresolved;
  $("replace-button").classList.toggle("secondary-replace", !!unresolved);
  $("recovery-summary").textContent =
    `${data.regions.filter((r) => r.status === "recovered").length} area dipulihkan / ${unresolved} perlu bukti`;
  $("second-title").textContent = data.second_aligned
    ? unresolved
      ? "Masih ada yang perlu dilihat."
      : "Dua foto, satu hasil tinjauan."
    : "Satu sudut pandang lagi.";
  $("second-instruction").textContent = unresolved
    ? data.instruction
    : "Tinjau bacaan di bawah. Jika ada bagian yang terlewat, tandai pada halaman sebelum menambahkan foto kedua.";
  $("add-photo").textContent = data.second_aligned
    ? "Ganti foto kedua"
    : "Tambahkan foto kedua";
  $("original-evidence").hidden = !data.second_original;
  if (data.second_original) $("second-original").src = data.second_original;
  $("ocr-lines").replaceChildren();
  $("line-count").textContent = `${data.lines.length} baris`;
  if (!data.lines.length) {
    const p = document.createElement("p");
    p.className = "empty-reading";
    p.textContent = "Teks belum terbaca. Coba foto lebih tajam.";
    $("ocr-lines").append(p);
  }
  data.lines.forEach((line) => {
    const button = document.createElement("button");
    button.className = "ocr-line";
    const text = document.createElement("span");
    text.textContent = line.text;
    const meta = document.createElement("small");
    const source =
      line.source === "photo-2"
        ? "Foto 2"
        : line.source === "mixed"
          ? "Foto 1 + 2"
          : "Foto 1";
    meta.textContent = `${source} / skor ${Math.round(line.score * 100)}%${line.uncertain || line.unresolved ? " / tinjau" : ""}`;
    button.dataset.uncertain = String(line.uncertain || line.unresolved);
    button.append(text, meta);
    button.addEventListener("click", () =>
      showSource(
        line.box,
        source,
        `Bacaan OCR: ${line.text}. Skor ${Math.round(line.score * 100)}%.`,
      ),
    );
    $("ocr-lines").append(button);
  });
  $("export-note").textContent = unresolved
    ? `${unresolved} area belum pulih. Ekspor adalah bahan tinjauan; penanda ketidakpastian disertakan dalam teks dan laporan.`
    : "Hasil OCR tetap perlu diperiksa. Laporan menyertakan koordinat area dan sumbernya.";
}
function addArea(box) {
  if (manualRegions.length >= 10) {
    showError("Maksimal sepuluh area tambahan.");
    return;
  }
  if (
    box.some((v) => !Number.isFinite(v)) ||
    Math.min(...box) < 0 ||
    box[2] < 0.005 ||
    box[3] < 0.005 ||
    box[0] + box[2] > 1.001 ||
    box[1] + box[3] > 1.001
  ) {
    showError("Posisi dan ukuran area harus berada di dalam halaman.");
    return;
  }
  manualRegions.push(box);
  selectedBox = null;
  drawRegions();
  $("selection-help").textContent =
    "Area ditandai. Tambahkan foto kedua yang memperlihatkan bagian ini.";
}
$("add-coordinates").addEventListener("click", () =>
  addArea(["x", "y", "w", "h"].map((k) => Number($("area-" + k).value) / 100)),
);
$("mark-area").addEventListener("click", () => {
  selectingArea = !selectingArea;
  $("mark-area").setAttribute("aria-pressed", String(selectingArea));
  $("evidence-page").classList.toggle("selecting", selectingArea);
  $("selection-help").textContent = selectingArea
    ? "Tarik kotak mengelilingi bagian yang kurang jelas. Atau gunakan input persentase di bawah."
    : "Klik area berwarna untuk melihat sumbernya.";
});
function point(event) {
  const b = $("evidence-overlay").getBoundingClientRect();
  return [
    Math.max(0, Math.min(1, (event.clientX - b.left) / b.width)),
    Math.max(0, Math.min(1, (event.clientY - b.top) / b.height)),
  ];
}
$("evidence-overlay").addEventListener("pointerdown", (event) => {
  if (!selectingArea || busy || event.button !== 0) return;
  event.preventDefault();
  selectionStart = point(event);
  event.currentTarget.setPointerCapture(event.pointerId);
});
$("evidence-overlay").addEventListener("pointermove", (event) => {
  if (!selectionStart) return;
  const p = point(event);
  selectedBox = [
    Math.min(p[0], selectionStart[0]) * currentData.width,
    Math.min(p[1], selectionStart[1]) * currentData.height,
    Math.abs(p[0] - selectionStart[0]) * currentData.width,
    Math.abs(p[1] - selectionStart[1]) * currentData.height,
  ];
  drawRegions();
});
$("evidence-overlay").addEventListener("pointerup", (event) => {
  if (!selectionStart) return;
  const p = point(event);
  addArea([
    Math.min(p[0], selectionStart[0]),
    Math.min(p[1], selectionStart[1]),
    Math.abs(p[0] - selectionStart[0]),
    Math.abs(p[1] - selectionStart[1]),
  ]);
  selectionStart = null;
  selectedBox = null;
  if (event.currentTarget.hasPointerCapture(event.pointerId))
    event.currentTarget.releasePointerCapture(event.pointerId);
  drawRegions();
});
$("evidence-overlay").addEventListener("pointercancel", () => {
  selectionStart = null;
  selectedBox = null;
  drawRegions();
});
$("close-source").addEventListener("click", () => {
  $("source-inspect").hidden = true;
  selectedBox = null;
  drawRegions();
});
$("add-photo").addEventListener("click", () => {
  if (!busy) {
    $("second-input").value = "";
    $("second-input").click();
  }
});
$("second-input").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) recoverPhoto(file, file.name);
});
async function recoverPhoto(file, name) {
  if (busy || !firstPhoto) return false;
  if (file.size > 12 * 1024 * 1024) {
    showError("Ukuran maksimal 12 MB.");
    return false;
  }
  $("error").hidden = true;
  setBusy(true);
  try {
    const body = new FormData();
    body.append("first", firstPhoto, "first.jpg");
    body.append("second", file, "second.jpg");
    const retained = (currentData.regions || [])
      .filter((r) => r.reason === "user-selected")
      .map((r) => [
        r.box[0] / currentData.width,
        r.box[1] / currentData.height,
        r.box[2] / currentData.width,
        r.box[3] / currentData.height,
      ]);
    body.append("regions", JSON.stringify([...retained, ...manualRegions]));
    const response = await fetch("/api/recover", { method: "POST", body });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Foto kedua belum dapat diproses.",
      );
    secondPhoto = file;
    manualRegions = [];
    display(data, $("filename").textContent, false);
    $("second-name").textContent = `Foto kedua: ${name}`;
    recoverySection.scrollIntoView({ block: "start" });
    return true;
  } catch (error) {
    showError(error.message);
    return false;
  } finally {
    setBusy(false);
  }
}
$("demo-recovery").addEventListener("click", async () => {
  if (busy) return;
  try {
    const response = await fetch("/api/sample/second");
    if (!response.ok) throw new Error("Contoh foto kedua tidak dapat dimuat.");
    await recoverPhoto(
      await response.blob(),
      "Contoh sintetis / penghalang dipindahkan",
    );
  } catch (error) {
    showError(error.message);
  }
});
function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  exportUrls.push(url);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    exportUrls = exportUrls.filter((x) => x !== url);
  }, 30000);
}
function reviewText() {
  const missing = currentData.regions.filter((r) => r.status === "unresolved");
  const header = [
    "SCANPILOT / HASIL OCR UNTUK DITINJAU",
    "Isi belum diverifikasi manusia.",
    ...missing.map(
      (r) => `[AREA BELUM PULIH: ${r.id}, koordinat ${r.box.join(", ")}]`,
    ),
    "",
  ];
  return header
    .concat(
      currentData.lines.map(
        (line) =>
          `${line.uncertain || line.unresolved ? "[TINJAU] " : ""}${line.text}`,
      ),
    )
    .join("\n");
}
$("export-text").addEventListener("click", () =>
  saveBlob(
    new Blob([reviewText()], { type: "text/plain;charset=utf-8" }),
    "scanpilot-review.txt",
  ),
);
async function fileHash(file) {
  if (!file || !crypto.subtle) return null;
  const hash = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(hash), (x) =>
    x.toString(16).padStart(2, "0"),
  ).join("");
}
$("export-report").addEventListener("click", async () => {
  const data = currentData;
  const files = [firstPhoto, secondPhoto];
  const report = {
    schema: "scanpilot-evidence-v1",
    created_at: new Date().toISOString(),
    status: data.status,
    verified_by_human: false,
    coordinate_space: {
      width: data.width,
      height: data.height,
      units: "pixels",
      origin: "top-left",
      image: "rectified-first-photo",
    },
    regions: data.regions,
    lines: data.lines,
    before_lines: data.before_lines,
    trace: data.trace,
    registration: data.registration || null,
    second_to_page: data.second_to_page || null,
    sources: await Promise.all(
      files
        .filter(Boolean)
        .map(async (file, i) => ({
          id: `photo-${i + 1}`,
          sha256: await fileHash(file),
          bytes: file.size,
        })),
    ),
    limitations: [
      "Skor OCR bukan probabilitas kebenaran terkalibrasi.",
      "Penutup putih dan bagian yang sepenuhnya hilang mungkin tidak terdeteksi.",
      "Satu halaman datar; maksimal dua foto.",
    ],
    opencv: data.opencv,
  };
  saveBlob(
    new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }),
    "scanpilot-evidence.json",
  );
});
$("export-pdf").addEventListener("click", async () => {
  if (busy) return;
  setBusy(true);
  try {
    // Rasterize the actual result with unresolved outlines and a review label.
    const img = new Image();
    img.src = currentData.result;
    await img.decode();
    const canvas = document.createElement("canvas");
    canvas.width = img.width;
    canvas.height = img.height + 60;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    ctx.strokeStyle = "#b45309";
    ctx.lineWidth = 3;
    currentData.regions
      .filter((r) => r.status === "unresolved")
      .forEach((r) => ctx.strokeRect(...r.box));
    ctx.fillStyle = "#172b4d";
    ctx.font = "14px sans-serif";
    ctx.fillText(
      "SCANPILOT / UNTUK DITINJAU - kotak jingga: area belum pulih",
      12,
      img.height + 32,
    );
    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.95),
    );
    const body = new FormData();
    body.append("file", blob, "review.jpg");
    const response = await fetch("/api/export/pdf", { method: "POST", body });
    if (!response.ok) throw new Error("PDF belum dapat dibuat.");
    saveBlob(await response.blob(), "scanpilot-review.pdf");
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
});
fetch("/api/health")
  .then((r) => r.json())
  .then((data) => {
    const local = data.mode === "local";
    document.querySelector("footer > span").textContent = local
      ? "Mode lokal / Foto diproses di server laptop; tidak disimpan sebagai riwayat."
      : "Mode AWS / Foto diproses di server AWS; tidak disimpan sebagai riwayat.";
    $("canvas-caption").textContent = local
      ? "Foto diproses melalui server lokal."
      : "Foto diproses melalui server AWS.";
  })
  .catch(() => {});
