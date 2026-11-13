# Sistem pakar diagnosis hama dan penyakit tanaman cabai (Backward Chaining)
import argparse
import json
import os
import sys
import textwrap
LEBAR = 72

# beberapa komen saya taruh agar tidak lupa banget

# Basis pengetahuan: membaca dan memeriksa file JSON

def muat_kb(path):
    """Membaca file JSON basis pengetahuan."""
    with open(path, encoding="utf-8") as f:
        return siapkan_kb(json.load(f))


def siapkan_kb(kb):
    """Membuat indeks kesimpulan -> daftar aturan yang menghasilkannya.
    Indeks ini dipakai backward chaining untuk mencari aturan dari bagian MAKA."""
    kb["aturan_untuk"] = {}
    for aturan in kb["aturan"]:
        kb["aturan_untuk"].setdefault(aturan["maka"], []).append(aturan)
    return kb


def adalah_fakta_dasar(kb, fakta):
    """Fakta dasar = fakta yang tidak pernah menjadi hasil aturan mana pun,
    sehingga nilainya hanya bisa diketahui dengan bertanya ke pengguna."""
    return fakta not in kb["aturan_untuk"]


def fakta_dasar_semua(kb):
    """Semua fakta dasar yang muncul di bagian JIKA (urut sesuai kemunculan)."""
    hasil = []
    for aturan in kb["aturan"]:
        for premis in aturan["jika"]:
            if adalah_fakta_dasar(kb, premis) and premis not in hasil:
                hasil.append(premis)
    return hasil


def validasi_kb(kb):
    """Memeriksa kelengkapan dan konsistensi basis pengetahuan.
    Mengembalikan daftar pesan kesalahan; daftar kosong berarti valid."""
    galat = []
    id_terpakai = set()

    for aturan in kb["aturan"]:
        rid = aturan.get("id", "?")
        if rid in id_terpakai:
            galat.append(f"ID aturan {rid} dipakai lebih dari sekali")
        id_terpakai.add(rid)
        if not aturan.get("jika"):
            galat.append(f"{rid}: bagian JIKA kosong")
        if aturan.get("mode") not in ("dan", "atau"):
            galat.append(f"{rid}: mode harus 'dan' atau 'atau'")
        if not aturan.get("sumber"):
            galat.append(f"{rid}: tidak mencantumkan sumber")
        for s in aturan.get("sumber", []):
            if s not in kb["sumber"]:
                galat.append(f"{rid}: sumber {s} tidak ada di daftar sumber")

    for fakta in fakta_dasar_semua(kb):
        if fakta not in kb["pertanyaan"]:
            galat.append(f"fakta dasar '{fakta}' belum punya teks pertanyaan")

    for tujuan in kb["tujuan"]:
        if tujuan["fakta"] not in kb["aturan_untuk"]:
            galat.append(f"kesimpulan '{tujuan['fakta']}' tidak dihasilkan aturan mana pun")
        if tujuan["fakta"] not in kb.get("saran", {}):
            galat.append(f"kesimpulan '{tujuan['fakta']}' belum punya saran")

    ada_rantai = any(not adalah_fakta_dasar(kb, p)
                     for aturan in kb["aturan"] for p in aturan["jika"])
    if not ada_rantai:
        galat.append("tidak ada aturan yang memakai hasil aturan lain")

    # Deteksi siklus (misalnya A -> B dan B -> A) agar penalaran pasti berhenti.
    def ada_siklus(fakta, jalur):
        if fakta in jalur:
            return True
        for aturan in kb["aturan_untuk"].get(fakta, []):
            if any(ada_siklus(p, jalur | {fakta}) for p in aturan["jika"]):
                return True
        return False

    for tujuan in kb["aturan_untuk"]:
        if ada_siklus(tujuan, frozenset()):
            galat.append(f"terdapat siklus aturan yang melibatkan '{tujuan}'")
            break

    # Syarat minimal dari soal tugas.
    if len(kb["aturan"]) < 5:
        galat.append("jumlah aturan kurang dari 5")
    if len(kb["tujuan"]) < 3:
        galat.append("jumlah kesimpulan kurang dari 3")
    if len(kb["sumber"]) < 2:
        galat.append("jumlah sumber kurang dari 2")
    return galat


def teks_aturan(aturan):
    """Mengubah aturan menjadi kalimat 'JIKA ... MAKA ...'."""
    sambung = " DAN " if aturan["mode"] == "dan" else " ATAU "
    return f"JIKA {sambung.join(aturan['jika'])} MAKA {aturan['maka']}"


# Mesin inferensi backward chaining

