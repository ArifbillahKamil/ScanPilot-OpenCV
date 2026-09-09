# Deployment AWS

Konfigurasi tersedia, tetapi belum dideploy atau diuji di AWS. Akun/profil AWS belum dikonfigurasi dan Docker daemon belum berjalan pada sesi implementasi ini. Jangan mengklaim URL publik, biaya terukur, atau cloud benchmark sebelum deployment nyata berhasil.

## Arsitektur

`Dockerfile` menjalankan aplikasi Python, OpenCV 5, OCR ONNX, dan planner dalam satu container Linux. `infra/ecs-express.yaml` menyediakan ECS Express Mode, execution role, infrastructure role, password demo di Secrets Manager, dan health probe. Express Mode mengelola layanan Fargate, HTTPS load balancer, networking, autoscaling, dan monitoring. Ini menjalankan komputasi utama ScanPilot di AWS.

Request pemulihan membawa kedua foto; tidak ada session server yang perlu ditempelkan ke satu replica. Dokumen tidak disimpan ke S3 atau database. Konfigurasi awal menggunakan 2 vCPU / 4 GB, minimum satu dan maksimum dua task. Ini adalah pilihan kapasitas awal, bukan hasil pengujian beban.

## Persiapan

1. Aktifkan Docker Desktop dengan Linux containers. Pastikan `docker version` dapat menghubungi daemon.
2. Konfigurasikan akses AWS di laptop memakai metode login/profil yang kamu miliki. Jangan memasukkan access key ke repository atau chat.
3. Pilih region dengan ECS/Fargate dan default VPC. Jika memakai VPC khusus, isi `NetworkConfiguration` pada template sebelum deployment.
4. Periksa resource dan izin IAM pada template. Deployment membuat resource berbayar: Fargate, load balancer, ECR, Secrets Manager, CloudWatch, dan komponen jaringan/data transfer yang digunakan.

Periksa rencana tanpa melakukan panggilan AWS:

```powershell
.venv\Scripts\python tools/deploy_aws.py --region ap-southeast-1
```

Setelah akun siap dan deployment disetujui, jalankan dengan `--apply`. Tambahkan `--profile nama-profil` jika menggunakan profil nondefault. Script memeriksa Docker dan identitas AWS, membangun image `linux/amd64`, push image dengan tag waktu ke ECR, memvalidasi template melalui AWS, lalu membuat/memperbarui CloudFormation stack.

```powershell
.venv\Scripts\python tools/deploy_aws.py --region ap-southeast-1 --profile nama-profil --apply
```

Script tidak mencetak password ECR atau password demo. Output stack memberikan endpoint, ARN layanan, dan ARN secret. Ambil password secara privat di Secrets Manager console; username browser adalah `scanpilot`. Akses `/api/health` tidak memerlukan password untuk health check.

## Verifikasi cloud dan penghapusan

- Pastikan stack selesai dan endpoint HTTPS merespons. `/api/health` harus menunjukkan `mode: aws-ecs` dan OpenCV 5.
- Jalankan demo **Tertutup** sampai pemulihan, sumber OCR, dan ekspor PDF. Uji juga foto salah dan penghalang yang tetap menutup teks. Rekam latensi cloud terpisah dari pengukuran lokal.
- Periksa CloudWatch untuk kegagalan runtime dan pastikan isi dokumen tidak dicatat. Pantau tagihan dan batas akun; script tidak mengklaim biaya nol.
- Sesudah demo tidak diperlukan, hapus stack yang benar melalui CloudFormation console. Repository ECR dibuat terpisah oleh script dan perlu dikelola/dihapus terpisah. Periksa pula resource terkelola, log, dan resource bersama di console; jangan menghapus load balancer atau jaringan milik aplikasi lain.

## Sumber

- [ECS Express Mode](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html)
- [CloudFormation ExpressGatewayService](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-expressgatewayservice.html)
- [Role dan prasyarat default VPC](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html)
- [Perubahan ketersediaan App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html): App Runner tidak menerima pelanggan baru mulai 30 April 2026; deployment baru proyek ini menggunakan ECS Express Mode.
