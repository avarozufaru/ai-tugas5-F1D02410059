import json
import os
import textwrap

FOLDER = os.path.dirname(os.path.abspath(__file__))
FILE_KB = os.path.join(FOLDER, "kb_cabai.json")
TAMPILKAN_JEJAK = True
LEBAR = 72

memori = {}
alasan = {}
sudah_ditanya = []
tidak_tahu = []
jejak = []
sedang_dibuktikan = []


def kosongkan_memori():
    memori.clear()
    alasan.clear()
    sudah_ditanya.clear()
    tidak_tahu.clear()
    jejak.clear()
    sedang_dibuktikan.clear()


def baca_kb(nama_file):
    with open(nama_file, encoding="utf-8") as f:
        return json.load(f)


def cari_aturan(kb, fakta):
    """Mencari semua aturan yang bagian MAKA-nya sama dengan fakta."""
    hasil = []
    for aturan in kb["aturan"]:
        if aturan["maka"] == fakta:
            hasil.append(aturan)
    return hasil


def fakta_dasar(kb, fakta):
    """Fakta dasar = tidak dihasilkan aturan mana pun, jadi harus ditanyakan."""
    return len(cari_aturan(kb, fakta)) == 0


def periksa_kb(kb):
    """Memeriksa kelengkapan basis pengetahuan sebelum program dipakai.
    Mengembalikan daftar kesalahan. Daftar kosong berarti basis valid."""
    salah = []
    if len(kb["sumber"]) < 2:
        salah.append("jumlah sumber kurang dari 2")
    if len(kb["aturan"]) < 5:
        salah.append("jumlah aturan kurang dari 5")
    if len(kb["kesimpulan"]) < 3:
        salah.append("jumlah kesimpulan kurang dari 3")

    ada_rantai = False
    for aturan in kb["aturan"]:
        if aturan["mode"] not in ("dan", "atau"):
            salah.append(aturan["id"] + ": mode harus 'dan' atau 'atau'")
        if len(aturan["sumber"]) == 0:
            salah.append(aturan["id"] + ": tidak mencantumkan sumber")
        for kode in aturan["sumber"]:
            if kode not in kb["sumber"]:
                salah.append(aturan["id"] + ": sumber " + kode + " tidak terdaftar")
        for premis in aturan["jika"]:
            if fakta_dasar(kb, premis):
                if premis not in kb["pertanyaan"]:
                    salah.append("fakta '" + premis + "' belum punya pertanyaan")
            else:
                ada_rantai = True
    if not ada_rantai:
        salah.append("tidak ada aturan yang memakai hasil aturan lain")

    for k in kb["kesimpulan"]:
        if fakta_dasar(kb, k["fakta"]):
            salah.append("kesimpulan '" + k["fakta"] + "' tidak dihasilkan aturan mana pun")
        if k["fakta"] not in kb["saran"]:
            salah.append("kesimpulan '" + k["fakta"] + "' belum punya saran")
    return salah


def teks_aturan(aturan):
    """Mengubah aturan menjadi kalimat JIKA ... MAKA ..."""
    if aturan["mode"] == "dan":
        penghubung = " DAN "
    else:
        penghubung = " ATAU "
    return "JIKA " + penghubung.join(aturan["jika"]) + " MAKA " + aturan["maka"]


def cetak(teks, spasi=0, gantung=2):
    """Mencetak teks panjang agar terpotong rapi sesuai lebar layar."""
    print(textwrap.fill(teks, LEBAR, initial_indent=" " * spasi,
                        subsequent_indent=" " * (spasi + gantung)))


def tanya(kb, fakta):
    """Menanyakan satu fakta dasar. Mengembalikan 'ya', 'tidak', atau 'tidak tahu'."""
    print()
    cetak("P" + str(len(sudah_ditanya) + 1) + ". " + kb["pertanyaan"][fakta], 2)
    if fakta in kb["petunjuk"]:
        cetak("Petunjuk: " + kb["petunjuk"][fakta], 6)
    while True:
        jawab = input("    Jawab (y/t/tt/?) > ").strip().lower()
        if jawab in ("y", "ya"):
            return "ya"
        if jawab in ("t", "tidak"):
            return "tidak"
        if jawab in ("tt", "tidak tahu"):
            return "tidak tahu"
        if jawab == "?":
            jelaskan_mengapa(fakta)
        else:
            print("    Ketik y (ya), t (tidak), tt (tidak tahu), atau ? (mengapa).")


