const $ = (id) => document.getElementById(id);
let busy = false;
let currentData = null;
let alignedView = false;
let currentView = "compare";
let lastErrorMessage = null;
const alignmentButton = $("alignment-button");
const sampleJump = document.createElement("a");
sampleJump.href = "#sample-library";
sampleJump.className = "sample-jump";
sampleJump.textContent = tr("Belum ada foto? Coba contoh ↓");
document.querySelector(".samples").id = "sample-library";
document.querySelector(".upload-copy").append(sampleJump);
function phase(value) {
  document.body.dataset.phase = value;
  const steps = ["upload", "processing", "review"];
  document.querySelectorAll("[data-step]").forEach((item) => {
    if (item.dataset.step === value) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
    item.classList.toggle(
      "done",
      steps.indexOf(item.dataset.step) < steps.indexOf(value),
    );
  });
}
function updateComparison() {
  if (!currentData) return;
  $("before-image").src = alignedView
    ? currentData.aligned
    : currentData.original;
  alignmentButton.textContent = alignedView
    ? tr("Lihat foto awal")
    : tr("Sejajarkan halaman");
  alignmentButton.setAttribute("aria-pressed", String(alignedView));
  $("comparison").dataset.mode = currentView;
  document
    .querySelectorAll("button[data-view]")
    .forEach((button) =>
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.view === currentView),
      ),
    );
  $("divider").hidden = currentView !== "compare";
  $("compare-control").hidden = currentView !== "compare";
  $("before-label").hidden = currentView === "result";
  $("after-label").hidden = currentView === "original";
  $("before-label").textContent = alignedView ? tr("HALAMAN SEJAJAR") : tr("FOTO AWAL");
  if (currentView === "original") {
    $("after-layer").style.clipPath = "inset(0 0 0 100%)";
    $("canvas-caption").textContent = tr("Foto masukan, tanpa koreksi.");
  } else if (currentView === "result") {
    $("after-layer").style.clipPath = "inset(0)";
    $("canvas-caption").textContent =
      tr("Hasil koreksi untuk ditinjau. Isi dan angka belum diverifikasi.");
  } else {
    split();
    $("canvas-caption").textContent = alignedView
      ? tr("Kedua halaman sejajar. Geser pembatas untuk membandingkan cahaya.")
      : tr("Geser pembatas untuk membandingkan. Sejajarkan halaman jika posisinya berbeda.");
  }
}
alignmentButton.addEventListener("click", () => {
  alignedView = !alignedView;
  updateComparison();
});
document.querySelectorAll("button[data-view]").forEach((button) =>
  button.addEventListener("click", () => {
    currentView = button.dataset.view;
    if (currentView === "original") alignedView = false;
    updateComparison();
  }),
);
const names = {
  covered: tr("Contoh / teks tertutup"),
  perspective: tr("Contoh · halaman miring"),
  shadow: tr("Contoh · bayangan"),
  blur: tr("Contoh · kurang fokus"),
};
function setBusy(value) {
  busy = value;
  if ($('language-select')) $('language-select').disabled = value;
  $("processing").hidden = !value;
  document
    .querySelectorAll(
      "button[data-sample],#upload-main,#replace-button,button[data-view],#alignment-button,#hero-upload,#hero-example,#preview-try",
    )
    .forEach((b) => (b.disabled = value));
  $("dropzone").setAttribute("aria-busy", String(value));
  $("compare-range").disabled = value;
  phase(value ? "processing" : currentData ? "review" : "upload");
  if (typeof recoveryBusy === "function") recoveryBusy(value);
}
function showError(message) {
  lastErrorMessage = message;
  $("error").textContent =
    tr(message) +
    (currentData ? tr(" Hasil dokumen sebelumnya tetap ditampilkan.") : "");
  $("error").hidden = false;
  $("error").scrollIntoView({ block: "nearest" });
}
function split() {
  const x = $("compare-range").value;
  $("after-layer").style.clipPath = `inset(0 0 0 ${x}%)`;
  $("divider").style.left = x + "%";
}
function display(data, name, isSample) {
  $("filename").textContent = isSample ? tr(name) : name;
  $("empty").hidden = true;
  $("comparison").hidden = false;
  $("compare-control").hidden = false;
  currentData = data;
  alignedView = false;
  currentView = "compare";
  $("view-switch").hidden = false;
  $("after-image").src = data.result;
  updateComparison();
  $("compare-range").value = 50;
  split();
  const retake = data.status === "retake";
  document.querySelector(".inspector").classList.toggle("retake", retake);
  document.querySelector(".inspector").classList.toggle("review", !retake);
  $("status-kicker").textContent = retake
    ? tr("PERLU FOTO ULANG")
    : tr("KOREKSI TERSEDIA");
  $("status-icon").textContent = retake ? "↻" : "✓";
  $("status-title").textContent = retake
    ? tr("Satu foto lagi.")
    : tr("Hasilnya siap ditinjau.");
  $("instruction").textContent = tr(data.instruction);
  if (data.page_estimated) {
    $("status-kicker").textContent = tr("PERSPEKTIF DILURUSKAN");
    $("status-title").textContent = tr("Periksa batas halaman.");
  }
  $("diagnosis").hidden = false;
  const issues = data.issues || [];
  $("diagnosis-summary").textContent = issues.length
    ? tr("{0} masalah terindikasi pada foto awal.", [issues.length])
    : tr("Tidak ada masalah kualitas utama yang terdeteksi.");
  $("diagnosis-list").replaceChildren();
  issues.forEach(issue => {
    const li = document.createElement("li"), label = document.createElement("strong"), action = document.createElement("span");
    label.textContent = tr(issue.label);
    action.textContent = tr(issue.action);
    li.dataset.state = issue.action === "Diperbaiki" ? "good" : "attention";
    li.append(label, action);
    $("diagnosis-list").append(li);
  });
  $("page-check").textContent = data.page_detected
    ? tr("Terdeteksi")
    : tr("Belum jelas");
  $("focus-check").textContent =
    data.before.sharpness < 45 ? tr("Perlu foto ulang") : tr("Cukup untuk tinjauan");
  $("light-check").textContent =
    data.before.uneven_light > 0.16
      ? data.after.uneven_light < data.before.uneven_light
        ? tr("Diperbaiki")
        : tr("Perlu ditinjau")
      : tr("Relatif merata");
  $("page-check").dataset.state = data.page_detected ? "good" : "attention";
  if (data.page_estimated) $("page-check").textContent = tr("Perkiraan dari tepi");
  $("focus-check").dataset.state =
    data.before.sharpness < 45 ? "attention" : "good";
  $("light-check").dataset.state =
    data.before.uneven_light > 0.16 &&
    data.after.uneven_light >= data.before.uneven_light
      ? "attention"
      : "good";
  $("result-actions").hidden = false;
  $("replace-button").textContent = retake
    ? tr("Pilih foto pengganti")
    : tr("Periksa foto lain");
  $("download").href = data.result;
  $("download").hidden = retake;
  $("trace-box").hidden = false;
  $("trace").replaceChildren();
  data.trace.forEach((step) => {
    const li = document.createElement("li"),
      title = document.createElement("strong");
    title.textContent = tr(step.title);
    li.append(title, document.createTextNode(tr(step.detail)));
    $("trace").append(li);
  });
  const li = document.createElement("li");
  li.textContent = tr("Ketajaman: {0} → {1}. Variasi cahaya: {2} → {3}. Waktu pemrosesan: {4} ms.", [data.before.sharpness, data.after.sharpness, data.before.uneven_light, data.after.uneven_light, data.elapsed_ms]);
  $("trace").append(li);
  $("engine").textContent =
    `OPENCV ${data.opencv} / ${data.runtime && data.runtime !== "local" ? "AWS ECS" : "LOCAL BUILD"}`;
  if (typeof renderRecovery === "function") renderRecovery(data);
  if (!refreshingLanguage) $("status-title").focus({ preventScroll: true });
  if (!refreshingLanguage && matchMedia("(max-width:800px)").matches)
    document.querySelector(".inspector").scrollIntoView({ block: "start" });
}
async function inspect(file, name, isSample = false) {
  if (busy) return false;
  $("error").hidden = true;
  if (file.size > 12 * 1024 * 1024) {
    showError(tr("Ukuran maksimal 12 MB. Pilih foto yang lebih kecil."));
    return false;
  }
  setBusy(true);
  try {
    const body = new FormData();
    body.append("file", file, "document.jpg");
    const response = await fetch("/api/analyze", { method: "POST", body });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : tr("Gambar belum dapat diproses."),
      );
    registerFirstPhoto(file, isSample);
    display(data, name, isSample);
    if (!isSample)
      document
        .querySelectorAll("[data-sample]")
        .forEach((b) => b.setAttribute("aria-pressed", "false"));
    return true;
  } catch (error) {
    showError(
      error.message === "Failed to fetch"
        ? tr("Server lokal tidak terhubung. Jalankan kembali ScanPilot.")
        : error.message,
    );
    return false;
  } finally {
    setBusy(false);
  }
}
function pick() {
  if (!busy) {
    $("file-input").value = "";
    $("file-input").click();
  }
}
$("upload-main").addEventListener("click", pick);
$("replace-button").addEventListener("click", pick);
function showWorkbench() {
  $("workbench").scrollIntoView({ behavior: "instant", block: "start" });
}
$("hero-upload").addEventListener("click", () => {
  if (!busy) {
    showWorkbench();
    pick();
  }
});
function tryHeroExample() {
  if (!busy) {
    showWorkbench();
    document.querySelector("[data-sample=perspective]").click();
  }
}
$("hero-example").addEventListener("click", tryHeroExample);
$("preview-try").addEventListener("click", tryHeroExample);
$("file-input").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) inspect(file, file.name);
});
$("compare-range").addEventListener("input", split);
function dragSplit(event) {
  const rect = $("comparison").getBoundingClientRect();
  $("compare-range").value = Math.round(
    Math.max(
      0,
      Math.min(100, ((event.clientX - rect.left) / rect.width) * 100),
    ),
  );
  split();
}
$("comparison").addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || busy || currentView !== "compare") return;
  $("comparison").setPointerCapture(event.pointerId);
  dragSplit(event);
});
$("comparison").addEventListener("pointermove", (event) => {
  if ($("comparison").hasPointerCapture(event.pointerId)) dragSplit(event);
});
$("comparison").addEventListener("pointerup", (event) => {
  if ($("comparison").hasPointerCapture(event.pointerId))
    $("comparison").releasePointerCapture(event.pointerId);
});
document.querySelectorAll("[data-sample]").forEach((button) => {
  button.setAttribute("aria-pressed", "false");
  button.addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    $("error").hidden = true;
    try {
      const response = await fetch("/api/sample/" + button.dataset.sample + '?lang=' + language);
      if (!response.ok) throw new Error(tr("Contoh tidak dapat dimuat."));
      const blob = await response.blob();
      setBusy(false);
      const success = await inspect(blob, names[button.dataset.sample], true);
      if (success)
        document
          .querySelectorAll("[data-sample]")
          .forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    } catch (error) {
      showError(error.message);
      setBusy(false);
    }
  });
});
const zone = $("dropzone");
let dragDepth = 0;
zone.addEventListener("dragenter", (event) => {
  event.preventDefault();
  dragDepth++;
  if (!busy) zone.classList.add("dragging");
});
zone.addEventListener("dragover", (event) => event.preventDefault());
zone.addEventListener("dragleave", (event) => {
  event.preventDefault();
  dragDepth--;
  if (dragDepth <= 0) zone.classList.remove("dragging");
});
zone.addEventListener("drop", (event) => {
  event.preventDefault();
  dragDepth = 0;
  zone.classList.remove("dragging");
  const file = event.dataTransfer.files[0];
  if (file && !busy) inspect(file, file.name);
});
window.addEventListener("dragover", (event) => event.preventDefault());
window.addEventListener("drop", (event) => event.preventDefault());
$("about-button").addEventListener("click", () => {
  const open = $("about").hidden;
  $("about").hidden = !open;
  $("about-button").setAttribute("aria-expanded", String(open));
  if (open)
    $("about").scrollIntoView({
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
});