class MesinBackwardChaining:
    """Membuktikan sebuah tujuan dengan bekerja mundur:
    tujuan -> cari aturan yang MAKA-nya tujuan itu -> buktikan setiap premisnya
    (sub-tujuan) -> bila premis adalah fakta dasar, tanyakan ke pengguna."""

    def __init__(self, kb, penanya, pencatat=None):
        self.kb = kb
        self.penanya = penanya        # fungsi(fakta, jejak) -> True/False
        self.pencatat = pencatat      # fungsi(kedalaman, teks) untuk jejak, boleh None
        self.nilai = {}               # memori kerja: fakta -> True/False
        self.bukti = {}               # fakta -> (aturan, premis yang terpenuhi)
        self.gagal = {}               # fakta -> [(id aturan, premis yang gagal)]
        self.ditanya = []             # urutan fakta dasar yang ditanyakan
        self._sedang_dibuktikan = set()

    def catat(self, kedalaman, teks):
        if self.pencatat:
            self.pencatat(kedalaman, teks)

    def buktikan(self, tujuan, jejak=(), kedalaman=0):
        # (a) Sudah diketahui di memori kerja: pakai lagi, jangan bertanya ulang.
        if tujuan in self.nilai:
            status = "ya" if self.nilai[tujuan] else "tidak"
            self.catat(kedalaman, f"'{tujuan}' sudah ada di memori kerja ({status}), tidak ditanya ulang")
            return self.nilai[tujuan]

        # Pengaman tambahan terhadap siklus.
        if tujuan in self._sedang_dibuktikan:
            return False

        # (b) Fakta dasar: tidak ada aturan yang menghasilkannya, jadi tanyakan.
        if adalah_fakta_dasar(self.kb, tujuan):
            jawaban = self.penanya(tujuan, jejak)
            self.ditanya.append(tujuan)
            self.nilai[tujuan] = jawaban
            return jawaban

        # (c) Coba setiap aturan yang bagian MAKA-nya sama dengan tujuan.
        self._sedang_dibuktikan.add(tujuan)
        self.gagal[tujuan] = []
        for aturan in self.kb["aturan_untuk"][tujuan]:
            self.catat(kedalaman, f"Untuk '{tujuan}' uji {aturan['id']}: {teks_aturan(aturan)}")
            terpenuhi, premis = self.uji_aturan(aturan, jejak + (aturan,), kedalaman + 1)
            if terpenuhi:
                self.nilai[tujuan] = True
                self.bukti[tujuan] = (aturan, premis)
                self.catat(kedalaman, f"{aturan['id']} terpenuhi -> '{tujuan}' TERBUKTI")
                self._sedang_dibuktikan.discard(tujuan)
                return True
            self.gagal[tujuan].append((aturan["id"], premis))
            self.catat(kedalaman, f"{aturan['id']} gagal -> '{tujuan}' belum terbukti")

        self._sedang_dibuktikan.discard(tujuan)
        self.nilai[tujuan] = False
        return False

    def uji_aturan(self, aturan, jejak, kedalaman):
        """Mengembalikan (terpenuhi?, daftar premis).
        Jika terpenuhi, daftar berisi premis yang terbukti (bahan alasan).
        Jika gagal, daftar berisi premis yang menyebabkan gagal."""
        if aturan["mode"] == "dan":
            for premis in aturan["jika"]:
                if not self.buktikan(premis, jejak, kedalaman):
                    return False, [premis]        # satu premis salah sudah cukup
            return True, list(aturan["jika"])
        # mode "atau": cukup satu premis benar, sisanya tidak perlu ditanyakan
        for premis in aturan["jika"]:
            if self.buktikan(premis, jejak, kedalaman):
                return True, [premis]
        return False, list(aturan["jika"])


# Tampilan, pertanyaan, dan penjelasan

class Warna:
    aktif = True
    KODE = {"judul": "1;36", "ok": "1;32", "gagal": "1;31", "redup": "2",
            "tebal": "1", "kuning": "1;33"}

    @classmethod
    def beri(cls, teks, jenis):
        if not cls.aktif:
            return teks
        return f"\033[{cls.KODE[jenis]}m{teks}\033[0m"


def garis(karakter="="):
    print(karakter * LEBAR)


def cetak_bungkus(teks, indent=0, gantung=0, jenis=None):
    """Mencetak teks panjang dengan pemotongan baris yang tetap menjorok rapi."""
    for baris in textwrap.wrap(teks, LEBAR, initial_indent=" " * indent,
                               subsequent_indent=" " * (indent + gantung)):
        print(Warna.beri(baris, jenis) if jenis else baris)


