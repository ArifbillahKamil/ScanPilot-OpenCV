> Pembaruan 8 September 2026: scope diperluas sesuai diskusi pengguna ke pemulihan dari dua foto. OCR lokal, penanda area, pencocokan dan penggabungan sumber, tinjauan bukti, serta ekspor sudah diimplementasikan. Arah UI terbaru mengikuti referensi Stripe yang disetujui pengguna. Rencana dan status mutakhir ada di README.md dan docs/IMPLEMENTATION.md. Bagian di bawah adalah catatan Stage 1/prototipe awal, bukan status fitur saat ini. AWS hidup dan validasi foto nyata masih belum terverifikasi.

# ScanPilot — Stage 1

Status: Stage 2 — prototipe lokal pertama tersedia. Pengguna menyetujui Paper + CleanShot + Screen Studio untuk dicoba dan direvisi. Validasi foto nyata, OCR, agent, dan AWS masih belum selesai.

## Konteks yang disepakati

- Pemilik: Muhammad Aribillah Kamil, solo developer, Full Stack / ML Engineer.
- Stack utama: Python. Hackathon pertama.
- Kompetisi: OpenCV AI Competition 2026, powered by AWS.
- Domain: AI/ML, computer vision, agentic document capture.
- Patokan: `hackathon-master-prompt (3).md`.
- Prioritas pengguna: demo sederhana dan mudah diulang.
- Target pengguna sementara: staf administrasi yang menerima foto invoice. Ini asumsi untuk divalidasi.

## Problem dan pembeda

Pertanyaan: Bagaimana mencegah angka penting dari foto dokumen yang buruk diteruskan sebagai data yang seolah sudah benar?

ScanPilot memeriksa kualitas foto, memilih koreksi yang relevan, mengevaluasi ulang, dan meminta foto tambahan jika bukti belum cukup. Kualitas gambar dan confidence OCR tidak menjamin kebenaran angka; antarmuka harus menjaga perbedaan tersebut.

Tiga fitur MVP:

1. Pemeriksaan kualitas: perspektif, bayangan, dan blur, dengan penanda area bermasalah.
2. Koreksi adaptif: perbaikan perspektif/pencahayaan, evaluasi ulang, dan instruksi pengambilan ulang untuk blur berat.
3. Perbandingan foto serta OCR sebelum–sesudah, dengan sumber visual untuk field penting dan status perlu diperiksa.

Tidak ada rekonstruksi generatif angka/teks hilang. Multi-page, tulisan tangan, dokumen melengkung, integrasi akuntansi, dan restorasi multi-frame berada di luar MVP awal.

## Konsep demo

Gunakan invoice sintetis tanpa data pribadi, angka ground truth diketahui, dan satu halaman cetak. Tampilkan foto awal dan hasil ScanPilot berdampingan. Koreksi foto miring/berbayang. Untuk foto blur berat, minta pengambilan ulang; setelah foto baru masuk, ulangi pemeriksaan dan OCR.

Wow moment: sistem mengubah tindakan dari memperbaiki gambar menjadi meminta bukti baru, lalu memperlihatkan perubahan hasil baca. Jangan sengaja memalsukan kesalahan OCR; pilih kasus dari pengujian nyata dan laporkan jika baseline juga berhasil.

## Arsitektur usulan

Python untuk layanan pemrosesan dan orkestrasi. OpenCV 5 melakukan pengukuran kualitas, deteksi halaman, transformasi perspektif, dan koreksi pencahayaan. OCR menggunakan engine yang sama untuk baseline dan pipeline adaptif. Pilihan engine/framework dan dukungan OpenCV 5 perlu diuji sebelum dikunci.

Layanan pemrosesan dan orkestrasi berjalan di AWS; penyimpanan bukti terbatas masa retensinya. Frontend web sederhana memakai HTML/CSS/JavaScript agar sebagian besar implementasi tetap Python. Agent memiliki tindakan terbatas, batas iterasi, dan trace keputusan. Kelayakan jalur Agentic Vision perlu dicocokkan dengan implementasi aktual; aturan kualitas saja tidak otomatis membuktikan integrasi agent yang kuat.

## Evaluasi

Bandingkan OCR langsung, preprocessing tetap, dan pipeline adaptif. Gunakan dokumen/sesi uji terpisah dari pengembangan. Ukur character error rate, exact match field angka penting, angka salah yang diterima, tingkat permintaan foto ulang, waktu, dan biaya per dokumen. Laporkan akurasi bersama coverage agar sistem tidak tampak unggul hanya karena menolak semua input sulit.

Dataset awal usulan: 10 template sintetis, masing-masing beberapa kondisi foto nyata. Variasi sintetis membantu pengembangan tetapi tidak menggantikan foto kamera. Benchmark sebelum–sesudah wajib memakai OCR yang sama; biaya/waktu foto ulang dihitung pada evaluasi workflow.

