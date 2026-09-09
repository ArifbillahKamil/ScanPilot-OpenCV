# UI revision 02 — Meja periksa

User feedback: UI awal terasa template/AI slop; kategori perlu mudah dibaca dengan porsi yang sesuai. Pengguna meminta perubahan kreatif sekaligus UX yang lebih baik.

## Keputusan desain

- Ganti hero pemasaran dengan judul kerja pendek dan progres tiga tahap.
- Palet baru: meja netral #eeeae2, area dokumen biru tinta #263957, aksen tindakan #c64724, lembar hasil #fbfaf6.
- Layout desktop: contoh di kiri 206 px, dokumen mengambil ruang tersisa, hasil di kanan 310 px. Rujukan produk sebelumnya tetap menjadi konteks, bukan pola layout yang disalin.
- Daftar contoh memakai thumbnail sumber sebenarnya, nama kondisi 16 px dan keterangan 12 px. Contoh tidak lagi berbentuk kartu fitur horizontal.
- Panel hasil menyerupai lembar pemeriksaan: keputusan dan tindakan lebih dahulu, lalu tiga kategori kualitas. Detail proses berada dalam disclosure.
- Headline aplikasi 36 px, heading keputusan 28 px, instruksi 16 px, kategori 15 px. Metadata diperkecil karena merupakan informasi pendukung.
- Typeface sistem Bahnschrift untuk judul, Segoe UI untuk body; monospace hanya untuk nomor/metadata. Tidak ada unduhan font eksternal.

## Perbaikan UX

- Mode Foto awal, Hasil koreksi, Bandingkan. Slider hanya ditampilkan pada mode perbandingan; keyboard tetap dapat mengoperasikannya.
- Saat koreksi tersedia, unduhan menjadi tindakan utama. Saat foto perlu diulang, hanya tindakan penggantian foto yang ditonjolkan.
- Ketika penggantian gagal, hasil sebelumnya dipertahankan dan error menjelaskan hal tersebut. Contoh aktif hanya berubah sesudah berhasil.
- Mobile: panel hasil kosong disembunyikan; tautan langsung ke contoh tersedia. Setelah pemrosesan, keputusan mendapatkan fokus dan panel hasil dibawa ke layar.
- Grid menyusut menjadi dua kolom pada tablet dan satu kolom di HP; contoh berpindah ke bawah. Status bermasalah memakai teks dan tanda selain warna.
- Progres menggunakan aria-current; status hidup, fokus keyboard, skip link, reduced motion, dan penanganan drop di luar area tersedia.

## Validasi dan batas

Screenshot versi terbaru menggantikan screenshot prototipe di artifacts/. Pemeriksaan browser mencakup contoh, penggantian foto, mode tampilan, perbandingan keyboard, error, dan ukuran responsif. Ini bukan pengganti pengujian pengguna, audit Lighthouse, atau pengujian pembaca layar penuh. Belum dilakukan tes visual tiga orang designer yang diminta patokan. Backend, ambang kualitas, dan keterbatasan OCR/AWS tetap seperti README.
