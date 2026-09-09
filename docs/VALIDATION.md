# Catatan validasi — 8 September 2026

## Hasil lokal

| Pemeriksaan | Hasil |
| --- | --- |
| Backend `unittest discover -s tests -v` | 20 tes lulus, 48,714 detik |
| Dependensi `.venv` terisolasi | `pip check`: tidak ada konflik |
| Sintaks JavaScript | `app.js` dan `recovery.js` lulus `node --check` |
| Browser alur awal | Upload, contoh, compare, keyboard, penggantian gagal, responsive lulus |
| Browser pemulihan | OCR dua foto, OCR awal/hasil, sumber, TXT/JSON/PDF, area manual, error preservation lulus |
| Lebar browser yang diperiksa | 360, 390, 680, 768, 1024, 1440 piksel |
| Lighthouse 13.4.1, halaman awal mobile default | Performance 95 / Accessibility 100, tanpa run warnings |
| Template AWS | Sintaks YAML lolos; mode rencana script tidak membuat panggilan AWS |

Lighthouse dijalankan pada server lokal dengan Chrome terpisah dan konfigurasi mobile default. Skor ini tidak mengukur waktu OCR, latensi AWS, seluruh state aplikasi, atau aksesibilitas melalui pengujian manusia. Laporan mentah ada di `artifacts/lighthouse.json` pada workspace implementasi. Screenshot browser ada di `artifacts/` dan tidak dimasukkan sebagai foto pengguna ke paket source.

## Ablation sintetis

Lima pasangan dengan nominal dan ID baru pada satu template: OCR langsung membaca nominal yang benar pada 0/5 kasus; preprocessing tetap 0/5; pemulihan dari foto kedua 5/5. Median waktu komputasi pemulihan terakhir 5.860 ms, setelah pemanasan engine, tanpa waktu mengambil foto tambahan. Data lengkap ada di `benchmark-synthetic.json`.

Hasil ini menunjukkan bahwa informasi yang tertutup membutuhkan bukti foto tambahan pada fixtures tersebut. Ini tidak menunjukkan peningkatan akurasi populasi sebesar 100%, tidak mengukur CER seluruh dokumen, dan tidak menggantikan benchmark foto HP independen. Nominal benchmark sengaja divariasikan terpisah dari baris item untuk menguji pembacaan visual, bukan kemampuan menjumlahkan invoice.

Pengujian negatif mencakup penghalang yang tetap ada, foto kedua yang tidak mencakup target, foto tanpa detail bersama, ID dokumen berbeda pada template sama, nominal yang bertentangan, penutup putih yang ditandai manual, serta target yang saling bertumpang tindih.

## Belum terverifikasi

- Foto kamera HP pengguna dan template dokumen lain.
- Docker Linux build dan service AWS hidup; Docker daemon serta profil AWS belum tersedia saat pengerjaan.
- Latensi, biaya dan ketahanan beban cloud.
- 3-Second Test dengan tiga designer/developer dan checklist penilaian manusia pada master prompt.

Status ini adalah penyelesaian implementasi fitur lokal, bukan pernyataan bahwa seluruh persyaratan submission kompetisi selesai.
