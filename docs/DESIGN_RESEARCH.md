# ScanPilot — referensi visual dan keputusan yang perlu dipilih

## Metode dan batas pengamatan

Enam referensi dari One Page Love ditinjau melalui deskripsi kurator. Screenshot Paper, Screen Studio, CleanShot, Alcove (mobile), dan Craft 2015 (halaman penuh) diunduh dan dilihat. Craft 3 baru ditinjau dari metadata kurasi. Screenshot yang disajikan galeri dapat diperbarui sesudah tanggal publikasi artikel; jangan anggap gambar sama dengan versi awal.

Motion dan hover belum diuji di browser interaktif. Nama font berasal dari metadata galeri, bukan pemeriksaan CSS versi terkini. Semua hex di bawah adalah PALET USULAN ScanPilot yang diinspirasi referensi, bukan warna situs yang diukur. Analisis belum merupakan audit desktop lengkap.

## Tabel komparatif

| Referensi | Hero dan tipografi | Layout dan warna yang terlihat | Motion/interaksi yang terdokumentasi | Elemen yang layak diadaptasi | Palet usulan |
| --- | --- | --- | --- | --- | --- |
| [Paper](https://onepagelove.com/paper) | Judul sans besar rata kiri; metadata Matter | Kanvas terang seperti kertas, garis grid, pratinjau tool | Kurator menyebut demo dalam halaman dan interaksi; hover belum diperiksa | Dokumen sebagai objek utama pada area kerja luas | #F5F2EA / #242522 / #486C58 |
| [Screen Studio](https://onepagelove.com/screen-studio) | Judul tebal, video produk; metadata Manrope | Gelap, kontras tinggi, preview produk | Kurator menyoroti demonstrasi zoom/follow dan animasi load | Perlihatkan perubahan hasil sejak awal | #191D20 / #F6F5F0 / #D8AA54 |
| [CleanShot](https://onepagelove.com/cleanshot) | Pernyataan manfaat langsung, CTA jelas; metadata Nunito | Putih, teks hitam, aksen biru, ruang kosong | Video penjelasan dan screenshot; hover belum diketahui | Kontrol sederhana dan urutan tindakan yang jelas | #F7F8F5 / #1D2D36 / #2D677A |
| [Alcove](https://onepagelove.com/alcove) | Kombinasi sans dan serif italic; metadata Editorial New + Inter | Fokus tunggal, gelap, cahaya hangat di ikon | Kurator mencatat partikel/background bergerak dan load animation | Ritme tenang serta penekanan satu frasa; gaya langit tidak cocok untuk scanner | #F5EFE4 / #332E29 / #9B593D |
| [Craft 3](https://onepagelove.com/craft-3) | Metadata typographic, Native System UI; hero belum diverifikasi visual | Kurator mencatat bento; tidak akan diadopsi sebagai struktur ScanPilot | Style block interaktif dan tombol dengan background berubah | Kontrol yang memperlihatkan perubahan hasil langsung | #FAF8F2 / #252A25 / #6A795A |
| [Craft, arsip 2015](https://onepagelove.com/craft) | Logo display dan hierarki sederhana; metadata Righteous + Lato | Putih, bentuk organik, isi bergantian sisi; aksen merah muda | Video dan alur visual vertikal; hover tidak bisa diverifikasi dari gambar | Urutan cerita yang menghubungkan input, tindakan, hasil | #F8F5ED / #34342F / #A34B35 |

Craft 2015 adalah produk film berbeda dari Craft 3. Dipakai sebagai pembanding storytelling saja; Craft 2015 dan Craft 3 adalah referensi arsip, bukan klaim situs aktif dengan desain yang sama.

## Rekomendasi: Paper + CleanShot + Screen Studio

Ambil kanvas dokumen dan keseimbangan ruang dari Paper, kejelasan kontrol dari CleanShot, serta demonstrasi perubahan hasil dari Screen Studio. Pengguna masih perlu memilih 2–3 referensi sebelum pola visual final dan implementasi frontend dikunci.

Usulan bentuk ScanPilot:

- Latar ivory #F5F2EA, tinta #242522, aksen hijau #486C58. Status memakai label/ikon selain warna.
- Usulan font: satu keluarga sans untuk aplikasi (misalnya IBM Plex Sans), mono hanya untuk angka dan metadata (IBM Plex Mono). Ketersediaan dan lisensi diperiksa saat implementasi.
- Desktop: dokumen memegang sebagian besar lebar, instruksi di panel samping. Mobile: dokumen, instruksi, lalu tombol utama dalam urutan vertikal.
- Tiga tahap: unggah, periksa/perbaiki, tinjau hasil. Saat bukti belum cukup, tampilkan permintaan foto ulang yang spesifik.
- Interaksi khas: pembatas perbandingan yang dapat digeser dan dikendalikan keyboard; klik hasil baca menyorot area sumber; pergantian foto mempertahankan konteks pemeriksaan.
- Animasi 150–220 ms hanya untuk transisi area terpilih/status. Ini angka rancangan, belum benchmark. Hormati reduced motion.
- Three.js sudah dipertimbangkan: tidak diperlukan untuk MVP 2D ini karena tidak menambah informasi pada inspeksi dokumen. SVG/canvas lebih sesuai untuk overlay dan transformasi.
- Copy awal: "Periksa fotonya. Percayai buktinya." Hindari label "angka pasti benar" hanya dari confidence OCR.

## Status

Pengguna telah menyetujui Paper + CleanShot + Screen Studio untuk dicoba dan direvisi. Frontend dan backend pemrosesan foto lokal pertama tersedia. Screenshot desktop/mobile ada di artifacts/ untuk review. Implementasi awal menggunakan font sistem Segoe UI, Georgia untuk frasa editorial, serta monospace sistem untuk metadata; pairing final dapat direvisi. Belum ada OCR, agent AI, deployment AWS, benchmark independen, atau validasi pengguna. Bahan cetak awal tersedia di demo/print.
