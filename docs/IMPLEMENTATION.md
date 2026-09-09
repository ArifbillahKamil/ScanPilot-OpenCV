# ScanPilot 0.2 — pemulihan berbasis bukti

Implementasi lokal terdiri dari tiga fitur utama: pemeriksaan foto dan OCR, pemulihan area dari foto kedua, serta tinjauan sumber dan ekspor. Arah visual Stripe yang disetujui pengguna dipertahankan. Tidak ada penyelesaian teks generatif.

## Alur yang berjalan

1. Unggah JPG, PNG, atau WebP, maksimal 12 MB / 24 MP per foto. EXIF orientation diterapkan. Sistem mencari empat sudut halaman dan meluruskan perspektif.
2. Ketajaman dan pencahayaan menentukan apakah koreksi cahaya dicoba atau foto baru diperlukan. Koreksi hanya digunakan jika pengukuran membaik.
3. RapidOCR menjalankan deteksi dan pengenalan teks ONNX di server yang sama. UI menampilkan teks, kotak baris, skor model, dan pilihan OCR foto pertama versus hasil.
4. Objek berwarna dan bacaan berkeyakinan rendah ditandai sebagai dugaan area bermasalah. Pengguna dapat menggambar kotak atau memasukkan koordinat melalui keyboard, termasuk untuk penutup putih yang tidak terlihat oleh heuristik.
5. Foto kedua harus memperlihatkan bagian tersebut dan cukup banyak teks di sekelilingnya. OpenCV SIFT, pencocokan rasio, dan homography RANSAC memetakan foto kedua ke halaman pertama. Kecocokan diperiksa melalui jumlah/sebaran inlier, galat, dan bentuk transformasi.
6. Bacaan numerik yang bertentangan pada posisi bersama menolak penggabungan. Ini dapat menghasilkan penolakan akibat kesalahan OCR; pengguna diminta memeriksa kedua foto.
7. Area hanya disalin jika foto kedua mencakupnya, indikasi penghalang berkurang, dan teks cukup terbaca. Hasil gabungan dibaca ulang. Area tanpa bukti tetap berstatus belum pulih.
8. Klik area atau baris OCR untuk melihat potongan sumber. Foto kedua asli juga tersedia. JPG, TXT, PDF tinjauan, dan laporan JSON dapat diunduh. PDF menandai area belum pulih; TXT menyertakan penanda ketidakpastian; JSON menyimpan kotak area, sumber baris, transformasi, jejak proses, dan SHA-256 unggahan jika secure context tersedia.

## Batas yang disengaja

- Maksimal dua foto untuk satu halaman datar. Mengganti foto kedua mengulang pemulihan dari foto pertama; bukan akumulasi banyak frame.
- Tidak mendukung HEIC, PDF sebagai input, multi-page, tulisan tangan secara khusus, atau kertas melengkung.
- Area putih kosong tidak dapat dibedakan secara pasti dari teks yang ditutup kertas putih. Penanda manual adalah bagian dari alur, bukan klaim bahwa semua penghalang dapat ditemukan.
- Skor OCR belum dikalibrasi dan bukan probabilitas kebenaran. Pembacaan bisa salah meskipun skornya tinggi.
- Dua dokumen dengan template sama dan perbedaan hanya pada bagian yang tertutup dapat lolos pencocokan. Pemeriksaan identitas mengurangi risiko, bukan membuktikan bahwa kedua foto berasal dari halaman fisik yang sama.
- Jika foto pertama terlalu buram untuk dicocokkan, sistem meminta foto awal pengganti. Tidak ada super-resolution yang mengarang karakter, penjumlahan untuk mengisi nominal, ataupun ramalan isi yang hilang.
- OpenCV melakukan resampling geometris dan JPEG melakukan kompresi. “Dari foto 2” berarti sumber visual area itu foto kedua, bukan piksel sensor yang tetap identik byte demi byte.
- Sumber `mixed` berarti kotak baris melintasi area dari kedua foto. Koordinat laporan berada pada halaman pertama yang sudah diluruskan, bukan pada foto mentah.

## Agen dan keterbukaan implementasi

Planner lokal berbasis kebijakan dengan tindakan terbatas: ukur, koreksi, baca, minta bukti, cocokkan, salin area, verifikasi ulang. Hasil visual mengubah tindakan berikutnya, termasuk permintaan input manusia. Tidak menggunakan model bahasa atau mengklaim reasoning LLM. Jejak proses berisi tindakan dan pengamatan terukur. Kelayakan/persaingan untuk Agentic Vision Award tetap harus dinilai berdasarkan aturan dan implementasi aktual.

## API dan data

`POST /api/analyze` menerima `file`. `POST /api/recover` menerima `first`, `second`, dan `regions` berupa JSON array `[x,y,width,height]` ternormalisasi. Maksimal 10 pilihan tambahan. `POST /api/export/pdf` menerima raster hasil tinjauan sebagai `file`.

Pemrosesan stateless: browser menyimpan dua berkas selama tab terbuka dan mengirim ulang keduanya saat pemulihan. Tidak ada akun, database, upload bucket, atau riwayat server. Parser multipart dapat menulis file temporer dan menutupnya setelah request. Muatan total dibatasi 25 MB, termasuk request tanpa Content-Length. Satu pekerjaan OCR diproses per worker; pekerjaan bersamaan menerima 429. Container membatasi konkurensi HTTP. Tidak ada isi OCR/gambar yang sengaja dicatat ke log.

Mode lokal tidak mengirim foto ke penyedia OCR eksternal. Mode AWS menjalankan OCR/OpenCV di AWS, jadi unggahan meninggalkan perangkat. UI menampilkan mode runtime. Deployment terlindungi password demo dari Secrets Manager; akun AWS dan secret tidak pernah dimasukkan ke frontend.

## Validasi dan status

- Pengujian integrasi memakai engine OCR sebenarnya, bukan hasil tiruan: pemulihan nominal, penutup berulang, dokumen berbeda, angka bertentangan, area manual, input salah, PDF, autentikasi demo, dan batas request.
- Browser diuji lewat Chrome dengan profil terpisah: dua foto, bukti sumber, OCR, ekspor, kegagalan penggantian yang mempertahankan hasil, keyboard, serta lebar 360–1440 piksel.
- `benchmark-synthetic.json` membandingkan OCR langsung, preprocessing tetap, dan pemulihan dua foto pada lima nominal/ID baru dalam satu template sintetis. Bukan benchmark kamera independen atau klaim akurasi populasi. Waktu mengambil foto tambahan tidak termasuk waktu komputasi.
- Belum tervalidasi: foto HP pengguna, build Linux melalui Docker, deployment AWS hidup, biaya cloud, dan 3-Second Test dengan tiga orang sesuai master prompt. Jangan menandai keseluruhan checklist kompetisi selesai sebelum bukti itu tersedia.

## Referensi teknis

- [OpenCV feature matching dan homography](https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html) — konsep dipakai dan diuji pada OpenCV 5 yang terpasang.
- [RapidOCR](https://github.com/RapidAI/RapidOCR) dan [paket ONNX 1.4.4](https://pypi.org/project/rapidocr-onnxruntime/1.4.4/) — engine dan model OCR lokal.
- [ECS Express Mode](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html) — compute cloud untuk keseluruhan pipeline, bukan sekadar penyimpanan dekoratif.
