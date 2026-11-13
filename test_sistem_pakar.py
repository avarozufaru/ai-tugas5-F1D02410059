import copy
import os
import unittest

from sistem_pakar import (MesinBackwardChaining, fakta_dasar_semua, muat_kb, siapkan_kb,
                          validasi_kb)

KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb_cabai.json")


def jalankan(kb, jawaban_ya, daftar_tujuan):
    """Menjalankan mesin. Fakta di jawaban_ya dijawab 'ya', sisanya 'tidak'."""
    mesin = MesinBackwardChaining(kb, lambda fakta, jejak: fakta in jawaban_ya)
    for tujuan in daftar_tujuan:
        mesin.buktikan(tujuan)
    terbukti = [t for t in daftar_tujuan if mesin.nilai[t]]
    return mesin, terbukti


class TestBasisPengetahuan(unittest.TestCase):
    def setUp(self):
        self.kb = muat_kb(KB_PATH)

    def test_kb_valid_dan_memenuhi_syarat_tugas(self):
        self.assertEqual(validasi_kb(self.kb), [])
        self.assertGreaterEqual(len(self.kb["aturan"]), 5)
        self.assertGreaterEqual(len(self.kb["tujuan"]), 3)
        self.assertGreaterEqual(len(self.kb["sumber"]), 2)

    def test_setiap_aturan_menunjuk_sumber_yang_ada(self):
        for aturan in self.kb["aturan"]:
            self.assertTrue(aturan["sumber"], aturan["id"])
            for kode in aturan["sumber"]:
                self.assertIn(kode, self.kb["sumber"])

    def test_validator_menolak_sumber_yang_tidak_ada(self):
        kb = copy.deepcopy(self.kb)
        kb["aturan"][0]["sumber"] = ["S99"]
        self.assertTrue(any("S99" in g for g in validasi_kb(kb)))

    def test_validator_menolak_aturan_melingkar(self):
        kb = copy.deepcopy(self.kb)
        kb["aturan"].append({"id": "RX", "jika": ["layu bakteri"], "mode": "dan",
                             "maka": "gangguan pembuluh angkut", "sumber": ["S1"]})
        siapkan_kb(kb)
        self.assertTrue(any("siklus" in g for g in validasi_kb(kb)))


class TestKasusUji(unittest.TestCase):
    def setUp(self):
        self.kb = muat_kb(KB_PATH)
        self.semua = [t["fakta"] for t in self.kb["tujuan"]]

    def test_kasus_1_layu_bakteri(self):
        ya = {"tanaman layu", "pembuluh batang cokelat", "lendir putih pada uji gelas air"}
        mesin, terbukti = jalankan(self.kb, ya, self.semua)
        self.assertEqual(terbukti, ["layu bakteri"])
        self.assertEqual(mesin.bukti["layu bakteri"][0]["id"], "R2")
        self.assertEqual(mesin.bukti["gangguan pembuluh angkut"][0]["id"], "R1")
        self.assertEqual(len(mesin.ditanya), 11)

    def test_kasus_2_virus_kuning_satu_dugaan(self):
        ya = {"tulang daun pucuk memucat", "daun muda keriting", "tanaman kerdil",
              "kutu kebul ditemukan"}
        mesin, terbukti = jalankan(self.kb, ya, ["virus kuning dengan vektor kutu kebul aktif"])
        self.assertEqual(terbukti, ["virus kuning dengan vektor kutu kebul aktif"])
        self.assertTrue(mesin.nilai["penyakit virus kuning"])
        # Premis ATAU berhenti di jawaban 'ya' pertama, jadi cukup 4 pertanyaan.
        self.assertEqual(mesin.ditanya, ["tulang daun pucuk memucat", "daun muda keriting",
                                         "tanaman kerdil", "kutu kebul ditemukan"])

    def test_kasus_3_negatif_tidak_ada_kesimpulan(self):
        ya = {"tanaman layu", "daun muda keriting"}
        mesin, terbukti = jalankan(self.kb, ya, self.semua)
        self.assertEqual(terbukti, [])
        self.assertEqual(len(mesin.ditanya), 9)

    def test_kasus_4_beberapa_kesimpulan_sekaligus(self):
        ya = {"buah membusuk", "bercak cekung kebasahan pada buah", "bercak melingkar konsentris",
              "daun muda keriting", "bercak keperakan di bawah daun"}
        _, terbukti = jalankan(self.kb, ya, self.semua)
        self.assertEqual(terbukti, ["serangan thrips", "antraknosa"])

    def test_tidak_ada_pertanyaan_ganda(self):
        mesin, _ = jalankan(self.kb, set(fakta_dasar_semua(self.kb)), self.semua)
        self.assertEqual(len(mesin.ditanya), len(set(mesin.ditanya)))

    def test_semua_kesimpulan_dapat_dicapai(self):
        _, terbukti = jalankan(self.kb, set(fakta_dasar_semua(self.kb)), self.semua)
        self.assertEqual(terbukti, self.semua)

    def test_semua_tidak_hanya_bertanya_seperlunya(self):
        mesin, terbukti = jalankan(self.kb, set(), self.semua)
        self.assertEqual(terbukti, [])
        self.assertLess(len(mesin.ditanya), len(fakta_dasar_semua(self.kb)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
