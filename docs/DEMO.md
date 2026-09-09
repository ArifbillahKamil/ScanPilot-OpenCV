# Demo ScanPilot

## Coba tanpa printer

1. Jalankan server dan buka `http://127.0.0.1:8765`.
2. Pilih contoh **Tertutup**. Perhatikan bahwa nominal total belum muncul di hasil OCR. Klik **Lanjutkan pemulihan**.
3. Klik **Gunakan foto kedua contoh**. Foto kedua memperlihatkan halaman yang sama setelah penghalang dipindahkan; pemrosesan berlangsung sungguhan.
4. Kotak hijau menunjukkan area dari foto kedua. Klik baris nominal untuk melihat potongan sebelum dan sesudah. Pilih **OCR foto 1 / sejajar** untuk membuktikan bahwa nominal sebelumnya tidak terbaca.
5. Kembalikan pilihan ke **OCR hasil**, lalu unduh PDF dan laporan JSON. Jangan menyebut skor OCR sebagai tingkat akurasi.

Contoh di aplikasi dihasilkan secara sintetis dan dilabeli demikian. Angka hasil pemulihan tidak ditulis tetap di UI atau disuntikkan ke OCR.

## Rekam demo dengan foto HP

Gunakan salah satu invoice di `demo/print/`. Seluruh nama dan transaksi rekaan. Letakkan halaman rata pada alas gelap; foto pertama harus memperlihatkan empat sudut dan cukup banyak tulisan yang tajam.

Tutup nominal total dengan kartu berwarna kecil. Ambil foto pertama. Pindahkan kartu dan ambil foto kedua lebih dekat; sertakan nomor invoice dan beberapa baris tabel untuk kecocokan. Hindari melipat kertas, mengganti versi invoice, atau hanya memotret satu angka tanpa konteks.

Pindahkan kedua foto ke laptop, lalu gunakan unggah biasa. Jika memakai penutup putih dan sistem tidak menandainya, gunakan **Tandai area**. Jika tidak cocok, ikuti arahan sistem dan ambil foto lebih lebar; jangan menyembunyikan kegagalan saat menjelaskan kemampuan.

Untuk browser HP pada Wi-Fi pribadi yang sama, jalankan server dengan `--host 0.0.0.0 --port 8765`, lalu buka alamat IPv4 laptop dengan port 8765. Windows mungkin meminta izin jaringan. Mode LAN masih memproses foto di laptop. Transfer foto ke laptop tetap menjadi opsi paling sederhana. Hash berkas di browser memerlukan HTTPS atau localhost; laporan LAN HTTP dapat menyimpan `sha256: null`.

## Naskah 90 detik

- 0–15 dtk: “Scanner bisa memperjelas foto, tapi bagian yang tertutup tidak punya bukti untuk dibaca.” Tunjukkan foto pertama dan nominal yang hilang.
- 15–35 dtk: ScanPilot menunjukkan area yang perlu bukti dan mengarahkan pengambilan kedua.
- 35–60 dtk: Unggah foto kedua. Tunjukkan pencocokan dan hasil area yang dipulihkan.
- 60–75 dtk: Klik nominal. Perlihatkan foto sumber dan perubahan bacaan OCR.
- 75–90 dtk: Tunjukkan laporan, jelaskan batas dua foto/halaman datar, serta hasil pengujian yang benar-benar telah dilakukan.

Untuk klaim demo AWS, rekam langkah tersebut pada URL deployment AWS setelah benar-benar diuji. Jangan memakai label cloud untuk video server lokal.