def penjelasan_mengapa(fakta, jejak):
    """Fasilitas MENGAPA: menjelaskan alasan sebuah pertanyaan diajukan."""
    print(Warna.beri("    MENGAPA pertanyaan ini diajukan?", "kuning"))
    for i, aturan in enumerate(jejak):
        awal = "Saya ingin membuktikan" if i == 0 else "Untuk itu perlu dibuktikan"
        sumber = ", ".join(aturan["sumber"])
        cetak_bungkus(f"{awal} '{aturan['maka']}' dengan {aturan['id']} "
                      f"[{sumber}]: {teks_aturan(aturan)}.", indent=6, gantung=2)
    cetak_bungkus(f"Jawaban Anda menentukan apakah premis '{fakta}' terpenuhi.", indent=6, gantung=2)


def buat_penanya(kb, nomor):
    """Membuat fungsi yang menanyakan fakta dasar ke pengguna (y / t / ?)."""
    def tanya(fakta, jejak):
        nomor[0] += 1
        info = kb["pertanyaan"][fakta]
        print()
        cetak_bungkus(f"P{nomor[0]}. {info['tanya']}", indent=2, gantung=4, jenis="tebal")
        if info.get("petunjuk"):
            cetak_bungkus(f"Petunjuk: {info['petunjuk']}", indent=6, jenis="redup")
        while True:
            try:
                jawab = input("    Jawaban (y/t/?) > ").strip().lower()
            except EOFError:
                print()
                sys.exit("Input berakhir, konsultasi dihentikan.")
            if jawab in ("y", "ya"):
                return True
            if jawab in ("t", "tidak", "n"):
                return False
            if jawab == "?":
                penjelasan_mengapa(fakta, jejak)
            else:
                print("    Ketik y (ya), t (tidak), atau ? (mengapa ditanyakan).")
    return tanya


def pencatat_jejak(kedalaman, teks):
    cetak_bungkus("> " + teks, indent=2 + 2 * kedalaman, gantung=2, jenis="redup")


def cetak_alasan(mesin, fakta, indent=4):
    """Fasilitas BAGAIMANA: menelusuri rantai aturan dari kesimpulan ke jawaban."""
    if fakta in mesin.bukti:
        aturan, premis = mesin.bukti[fakta]
        sumber = ", ".join(aturan["sumber"])
        print(" " * indent + f"{fakta}  <- {aturan['id']} ({aturan['mode']}) [{sumber}]")
        for p in premis:
            cetak_alasan(mesin, p, indent + 4)
    else:
        print(" " * indent + f"{fakta}  (jawaban Anda: ya)")


def sumber_dari_bukti(mesin, fakta, kumpulan):
    """Mengumpulkan semua kode sumber yang dipakai dalam rantai bukti."""
    if fakta in mesin.bukti:
        aturan, premis = mesin.bukti[fakta]
        kumpulan.update(aturan["sumber"])
        for p in premis:
            sumber_dari_bukti(mesin, p, kumpulan)


def alasan_gagal(mesin, fakta):
    bagian = []
    for rid, premis in mesin.gagal.get(fakta, []):
        bagian.append(f"{rid} tidak terpenuhi karena '{' / '.join(premis)}' tidak terbukti")
    return "; ".join(bagian)


def pilih_tujuan(kb):
    print("Pilih dugaan yang ingin diperiksa:")
    print("  0. Periksa semua dugaan")
    for i, t in enumerate(kb["tujuan"], start=1):
        print(f"  {i}. {t['fakta']} ({t['nama_ilmiah']})")
    while True:
        try:
            pilihan = input("Pilihan (0-%d) > " % len(kb["tujuan"])).strip()
        except EOFError:
            print()
            sys.exit("Input berakhir, konsultasi dihentikan.")
        if pilihan.isdigit() and 0 <= int(pilihan) <= len(kb["tujuan"]):
            angka = int(pilihan)
            return kb["tujuan"] if angka == 0 else [kb["tujuan"][angka - 1]]
        print("Pilihan tidak dikenal, masukkan angka dari daftar.")