def cetak_jejak(teks):
    if TAMPILKAN_JEJAK:
        print("  " + "  " * len(jejak) + "> " + teks)


def buktikan(kb, tujuan):
    """Membuktikan sebuah tujuan dengan bekerja mundur.
    Mengembalikan True jika tujuan terbukti, False jika tidak."""

    if tujuan in memori:
        return memori[tujuan]

    if fakta_dasar(kb, tujuan):
        jawaban = tanya(kb, tujuan)
        sudah_ditanya.append(tujuan)
        if jawaban == "tidak tahu":
            tidak_tahu.append(tujuan)
        memori[tujuan] = (jawaban == "ya")
        return memori[tujuan]

    if tujuan in sedang_dibuktikan:
        return False
    sedang_dibuktikan.append(tujuan)

    hasil = False
    for aturan in cari_aturan(kb, tujuan):
        cetak_jejak("uji " + aturan["id"] + " untuk '" + tujuan + "'")
        jejak.append(aturan)
        terpenuhi = uji_premis(kb, aturan)
        jejak.pop()
        if terpenuhi:
            cetak_jejak(aturan["id"] + " terpenuhi -> '" + tujuan + "' TERBUKTI")
            alasan[tujuan] = aturan
            hasil = True
            break
        cetak_jejak(aturan["id"] + " gagal")

    sedang_dibuktikan.remove(tujuan)
    memori[tujuan] = hasil
    return hasil


def uji_premis(kb, aturan):
    """Mode 'dan': semua premis harus terbukti (berhenti di premis salah pertama).
    Mode 'atau': cukup satu premis terbukti (berhenti di premis benar pertama)."""
    if aturan["mode"] == "dan":
        for premis in aturan["jika"]:
            if not buktikan(kb, premis):
                return False
        return True
    else:
        for premis in aturan["jika"]:
            if buktikan(kb, premis):
                return True
        return False


def jelaskan_mengapa(fakta):
    """MENGAPA: menjelaskan alasan sebuah pertanyaan diajukan."""
    print("    MENGAPA ditanyakan?")
    for aturan in jejak:
        cetak("- Sedang diuji " + aturan["id"] + " [" + aturan["rujukan"] + "]: "
              + teks_aturan(aturan), 6)
    cetak("Jawaban Anda menentukan apakah '" + fakta + "' terpenuhi.", 6)


def jelaskan_bagaimana(fakta, spasi):
    """BAGAIMANA: menelusuri rantai aturan dari kesimpulan sampai jawaban pengguna."""
    if fakta in alasan:
        aturan = alasan[fakta]
        print(" " * spasi + fakta + "  <-- " + aturan["id"]
              + " (" + aturan["mode"].upper() + ") [" + aturan["rujukan"] + "]")
        for premis in aturan["jika"]:
            if memori.get(premis):
                jelaskan_bagaimana(premis, spasi + 4)
    else:
        print(" " * spasi + fakta + "  (jawaban Anda: ya)")


def status_fakta(fakta):
    if fakta not in memori:
        return "tidak diperiksa"
    if fakta in tidak_tahu:
        return "tidak tahu"
    if memori[fakta]:
        return "ya"
    return "tidak"


def jelaskan_gagal(kb, tujuan):
    """Menjelaskan mengapa sebuah dugaan tidak terbukti."""
    for aturan in cari_aturan(kb, tujuan):
        bagian = []
        for premis in aturan["jika"]:
            bagian.append(premis + " [" + status_fakta(premis) + "]")
        if aturan["mode"] == "dan":
            penghubung = " DAN "
        else:
            penghubung = " ATAU "
        cetak("- " + tujuan + ": " + aturan["id"] + " butuh " + penghubung.join(bagian), 2)


def pilih_dugaan(kb):
    print("Pilih dugaan yang ingin diperiksa:")
    print("  0. Periksa semua dugaan")
    nomor = 1
    for k in kb["kesimpulan"]:
        print("  " + str(nomor) + ". " + k["fakta"] + " (" + k["nama_ilmiah"] + ")")
        nomor = nomor + 1
    while True:
        pilihan = input("Pilihan > ").strip()
        if pilihan.isdigit() and 0 <= int(pilihan) <= len(kb["kesimpulan"]):
            if pilihan == "0":
                return kb["kesimpulan"]
            return [kb["kesimpulan"][int(pilihan) - 1]]
        print("Masukkan angka 0 sampai " + str(len(kb["kesimpulan"])) + ".")


