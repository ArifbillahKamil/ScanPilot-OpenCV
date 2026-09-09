# Bahan cetak ScanPilot

Cetak ketiga PDF pada A4, skala 100%. Hitam putih cukup. Semua nama, barang, dan angka sintetis; dokumen ini bukan tagihan nyata.

Untuk masing-masing halaman, ambil foto:

1. Referensi jelas: halaman penuh di atas meja gelap, fokus dan cahaya merata.
2. Miring: sudut kamera berbeda tetapi seluruh halaman tetap masuk foto.
3. Bayangan: sebagian halaman terkena bayangan tanpa sengaja menutupnya dengan benda.
4. Buram: gerakkan HP sedikit saat mengambil foto.
5. Pengambilan ulang: kembali fokus dengan halaman penuh dan cahaya merata.

Simpan foto asli. Jangan kirim melalui aplikasi yang mengompresi gambar jika ada pilihan file asli. Hindari latar yang memuat data pribadi.

`ground_truth.json` mencatat angka acuan dan urutan teks yang digambar pada PDF. Urutan ini belum tentu sama dengan reading order engine OCR; normalisasi dan alignment benchmark perlu dirancang terpisah.

Ketiga halaman hanya bahan pengembangan/demo dengan satu layout, bukan benchmark independen. Benchmark final perlu template dan sesi foto lain. Data acuan tidak boleh dipakai oleh aplikasi untuk menebak hasil OCR saat inferensi.

Regenerasi: `python tools/make_demo_invoices.py` dari root proyek.
