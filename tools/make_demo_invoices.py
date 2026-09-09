"""Generate deterministic vector A4 PDFs and ground truth using Python stdlib.

Run: python tools/make_demo_invoices.py
No real businesses, personal data, taxes, or payment instructions are used.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'demo' / 'print'


def money(value):
    return 'Rp ' + f'{value:,}'.replace(',', '.')


def pdf_escape(value):
    return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def write_pdf(path, commands):
    stream = '\n'.join(commands).encode('ascii')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
        f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream',
    ]
    data = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(data)
    data.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        data.extend(f'{offset:010} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    path.write_bytes(data)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    samples = [
        [('Buku catatan', 8, 18500), ('Map dokumen', 12, 6500), ('Pulpen hitam', 10, 4500)],
        [('Kertas A4', 3, 68500), ('Amplop dokumen', 15, 2800), ('Label arsip', 6, 12500)],
        [('Binder arsip', 7, 38500), ('Pembatas halaman', 9, 8500), ('Klip dokumen', 4, 16500)],
    ]
    manifest = []
    for number, items in enumerate(samples, 1):
        invoice_id = f'SP-DEMO-{number:03}'
        commands = ['0.12 g 0.12 G']
        transcript = []

        def text(x, y, value, size=12, bold=False):
            font = 'F2' if bold else 'F1'
            commands.append(f'BT /{font} {size} Tf 1 0 0 1 {x} {y} Tm ({pdf_escape(value)}) Tj ET')
            transcript.append(value)

        def line(y):
            commands.append(f'0.5 w 48 {y} m 547 {y} l S')

        text(48, 787, 'SCANPILOT / BAHAN UJI', 10, True)
        text(48, 742, 'INVOICE CONTOH', 28, True)
        text(48, 717, 'Dokumen sintetis - bukan tagihan atau bukti transaksi.', 10)
        line(694)
        text(48, 666, 'Pemasok: Studio Contoh', 12, True)
        text(48, 643, 'Pelanggan: Tim Administrasi Contoh')
        text(48, 608, 'Nomor invoice: ' + invoice_id)
        text(48, 585, 'Tanggal contoh: 08 September 2026')
        line(554)
        for x, label in [(48, 'Barang'), (280, 'Qty'), (335, 'Harga'), (450, 'Jumlah')]:
            text(x, 533, label, 11, True)
        line(518)
        total = 0
        records = []
        for i, (label, qty, price) in enumerate(items):
            amount = qty * price
            total += amount
            y = 489 - i * 39
            for x, value in [(48, label), (280, str(qty)), (335, money(price)), (450, money(amount))]:
                text(x, y, value, 11)
            records.append(dict(description=label, quantity=qty, unit_price_idr=price, amount_idr=amount))
        line(377)
        text(48, 348, 'TOTAL', 14, True)
        text(414, 348, money(total), 16, True)
        text(48, 296, 'Seluruh nama dan transaksi pada halaman ini adalah rekaan.', 10)
        text(48, 279, 'Tidak ada instruksi pembayaran. Dipakai hanya untuk pengujian OCR.', 10)
        line(99)
        text(48, 77, invoice_id + ' | Cetak A4, skala 100%, hitam putih cukup.', 9)
        write_pdf(OUT / f'{invoice_id}.pdf', commands)
        manifest.append(dict(invoice_id=invoice_id, total_idr=total, total_display=money(total),
                             currency='IDR', items=records, text_in_drawing_order=transcript))
    (OUT / 'ground_truth.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Created {len(manifest)} A4 PDFs and ground_truth.json in {OUT}')


if __name__ == '__main__':
    main()