## Riset pemenang dan batas kesimpulan

- OpenCV AI Competition 2023: FREISA juara pertama, OpenCV for Exoplanet Detection kedua, IC4U ketiga. Sumber: https://www.hackster.io/contests/opencv-ai-competition-2023
- OpenCV Bin-Picking 2025: GBP2025 menang; pengumuman menekankan pengujian pada robot nyata. Kompetisi ini berbeda format dan merupakan pembanding domain, bukan edisi identik. Sumber: https://opencv.org/announcing-the-winners-of-the-first-perception-challenge-for-bin-picking-bpc/
- Inferensi: tugas spesifik dan bukti kerja nyata layak diprioritaskan. Sumber ini belum cukup untuk menyimpulkan pola stack, struktur pitch video, kategori yang jarang menang, atau tingkat persaingan ScanPilot.
- Aturan 2026: https://opencv26.devpost.com/rules
- Persyaratan 2026: https://opencv26.devpost.com/

## Penilaian awal 9 lensa

Skor subjektif untuk arah kerja, bukan probabilitas menang atau hasil validasi pengguna.

| Lensa | Skor / 10 | Dasar |
| --- | --- | --- |
| Pain point clarity | 7 | Kesalahan angka konkret; kebutuhan pengguna belum diwawancarai |
| Differentiation | 6 | Harus membuktikan nilai pengambilan ulang adaptif |
| Technical feasibility | 8 | Satu halaman dan tiga jenis gangguan |
| Judge appeal | 8 | Pengukuran CV dan perubahan tindakan dapat diperlihatkan |
| Scalability story | 7 | Pemrosesan dokumen independen; biaya belum diukur |
| Competitive potential | 6 | Pasar scanner matang dan pembeda belum terbukti |
| Uniqueness | 6 | Keunikan ada pada workflow dan evaluasi, bukan scan dasar |
| Wow factor | 8 | Bukti visual sebelum–sesudah dan pengambilan ulang |
| ChatGPT test | 7 | Lulus secara konsep jika workflow kamera dan verifikasi benar-benar berjalan |

Verdict: GO untuk proof of concept terbatas. Rekomendasi: buktikan pipeline adaptif mengungguli preprocessing tetap pada field penting sebelum memperluas produk.

## Enam pemeriksaan strategi

1. Failure penting: angka salah diterima tanpa pemeriksaan; tingkat kebutuhan belum tervalidasi.
2. Stakes: pekerjaan koreksi administrasi dan kesalahan pencatatan; jangan mengarang nilai kerugian.
3. Before/after: foto dan hasil baca ditampilkan bersama.
4. Framing: satu pertanyaan tentang angka salah dari foto buruk.
5. Bukti kriteria: benchmark, trace agent, demo AWS, instruksi reproduksi, dan uji pengguna.
6. Nama: ScanPilot menyiratkan panduan scan; pemahaman nama belum diuji pada pengguna.

## Struktur website usulan

Area scan sebagai layar pertama; perbandingan hasil; instruksi foto ulang; ringkasan evaluasi terukur; penjelasan cara kerja serta akses materi untuk juri. Hindari dashboard atau landing page panjang yang mengalihkan perhatian dari demo.

## Hal yang belum dipastikan

- Jam kerja per minggu dan akses calon pengguna belum diketahui.
- HP tersedia; pengguna bisa mengusahakan dokumen cetak tanpa memiliki printer.
- Invoice sintetis menjadi bahan demo awal. Instruksi "Lanjutkan" diterima sebagai kelanjutan scope ini.
- Status penerimaan proposal peserta baru; jadwal di situs tidak sepenuhnya konsisten.
- Versi/build OpenCV 5 dan engine OCR yang dapat dijalankan secara reproduktif di AWS.
- Enam referensi visual ditinjau; kombinasi rekomendasi disetujui pengguna untuk prototipe.

## Prototipe lokal pertama

Implementasi tersedia di app/ dan static/. Tujuh tes backend dan pemeriksaan browser desktop/mobile sudah lolos untuk contoh sintetis. Fungsi yang berjalan: unggah foto, deteksi halaman, koreksi perspektif, koreksi pencahayaan dengan evaluasi ulang, permintaan foto ulang, perbandingan dan unduhan JPG. Instruksi di README.md.

OCR, model agent, AWS, benchmark independen, Lighthouse, dan tes tiga orang designer belum tersedia/terverifikasi. Proyek belum memenuhi seluruh checklist final kompetisi. Ambang kualitas awal tidak membuktikan kebenaran teks.

## Pemeriksaan lingkungan

Python 3.12.9, OpenCV 5.0.0, Pillow 11.1.0 dan Node 22.22.2 tersedia di lingkungan lokal. FastAPI dapat ditemukan. Belum ada virtual environment proyek atau repository Git. Import OpenCV berhasil; ini belum membuktikan deployment AWS atau kualitas pipeline.
