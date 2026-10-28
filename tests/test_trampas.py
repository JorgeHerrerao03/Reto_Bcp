"""Evals contra las trampas del paquete. Ejecutar: python -m unittest discover -s tests -t . -v
Los tests del núcleo corren en modo reglas (reproducible, sin API); test_claude.py prueba el modo Claude con un stub."""
import os
os.environ["RSA_MODO"] = "reglas"
import re
import tempfile
import unittest
from pathlib import Path

from rsa.engine import AGENT_DIR, Engine


class Trampas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.eng = Engine(out=cls.tmp.name)
        cls.v = cls.eng.run()
        cls.S = {s["palanca"]: s for s in cls.v["signals"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def sig(self, txt):
        return next(s for s in self.v["signals"] if txt in s["titulo"])

    def test_ingesta_18(self):
        self.assertEqual(len(self.v["fuentes"]), 18)

    def test_ruido_f13_f16(self):
        self.assertEqual({d["fuente"] for d in self.v["descartadas"]}, {"F13", "F14", "F15", "F16"})

    def test_cuatro_senales_y_s1_primero(self):
        self.assertEqual(len(self.v["signals"]), 4)
        self.assertIn("seguro", self.v["signals"][0]["titulo"])

    def test_agrupamiento(self):
        got = sorted(tuple(s["fuentes"]) for s in self.v["signals"])
        self.assertEqual(got, sorted([("F01", "F02", "F03", "F04"), ("F05", "F06", "F07"),
                                      ("F08", "F09", "F10", "F11", "F12"), ("F17", "F18")]))

    def test_f12_corrige_f11(self):
        s = self.sig("día de pago")
        c = {x["sid"]: x for x in s["claims"]}
        self.assertEqual(c["F11.1"].get("superada"), "refutada")
        self.assertTrue(c["F11.1"]["por"].startswith("F12"))

    def test_no_cuantifica_s1(self):
        s = self.sig("seguro")
        self.assertTrue(any("No cuantifico" in m for m in s["no_afirmo"]))
        brief = (Path(self.tmp.name) / "briefs" / f"{s['id']}_brief.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"S/\s?\d|\d+\s?%|USD", brief))

    def test_no_recomienda_eliminar_comisiones(self):
        s = self.sig("Comisiones")
        self.assertTrue(any("No recomiendo eliminar" in m for m in s["no_afirmo"]))
        self.assertNotIn("eliminar", s["recomendacion"] if "recomendacion" in s else "")

    def test_herramienta_web_vs_sucursal(self):
        calls = [e for e in self.v["log"] if e["accion"] == "consulta_herramienta"]
        self.assertEqual([c["args"][1] for c in calls], ["Web", "Sucursal"])
        self.assertTrue(all(c["resultado"]["encontrado"] for c in calls))

    def test_herramienta_omitida_con_motivo(self):
        om = [e for e in self.v["log"] if e["accion"] == "consulta_omitida"]
        self.assertTrue(om and all(e["motivo"] for e in om))

    def test_citas_existen(self):
        sids = {s["sid"] for f in self.v["fuentes"] for s in f["sents"]}
        for s in self.v["signals"]:
            for c in s["claims"]:
                self.assertIn(c["sid"], sids)

    def test_incorporar_contradice_y_ruido(self):
        with tempfile.TemporaryDirectory() as d:
            e = Engine(out=d)
            e.run()
            v = e.incorporar(AGENT_DIR / "demo" / "F19_contradice.md")
            s1 = next(s for s in v["signals"] if "seguro" in s["titulo"])
            self.assertIn("F19", s1["fuentes"])
            self.assertLess(s1["score"], e.state["versiones"][0]["signals"][0]["score"])
            self.assertTrue(any(t["sid"] == "F01.2" for t in v["diff"]["cambios"][s1["id"]]["transiciones"]))
            v = e.incorporar(AGENT_DIR / "demo" / "F21_ruido.md")
            self.assertIn("F21", v["diff"]["descartadas_nuevas"])
            with self.assertRaises(ValueError):
                e.incorporar(AGENT_DIR / "demo" / "F21_ruido.md")

    def test_originales_intactos(self):
        import hashlib
        for f in self.v["fuentes"]:
            raw = Path(f["archivo"]).read_text(encoding="utf-8-sig")
            self.assertEqual(hashlib.sha1(raw.encode()).hexdigest()[:10], f["sha1"])


if __name__ == "__main__":
    unittest.main()


class App(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.eng = Engine(out=self.tmp.name)
        self.eng.run()

    def tearDown(self):
        self.tmp.cleanup()

    def test_preview_no_persiste(self):
        md = self.eng.build_md(data="Finanzas concilió la comisión cobrada con la cuenta contable.", meta={"area": "Finanzas"})
        p = self.eng.preview(md)
        self.assertEqual(p["fuente"]["id"], "F19")
        self.assertEqual(len(self.eng.state["versiones"]), 1)
        self.assertEqual(self.eng.state["incorporadas"], [])

    def test_incorporar_texto_y_deshacer(self):
        md = self.eng.build_md(data="La cafetería cambia de horario. No modifica tarifas ni cobros.", meta={})
        v = self.eng.incorporar(md=md)
        self.assertIn("F19", v["diff"]["descartadas_nuevas"])
        self.assertEqual(self.eng.deshacer(), "F19")
        self.assertEqual(len(self.eng.state["versiones"]), 1)
        self.assertEqual(len(self.eng.sources()), 18)

    def test_docx(self):
        import io, zipfile
        from rsa.convert import raw_text
        xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
               '<w:p><w:r><w:t>Hola</w:t></w:r></w:p><w:p><w:r><w:t>mundo</w:t></w:r></w:p></w:body></w:document>')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", xml)
        self.assertEqual(raw_text("a.docx", buf.getvalue()), "Hola\n\nmundo")

    def test_sync_ordena_por_fecha(self):
        v = self.eng.sync(AGENT_DIR / "demo")
        self.assertEqual(self.eng.state["incorporadas"], ["F19", "F20", "F21"])
        self.assertEqual(len(self.eng.state["versiones"]), 4)

    def test_busqueda(self):
        from rsa.search import search
        hits = search(self.eng.latest(), "maqueta selector de fechas")
        self.assertEqual(hits[0]["fuente"], "F12")
