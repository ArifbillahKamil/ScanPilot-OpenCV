# ScanPilot

**Alur utama sekarang berupa paket dokumen:** unggah satu PDF maksimal 20 MB atau hingga 20 foto. Setiap halaman diperiksa otomatis dan diprioritaskan berdasarkan kebutuhan penanganan. Buka halaman bermasalah untuk pemulihan dua foto, lalu kembali ke daftar dan ekspor PDF gabungan beserta laporan. Halaman PDF yang tidak diubah mempertahankan teks dan grafis aslinya. Paket berada di tab browser; refresh akan menghapusnya. Lihat [panduan paket](docs/PACKAGES.md) dan [README English](README.en.md) untuk batas serta alur terbaru; bagian satu foto di bawah menjelaskan editor per halaman.

[English](README.en.md) | [Bahasa Indonesia](README.md)

Antarmuka menyediakan pilihan **English / Indonesia** di header, dengan English sebagai bahasa awal. Pilihan tersimpan di browser. Pergantian bahasa mempertahankan hasil dan area pilihan; teks OCR serta nama berkas asli tidak diterjemahkan. Anotasi ekspor mengikuti bahasa yang dipilih.

Pulihkan bagian dokumen yang tertutup atau meragukan dengan bukti dari foto kedua. OpenCV 5 mencocokkan halaman; OCR lokal membaca teks; setiap area hasil memiliki sumber yang bisa diperiksa. Tidak ada angka yang diisi melalui prediksi generatif.

## Jalankan

Gunakan Python 3.12. Environment proyek `.venv` sudah disiapkan pada laptop ini. Untuk instalasi baru:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Buka http://127.0.0.1:8765. Pilih **Tertutup**, klik **Lanjutkan pemulihan**, kemudian **Gunakan foto kedua contoh**. Klik nominal hasil OCR untuk melihat potongan sumber sebelum dan sesudah. Semua contoh diproses saat digunakan.

## Tiga fitur utama

1. **Periksa dan baca:** unggah/drop JPG, PNG, WebP; orientasi EXIF; deteksi halaman; koreksi perspektif/cahaya; OCR dan area meragukan.
2. **Pulihkan dari bukti kedua:** arahan pemotretan, penanda manual, pencocokan SIFT/RANSAC, pemeriksaan pertentangan bacaan, salinan area yang didukung, serta pembacaan ulang hasil.
3. **Tinjau dan simpan:** perbandingan gambar/OCR, sumber tiap area/baris, potongan kedua foto, penanda belum pulih, unduhan JPG/TXT/PDF/JSON, dan jejak keputusan.

Paket maksimal 20 halaman. PDF maksimal 20 MB; tiap foto maksimal 12 MB / 24 MP. Pemulihan memakai dua foto per halaman. Ekspor paket maksimal 80 MB per request. HEIC, PDF bersandi, serta PDF interaktif/bertanda tangan belum didukung. Mode lokal tidak memakai layanan OCR eksternal atau menyimpan riwayat server. Mode AWS memproses unggahan di AWS dan diberi label di UI.

## Pengujian

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m pip check
node --check static/app.js
node --check static/recovery.js
.venv\Scripts\python tools/benchmark_recovery.py
```

Tes integrasi menjalankan OCR sebenarnya, termasuk penolakan dokumen berbeda, angka bertentangan, penghalang berulang, dan pemilihan area manual. Script browser `tools/check_browser.py` dan `tools/check_recovery_browser.py` memerlukan Chrome dengan profil pengujian terpisah pada CDP port 9225 dan server pada port 8765; jangan arahkan ke profil browser pribadi.

Lima pasangan sintetis dengan nominal baru dibandingkan melalui OCR langsung, preprocessing tetap, dan pemulihan dua foto. Angka lengkap serta latensi tersedia di [hasil benchmark](docs/benchmark-synthetic.json). Dataset ini satu template sintetis, bukan bukti akurasi pada foto HP atau template lain.

## Batas dan kesiapan

Skor OCR bukan jaminan kebenaran. Penutup putih dapat terlewat dan membutuhkan penanda manual. Kecocokan visual tidak membuktikan identitas halaman fisik. Jika tidak ada bukti yang cukup, bagian tersebut tetap belum pulih. Planner berbasis kebijakan; tidak menggunakan model bahasa.

Fitur lokal tersedia. Build Docker Linux/amd64 dan smoke test OCR, pemulihan, serta ekspor–impor PDF sudah lolos. Template ECS Express Mode dan script deployment tersedia. **Deployment AWS hidup, biaya/latensi cloud, benchmark akurasi independen, dan review pengguna sesuai master prompt belum terverifikasi.** Lihat [kesiapan deployment](docs/RELEASE_READINESS.md). Keseluruhan checklist kompetisi belum dinyatakan selesai.

- [Detail implementasi dan batas](docs/IMPLEMENTATION.md)
- [Hasil pengujian dan hal yang belum terverifikasi](docs/VALIDATION.md)
- [Panduan demo sintetis dan foto HP](docs/DEMO.md)
- [Deployment AWS](docs/AWS.md)
- [Bahan invoice cetak](demo/print/README.md)
- [Riwayat arahan proyek](PROJECT_BRIEF.md)
- [Arahan visual yang disetujui](docs/UI_REVISION_03.md)

Stack: FastAPI, OpenCV 5, RapidOCR / ONNX Runtime, dan HTML/CSS/JavaScript. Model OCR disertakan dalam paket RapidOCR. Lihat [RapidOCR](https://github.com/RapidAI/RapidOCR) untuk lisensi dan atribusi upstream.