def cetak_hasil(kb, mesin, daftar_tujuan):
    print()
    garis()
    print(Warna.beri("HASIL DIAGNOSIS", "judul"))
    garis()

    # Kesimpulan yang terbukti di sepanjang penalaran ikut ditampilkan,
    # termasuk yang terbukti sebagai sub-tujuan (misalnya penyakit virus kuning pada R10).
    terbukti = [t for t in kb["tujuan"] if mesin.nilai.get(t["fakta"])]
    tidak = [t for t in daftar_tujuan if not mesin.nilai.get(t["fakta"])]

    if terbukti:
        for t in terbukti:
            print(Warna.beri(f"Kesimpulan: {t['fakta'].upper()} ({t['nama_ilmiah']})", "ok"))
            print("  Alasan (aturan yang dipakai):")
            cetak_alasan(mesin, t["fakta"])
            saran = kb["saran"][t["fakta"]]
            cetak_bungkus(f"Saran awal [{', '.join(saran['sumber'])}]: {saran['teks']}", indent=2, gantung=2)
            print()
    else:
        print(Warna.beri("Kesimpulan: TIDAK ADA. Gejala yang dijawab belum cukup untuk "
                         "membuktikan dugaan mana pun.", "gagal"))
        print()

    if tidak:
        print("Dugaan yang diperiksa tetapi tidak terbukti:")
        for t in tidak:
            cetak_bungkus(f"- {t['fakta']}: {alasan_gagal(mesin, t['fakta'])}", indent=2, gantung=2)
        print()

    total = len(fakta_dasar_semua(kb))
    print(f"Pertanyaan diajukan: {len(mesin.ditanya)} dari {total} fakta dasar "
          f"({total - len(mesin.ditanya)} tidak perlu ditanyakan).")

    kode = set()
    for t in terbukti:
        sumber_dari_bukti(mesin, t["fakta"], kode)
        kode.update(kb["saran"][t["fakta"]]["sumber"])
    if kode:
        print("Sumber pengetahuan yang dipakai:")
        for k in sorted(kode, key=lambda s: int(s[1:])):
            s = kb["sumber"][k]
            cetak_bungkus(f"{k}. {s['judul']} - {s['penerbit']} ({s['tahun']})", indent=2, gantung=4)

    print()
    print(Warna.beri("Catatan batas keberlakuan:", "kuning"))
    cetak_bungkus(kb["batas"], indent=2)
    garis()


def main():
    parser = argparse.ArgumentParser(description="Sistem pakar hama dan penyakit cabai (Backward Chaining)")
    folder = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--kb", default=os.path.join(folder, "kb_cabai.json"),
                        help="lokasi file basis pengetahuan (default: kb_cabai.json)")
    parser.add_argument("--tanpa-jejak", action="store_true",
                        help="sembunyikan jejak penalaran backward chaining")
    parser.add_argument("--tanpa-warna", action="store_true",
                        help="matikan warna teks di terminal")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    Warna.aktif = not args.tanpa_warna and sys.stdout.isatty()
    if Warna.aktif and os.name == "nt":
        os.system("")  # mengaktifkan kode warna ANSI di terminal Windows

    try:
        kb = muat_kb(args.kb)
    except (OSError, json.JSONDecodeError, KeyError) as e:
        sys.exit(f"Gagal membaca basis pengetahuan: {e}")
    galat = validasi_kb(kb)
    if galat:
        print("Basis pengetahuan tidak valid:")
        for g in galat:
            print("  -", g)
        sys.exit(1)

    garis()
    print(Warna.beri(f"SISTEM PAKAR {kb['judul'].upper()}", "judul"))
    print(f"Metode: {kb['metode']} | Basis pengetahuan: {os.path.basename(args.kb)}")
    garis()
    print(f"Termuat {len(kb['aturan'])} aturan, {len(fakta_dasar_semua(kb))} fakta dasar, "
          f"{len(kb['tujuan'])} kesimpulan, {len(kb['sumber'])} sumber. Validasi: OK")
    print()

    daftar_tujuan = pilih_tujuan(kb)
    print()
    print("Jawab y (ya), t (tidak), atau ? untuk melihat alasan pertanyaan.")

    nomor = [0]
    mesin = MesinBackwardChaining(kb, buat_penanya(kb, nomor),
                                  None if args.tanpa_jejak else pencatat_jejak)
    try:
        for i, t in enumerate(daftar_tujuan, start=1):
            print()
            print(Warna.beri(f"[Dugaan {i}/{len(daftar_tujuan)}] {t['fakta']}", "judul"))
            hasil = mesin.buktikan(t["fakta"])
            status = Warna.beri("TERBUKTI", "ok") if hasil else Warna.beri("tidak terbukti", "gagal")
            print(f"  Hasil: {t['fakta']} {status}")
    except KeyboardInterrupt:
        print()
        sys.exit("Konsultasi dihentikan.")

    cetak_hasil(kb, mesin, daftar_tujuan)


if __name__ == "__main__":
    main()
