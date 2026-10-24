// All document/OCR content is inserted with textContent, never HTML.
let firstPhoto = null;
let secondPhoto = null;
let firstIsSample = false;
let firstSampleLanguage = 'en';
let secondIsSample = false;
let secondPhotoName = '';
let runtimeMode = null;
let manualRegions = [];
let selectingArea = false;
let selectionStart = null;
let selectedBox = null;
let sourceFocusOrigin = null;
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
const successPanel = document.createElement("section");
successPanel.id = "recovered-preview";
successPanel.hidden = true;
successPanel.setAttribute("aria-labelledby", "recovered-preview-title");
successPanel.innerHTML = '<span class="section-label" id="recovered-preview-kicker"></span><h3 id="recovered-preview-title"></h3><p id="recovered-preview-note"></p><div id="recovered-preview-lines"></div>';
document.querySelector(".second-step").after(successPanel);
const reviewRecovered = document.createElement("button");
reviewRecovered.id = "review-recovered";
reviewRecovered.className = "primary";
reviewRecovered.hidden = true;
reviewRecovered.addEventListener("click", () => {
  const region=currentData.regions.find(r=>r.status==="recovered");
  if(region) {
    showSource(region.box,tr("Foto 2"),tr("Bandingkan area sebelum dan sesudah. Piksel pengganti berasal dari foto kedua."));
    $("close-source").focus({preventScroll:true});
  }
});
const downloadReviewed = document.createElement("button");
downloadReviewed.id = "download-reviewed";
downloadReviewed.hidden = true;
downloadReviewed.addEventListener("click", () => $("export-pdf").click());
document.querySelector(".second-actions").prepend(reviewRecovered,downloadReviewed);
const mobileReview=document.createElement("button");
mobileReview.id="mobile-review-recovered";
mobileReview.hidden=true;
mobileReview.addEventListener("click",()=>{
  successPanel.scrollIntoView({block:"start"});
  const first=successPanel.querySelector("button");
  if(first) first.focus({preventScroll:true});
});
document.querySelector(".recovery-heading").append(mobileReview);
const readingChoice = document.createElement("select");
readingChoice.id = "reading-view";
readingChoice.setAttribute("aria-label", tr("Bandingkan bacaan OCR"));
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
continueRecovery.textContent = tr("Lanjutkan pemulihan");
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
  firstIsSample = isSample;
  firstSampleLanguage = language;
  secondIsSample = false;
  secondPhotoName = '';
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
    const label = tr("Area {0}: {1}", [i + 1, region.status === "recovered" ? tr("Dari foto 2") : region.reason === "low-ocr-score" ? tr("Bacaan OCR meragukan") : tr("Perlu bukti")]);
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
    overlay.append(rectangle(pixels, "selected", tr("Pilihan {0}", [i + 1])));
    const button = document.createElement("button");
    button.className = "region-item";
    button.textContent = tr("Hapus pilihan {0}", [i + 1]);
    button.addEventListener("click", () => {
      manualRegions.splice(i, 1);
      drawRegions();
    });
    $("region-list").append(button);
  });
  if (selectedBox)
    overlay.append(rectangle(selectedBox, "focus", tr("Baris yang dipilih")));
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
  if(!refreshingLanguage && $("source-inspect").hidden) sourceFocusOrigin=document.activeElement;
  selectedBox = box;
  drawRegions();
  $("source-inspect").hidden = false;
  $("source-title").textContent = tr(title);
  $("source-note").textContent = tr(note);
  drawCrop("source-one", currentData.aligned, box).catch(() =>
    showError(tr("Pratinjau sumber belum dapat dibaca.")),
  );
  $("source-two-figure").hidden = !currentData.second_aligned;
  if (currentData.second_aligned)
    drawCrop("source-two", currentData.second_aligned, box).catch(() =>
      showError(tr("Pratinjau foto kedua belum dapat dibaca.")),
    );
  if (!refreshingLanguage) $("source-inspect").scrollIntoView({ block: "nearest" });
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
  const recovered = data.regions.filter(r=>r.status==="recovered").length;
  const changedLines=(currentData.lines||[]).filter(line=>line.source==="photo-2");
  const hasRecovery = recovered > 0;
  recoverySection.dataset.recovered=String(hasRecovery);
  reviewRecovered.hidden = !hasRecovery;
  mobileReview.hidden = !hasRecovery;
  mobileReview.textContent=tr("Tinjau teks yang pulih");
  downloadReviewed.hidden = !hasRecovery;
  reviewRecovered.textContent=tr("Tinjau teks yang pulih");
  downloadReviewed.textContent=tr("Unduh PDF tinjauan");
  $("add-photo").classList.toggle("primary",!hasRecovery);
  $("add-photo").classList.toggle("text-action",hasRecovery);
  $("demo-recovery").hidden=!firstIsSample || !!data.second_aligned;
  successPanel.hidden=!hasRecovery;
  $("recovered-preview-kicker").textContent=tr("DARI FOTO KEDUA");
  $("recovered-preview-title").textContent=tr("Ini yang berhasil dibaca kembali.");
  $("recovered-preview-note").textContent=tr("Klik bacaan untuk membandingkan bukti kedua foto. Teks OCR tetap perlu diperiksa.");
  $("recovered-preview-lines").replaceChildren();
  changedLines.slice(0,3).forEach(line=>{
    const button=document.createElement("button");
    button.className="recovered-excerpt";
    const text=document.createElement("span"), action=document.createElement("small");
    text.textContent=line.text;
    action.textContent=tr("Lihat bukti");
    button.append(text,action);
    button.addEventListener("click",()=>showSource(line.box,tr("Foto 2"),tr("Bacaan OCR: {0}. Skor {1}%.",[line.text,Math.round(line.score*100)])));
    $("recovered-preview-lines").append(button);
  });
  if(!changedLines.length) $("recovered-preview-note").textContent=tr("Area dipulihkan dari foto kedua. Sebagian baris menggabungkan kedua sumber; periksa buktinya.");
  continueRecovery.hidden = !unresolved;
  $("replace-button").classList.toggle("secondary-replace", !!unresolved);
  $("recovery-summary").textContent = (recovered===1 ? tr("1 area berhasil dipulihkan.") : tr("{0} area berhasil dipulihkan.",[recovered])) + " " +
    (unresolved ? tr("Area terdeteksi yang masih perlu bukti: {0}.",[unresolved]) : tr("Semua area yang ditandai telah ditangani. Tetap tinjau isi dokumen."));
  if(!data.regions.length) $("recovery-summary").textContent=tr("Belum ada area pemulihan yang ditandai.");
  $("second-title").textContent = data.second_aligned
    ? unresolved
      ? tr("Masih ada yang perlu dilihat.")
      : tr("Dua foto, satu hasil tinjauan.")
    : tr(data.status==='retake'?"Satu sudut pandang lagi.":"Periksa hasilnya.");
  $("second-instruction").textContent = unresolved
    ? tr(data.instruction)
    : hasRecovery ? tr("Bagian yang ditandai sudah memiliki bukti dari foto kedua. Bandingkan sumbernya, lalu simpan hasil untuk ditinjau.") : tr("Tinjau bacaan di bawah. Jika ada bagian yang terlewat, tandai pada halaman sebelum menambahkan foto kedua.");
  $("add-photo").textContent = data.second_aligned
    ? tr("Ganti foto kedua")
    : tr("Tambahkan foto kedua");
  $("original-evidence").hidden = !data.second_original;
  if (data.second_original) $("second-original").src = data.second_original;
  $("ocr-lines").replaceChildren();
  $("line-count").textContent = tr("{0} baris", [data.lines.length]);
  if (!data.lines.length) {
    const p = document.createElement("p");
    p.className = "empty-reading";
    p.textContent = tr("Teks belum terbaca. Coba foto lebih tajam.");
    $("ocr-lines").append(p);
  }
  data.lines.forEach((line) => {
    const button = document.createElement("button");
    button.className = "ocr-line";
    button.dataset.source = line.source;
    const text = document.createElement("span");
    text.textContent = line.text;
    const meta = document.createElement("small");
    const source =
      line.source === "photo-2"
        ? tr("Foto 2")
        : line.source === "mixed"
          ? tr("Foto 1 + 2")
          : tr("Foto 1");
    meta.textContent = tr("{0} / skor {1}%{2}", [source, Math.round(line.score * 100), line.uncertain || line.unresolved ? tr(" / tinjau") : ""]);
    button.dataset.uncertain = String(line.uncertain || line.unresolved);
    button.append(text, meta);
    button.addEventListener("click", () =>
      showSource(
        line.box,
        source,
        tr("Bacaan OCR: {0}. Skor {1}%.", [line.text, Math.round(line.score * 100)]),
      ),
    );
    $("ocr-lines").append(button);
  });
  if(hasRecovery && !readingOnly && !refreshingLanguage) {
    const firstChanged=$("ocr-lines").querySelector('[data-source="photo-2"]');
    if(firstChanged) $("ocr-lines").scrollTop=firstChanged.offsetTop-$("ocr-lines").offsetTop;
  }
  $("export-note").textContent = unresolved
    ? tr("{0} area belum pulih. Ekspor adalah bahan tinjauan; penanda ketidakpastian disertakan dalam teks dan laporan.", [unresolved])
    : tr("Hasil OCR tetap perlu diperiksa. Laporan menyertakan koordinat area dan sumbernya.");
}
function addArea(box) {
  if (manualRegions.length >= 10) {
    showError(tr("Maksimal sepuluh area tambahan."));
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
    showError(tr("Posisi dan ukuran area harus berada di dalam halaman."));
    return;
  }
  manualRegions.push(box);
  selectedBox = null;
  drawRegions();
  $("selection-help").textContent =
    tr("Area ditandai. Tambahkan foto kedua yang memperlihatkan bagian ini.");
}
$("add-coordinates").addEventListener("click", () =>
  addArea(["x", "y", "w", "h"].map((k) => Number($("area-" + k).value) / 100)),
);
$("mark-area").addEventListener("click", () => {
  selectingArea = !selectingArea;
  $("mark-area").setAttribute("aria-pressed", String(selectingArea));
  $("evidence-page").classList.toggle("selecting", selectingArea);
  $("selection-help").textContent = selectingArea
    ? tr("Tarik kotak mengelilingi bagian yang kurang jelas. Atau gunakan input persentase di bawah.")
    : tr("Klik area berwarna untuk melihat sumbernya.");
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
  if(sourceFocusOrigin?.isConnected) sourceFocusOrigin.focus({preventScroll:true});
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
async function recoverPhoto(file, name, isSample = false) {
  if (busy || !firstPhoto) return false;
  if (file.size > 12 * 1024 * 1024) {
    showError(tr("Ukuran maksimal 12 MB."));
    return false;
  }
  $("error").hidden = true;
  setBusy(true);
  try {
    const body = new FormData();
    body.append("first", firstPhoto, "first.jpg");
    body.append("second", file, "second.jpg");
    if(window.packageWorkspace?.frame) body.append('first_page_frame','true');
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
          : tr("Foto kedua belum dapat diproses."),
      );
    secondPhoto = file;
    secondPhotoName = name;
    secondIsSample = isSample;
    manualRegions = [];
    display(data, $("filename").textContent, false);
    $("second-name").textContent = tr("Foto kedua: {0}", [name]);
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
    const response = await fetch("/api/sample/second?lang=" + firstSampleLanguage);
    if (!response.ok) throw new Error(tr("Contoh foto kedua tidak dapat dimuat."));
    await recoverPhoto(
      await response.blob(),
      tr("Contoh sintetis / penghalang dipindahkan"),
      true,
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
    tr("SCANPILOT / HASIL OCR UNTUK DITINJAU"),
    tr("Isi belum diverifikasi manusia."),
    ...missing.map(
      (r) => tr("[AREA BELUM PULIH: {0}, koordinat {1}]", [r.id, r.box.join(", ")]),
    ),
    "",
  ];
  return header
    .concat(
      currentData.lines.map(
        (line) =>
          `${line.uncertain || line.unresolved ? tr("[TINJAU] ") : ""}${line.text}`,
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
  const data = localizedEvidence(currentData);
  const files = [firstPhoto, secondPhoto];
  const report = {
    schema: "scanpilot-evidence-v1",
    language,
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
      tr("Skor OCR bukan probabilitas kebenaran terkalibrasi."),
      tr("Penutup putih dan bagian yang sepenuhnya hilang mungkin tidak terdeteksi."),
      tr("Satu halaman datar; maksimal dua foto."),
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
      tr("SCANPILOT / UNTUK DITINJAU - kotak jingga: area belum pulih"),
      12,
      img.height + 32,
    );
    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.95),
    );
    const body = new FormData();
    body.append("file", blob, "review.jpg");
    const response = await fetch("/api/export/pdf", { method: "POST", body });
    if (!response.ok) throw new Error(tr("PDF belum dapat dibuat."));
    saveBlob(await response.blob(), "scanpilot-review.pdf");
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
});
function updateRuntimeCopy(updateCaption = true) {
  const local = runtimeMode === 'local';
  document.querySelector('footer > span').textContent = tr(local
    ? 'Mode lokal / Foto diproses di server laptop; tidak disimpan sebagai riwayat.'
    : 'Mode AWS / Foto diproses di server AWS; tidak disimpan sebagai riwayat.');
  if(updateCaption&&!currentData) $('canvas-caption').textContent = tr(local
    ? 'Foto diproses melalui server lokal.' : 'Foto diproses melalui server AWS.');
}
fetch("/api/health")
  .then((r) => r.json())
  .then((data) => {
    runtimeMode = data.mode;
    const local = data.mode === "local";
    document.querySelector("footer > span").textContent = local
      ? tr("Mode lokal / Foto diproses di server laptop; tidak disimpan sebagai riwayat.")
      : tr("Mode AWS / Foto diproses di server AWS; tidak disimpan sebagai riwayat.");
    if (!currentData) $("canvas-caption").textContent = local
      ? tr("Foto diproses melalui server lokal.")
      : tr("Foto diproses melalui server AWS.");
  })
  .catch(() => {});