def konsultasi(kb, daftar_dugaan):
    """Menjalankan backward chaining untuk setiap dugaan.
    Mengembalikan daftar kesimpulan yang terbukti."""
    kosongkan_memori()
    for k in daftar_dugaan:
        print()
        print("[Dugaan] " + k["fakta"])
        if buktikan(kb, k["fakta"]):
            print("  Hasil: " + k["fakta"] + " TERBUKTI")
        else:
            print("  Hasil: " + k["fakta"] + " tidak terbukti")


    terbukti = []
    for k in kb["kesimpulan"]:
        if memori.get(k["fakta"]):
            terbukti.append(k)
    return terbukti


def cetak_hasil(kb, daftar_dugaan, terbukti):
    print()
    print("=" * LEBAR)
    print("HASIL DIAGNOSIS")
    print("=" * LEBAR)

    if len(terbukti) == 0:
        cetak("Kesimpulan: TIDAK ADA. Gejala yang dijawab belum cukup untuk "
              "membuktikan dugaan mana pun.")
    for k in terbukti:
        print("Kesimpulan: " + k["fakta"].upper() + " (" + k["nama_ilmiah"] + ")")
        print("  Alasan (rantai aturan yang dipakai):")
        jelaskan_bagaimana(k["fakta"], 4)
        saran = kb["saran"][k["fakta"]]
        cetak("Saran awal [" + saran["rujukan"] + "]: " + saran["teks"], 2)
        print()

    gagal = []
    for k in daftar_dugaan:
        if k not in terbukti:
            gagal.append(k)
    if len(gagal) > 0:
        print()
        print("Dugaan yang tidak terbukti:")
        for k in gagal:
            jelaskan_gagal(kb, k["fakta"])

    if len(tidak_tahu) > 0:
        print()
        cetak("Catatan: gejala berikut dijawab 'tidak tahu' dan dianggap belum "
              "terbukti. Periksa lagi agar hasil lebih pasti: " + ", ".join(tidak_tahu) + ".")

    print()
    print("Jumlah pertanyaan yang diajukan: " + str(len(sudah_ditanya)))

    kode_sumber = []
    for aturan in alasan.values():
        for kode in aturan["sumber"]:
            if kode not in kode_sumber:
                kode_sumber.append(kode)
    if len(kode_sumber) > 0:
        print("Sumber pengetahuan yang dipakai:")
        for kode in sorted(kode_sumber):
            s = kb["sumber"][kode]
            cetak(kode + ". " + s["penulis"] + " (" + s["tahun"] + "). " + s["judul"]
                  + ". " + s["penerbit"] + ".", 2)

    print()
    print("Batas keberlakuan:")
    cetak(kb["batas"], 2, 0)
    print("=" * LEBAR)


def main():
    kb = baca_kb(FILE_KB)
    kesalahan = periksa_kb(kb)
    if len(kesalahan) > 0:
        print("Basis pengetahuan tidak valid:")
        for teks in kesalahan:
            print("  - " + teks)
        return

    print("=" * LEBAR)
    print("SISTEM PAKAR " + kb["judul"].upper())
    print("Metode: " + kb["metode"])
    print("=" * LEBAR)
    print("Termuat " + str(len(kb["aturan"])) + " aturan, " + str(len(kb["kesimpulan"]))
          + " kesimpulan, dan " + str(len(kb["sumber"])) + " sumber.")
    print("Jawab setiap pertanyaan dengan: y = ya, t = tidak, tt = tidak tahu,")
    print("atau ? untuk melihat MENGAPA pertanyaan itu diajukan.")
    print()

    while True:
        daftar = pilih_dugaan(kb)
        terbukti = konsultasi(kb, daftar)
        cetak_hasil(kb, daftar, terbukti)
        lagi = input("Konsultasi lagi? (y/t) > ").strip().lower()
        if lagi not in ("y", "ya"):
            print("Terima kasih.")
            break
        print()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
        print("Konsultasi dihentikan.")
