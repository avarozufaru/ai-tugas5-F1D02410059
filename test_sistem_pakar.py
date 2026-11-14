import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest import mock
import sistem_pakar as sp

KB = sp.baca_kb(sp.FILE_KB)


def jalankan(nomor_dugaan, ya, tt=()):
    """nomor_dugaan 0 = semua dugaan, 1..8 = satu dugaan (sama seperti menu)."""
    def tanya_palsu(kb, fakta):
        if fakta in ya:
            return "ya"
        if fakta in tt:
            return "tidak tahu"
        return "tidak"

    if nomor_dugaan == 0:
        daftar = KB["kesimpulan"]
    else:
        daftar = [KB["kesimpulan"][nomor_dugaan - 1]]

    with mock.patch.object(sp, "tanya", tanya_palsu), redirect_stdout(io.StringIO()):
        terbukti = sp.konsultasi(KB, daftar)
    return [k["fakta"] for k in terbukti]


class TestKasusUji(unittest.TestCase):

    def test_kasus1_layu_bakteri(self):
        hasil = jalankan(0, ["tanaman layu", "pembuluh batang cokelat",
                             "daun layu tetap hijau", "lendir putih dari potongan batang"])
        self.assertEqual(hasil, ["layu bakteri"])
        self.assertEqual(sp.alasan["layu bakteri"]["id"], "R2")
        self.assertEqual(sp.alasan["gangguan pembuluh angkut"]["id"], "R1")

    def test_kasus2_virus_kuning_dengan_kutu_kebul(self):
        hasil = jalankan(6, ["tulang daun menjernih", "daun muda keriting",
                             "tanaman kerdil", "kutu kebul di bawah daun"])
        self.assertEqual(hasil, ["penyakit virus kuning",
                                 "virus kuning dengan penular kutu kebul aktif"])
        self.assertEqual(len(sp.sudah_ditanya), 4)

    def test_kasus3_negatif(self):
        hasil = jalankan(0, ["tanaman layu", "daun muda keriting"])
        self.assertEqual(hasil, [])

    def test_kasus4_thrips(self):
        hasil = jalankan(0, ["daun muda keriting", "bercak keperakan pada daun"])
        self.assertEqual(hasil, ["serangan thrips"])

    def test_kasus5_antraknosa_dan_lalat_buah(self):
        hasil = jalankan(0, ["buah membusuk", "bercak cekung kehitaman pada buah",
                             "spora merah jambu-oranye melingkar konsentris",
                             "bintik hitam bekas tusukan pada kulit buah", "larva di dalam buah"])
        self.assertEqual(hasil, ["antraknosa", "serangan lalat buah"])

    def test_jawaban_tidak_tahu(self):
        hasil = jalankan(1, ["tanaman layu", "pembuluh batang cokelat", "daun layu tetap hijau"],
                         tt=["lendir putih dari potongan batang"])
        self.assertEqual(hasil, [])
        self.assertEqual(sp.tidak_tahu, ["lendir putih dari potongan batang"])


class TestMesin(unittest.TestCase):

    def test_tidak_ada_pertanyaan_ganda(self):
        semua_fakta = list(KB["pertanyaan"].keys())
        jalankan(0, semua_fakta)
        self.assertEqual(len(sp.sudah_ditanya), len(set(sp.sudah_ditanya)))

    def test_setiap_kesimpulan_bisa_dicapai(self):
        semua_fakta = list(KB["pertanyaan"].keys())
        hasil = jalankan(0, semua_fakta)
        self.assertEqual(len(hasil), len(KB["kesimpulan"]))

    def test_aturan_melingkar_tetap_berhenti(self):
        kb_melingkar = {"aturan": [
            {"id": "X1", "jika": ["B"], "mode": "dan", "maka": "A"},
            {"id": "X2", "jika": ["A"], "mode": "dan", "maka": "B"}]}
        sp.kosongkan_memori()
        with redirect_stdout(io.StringIO()):
            self.assertFalse(sp.buktikan(kb_melingkar, "A"))


class TestBasisPengetahuan(unittest.TestCase):

    def test_kb_valid(self):
        self.assertEqual(sp.periksa_kb(KB), [])

    def test_syarat_minimal_soal(self):
        self.assertGreaterEqual(len(KB["sumber"]), 2)
        self.assertGreaterEqual(len(KB["aturan"]), 5)
        self.assertGreaterEqual(len(KB["kesimpulan"]), 3)

    def test_setiap_aturan_punya_rujukan_halaman(self):
        for aturan in KB["aturan"]:
            self.assertTrue(aturan["sumber"])
            self.assertTrue(aturan["rujukan"])

    def test_validator_menemukan_kesalahan(self):
        kb_rusak = copy.deepcopy(KB)
        kb_rusak["aturan"][0]["sumber"] = ["S9"]
        del kb_rusak["pertanyaan"]["tanaman layu"]
        kesalahan = sp.periksa_kb(kb_rusak)
        self.assertEqual(len(kesalahan), 2)


if __name__ == "__main__":
    unittest.main()
