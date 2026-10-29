"""Regresiones de la auditoría externa: contradicciones con Claude parcial, fallos de la API, deshacer tras
re-análisis, IDs, sync, demos repetidas, cifras y cautelas que evolucionan con la evidencia."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rsa import brain, llm
from rsa.engine import AGENT_DIR, Engine

from tests.test_claude import fake_call

DEMO = Path(AGENT_DIR) / "demo"


def stub(rel_mode):
    """fake_call con Claude que clasifica F12.1 como HECHO y una etapa de relaciones que falla o no ve nada."""
    def call(prompt, max_tokens=500, system=None, temperature=None):
        txt, meta = fake_call(prompt, max_tokens, system, temperature)
        if isinstance(prompt, str) and prompt.startswith("Fuente F12"):
            d = json.loads(txt)
            for o in d["oraciones"]:
                o["tipo"] = "hecho"
            txt = json.dumps(d, ensure_ascii=False)
        if isinstance(prompt, str) and prompt.startswith("Señal:") and "relaciones" in prompt:
            if rel_mode == "falla":
                return "Lo siento, no puedo", {**meta, "stop_reason": "end_turn"}
            if rel_mode == "vacio":
                return json.dumps({"relaciones": [], "cautelas": []}), meta
        return txt, meta
    return call


class Base(unittest.TestCase):
    rel_mode = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.pop("RSA_MODO", None)
        call = stub(self.rel_mode) if self.rel_mode else fake_call
        self.p = [mock.patch.object(llm, "call", call),
                  mock.patch.object(llm, "cfg", lambda: {"key": "sk-test", "model": "stub", "price_in": 0.1, "price_out": 0.5})]
        for x in self.p:
            x.start()
        import rsa.engine as E
        self._brain = E.Engine.brain
        cache = os.path.join(self.tmp.name, "cache.json")
        E.Engine.brain = lambda s: None if s.solo_reglas else E.Brain(cache)
        self.eng = Engine(out=os.path.join(self.tmp.name, "out"))

    def tearDown(self):
        import rsa.engine as E
        E.Engine.brain = self._brain
        for x in self.p:
            x.stop()
        os.environ["RSA_MODO"] = "reglas"
        self.tmp.cleanup()

    def s4(self, v):
        return next(s for s in v["signals"] if "calendario" in s["titulo"].lower())


class RelacionesFallan(Base):
    rel_mode = "falla"

    def test_f12_refuta_f11_aunque_claude_falle(self):
        v = self.eng.run()
        st = {c["sid"]: c.get("superada") for c in self.s4(v)["claims"]}
        self.assertEqual(st["F11.1"], "refutada")
        self.assertEqual(self.s4(v)["auditoria"]["relaciones_motor"], "reglas (Claude falló)")
        self.assertIn("aviso", v["motor"])                         # el fallo se informa, no se oculta
        self.assertGreater(v["motor"]["etapas"]["relaciones"]["fallo"], 0)
        self.assertGreater(v["motor"]["costo_usd"], 0)             # una respuesta inválida también se contabiliza
        self.assertNotIn("F11.1", [x["cita"] for x in self.s4(v)["brief"]["creemos"]])


class RelacionesVacias(Base):
    rel_mode = "vacio"

    def test_correccion_explicita_prevalece(self):
        v = self.eng.run()
        st = {c["sid"]: c.get("superada") for c in self.s4(v)["claims"]}
        self.assertEqual(st["F11.1"], "refutada")


class Robustez(Base):
    def test_deshacer_tras_reanalisis(self):
        self.eng.run()
        self.eng.incorporar(path=DEMO / "F19_contradice.md")
        self.eng.run(evento="re-análisis")
        self.assertEqual(self.eng.deshacer(), "F19")
        self.assertNotIn("F19", [f["id"] for f in self.eng.latest()["fuentes"]])
        self.assertEqual(self.eng.state["incorporadas"], [])

    def test_id_invalido(self):
        self.eng.run()
        md = (DEMO / "F19_contradice.md").read_text(encoding="utf-8").replace("**ID:** F19", "**ID:** ../escape")
        with self.assertRaises(ValueError):
            self.eng.incorporar(md=md)
        self.assertTrue(self.eng.free_id(md).count("**ID:** F19"))

    def test_demo_repetida(self):
        self.eng.run()
        md = self.eng.build_md(path=DEMO / "F21_ruido.md")
        self.eng.incorporar(md=self.eng.free_id(md))
        v = self.eng.incorporar(md=self.eng.free_id(self.eng.build_md(path=DEMO / "F21_ruido.md")))
        self.assertEqual(len(set(self.eng.state["incorporadas"])), 2)
        self.assertEqual(len(v["fuentes"]), 20)

    def test_sync_sin_id(self):
        d = Path(self.tmp.name) / "nuevas"
        d.mkdir()
        for n in ("nueva1.md", "nueva2.md"):
            (d / n).write_text("**Fecha:** 2026-09-27\n\nLa comisión de mantenimiento se cobra dos veces.\n", encoding="utf-8")
        v = self.eng.sync(d)
        self.assertEqual(sorted(self.eng.state["incorporadas"]), ["F19", "F20"])
        self.assertEqual(len(v["fuentes"]), 20)

    def test_brief_refleja_cambio(self):
        self.eng.run()
        v = self.eng.incorporar(path=DEMO / "F19_contradice.md")
        s1 = next(s for s in v["signals"] if "seguro" in s["titulo"])
        self.assertTrue(s1["brief"]["cambio"])
        self.assertFalse(any("no distingue producción de certificación" in m for m in s1["no_afirmo"]))
        self.assertTrue(any(m.startswith("Actualizado por F19") for m in s1["no_afirmo"]))


class Cifras(unittest.TestCase):
    def test_cifras(self):
        ev = {"F01.1": "El monto aún se desconoce.", "F02.1": "Se revisaron 2026 casos.", "F04.9": "Web equivale al 8.29% de Sucursal"}
        self.assertFalse(llm._check("El monto es 999 [F01.1].", list(ev), ev)[2])
        self.assertFalse(llm._check("La prima es 20% [F02.1].", list(ev), ev)[2])
        self.assertTrue(llm._check("Web equivale al 8.29% de Sucursal [F04.9].", list(ev), ev)[2])
        self.assertFalse(llm._check("Web equivale al 8.29% [F01.1].", list(ev), ev)[2])   # cifra contra la cita
        self.assertTrue(llm._check("Hay 3 fuentes que coinciden [F01.1].", list(ev), ev)[2])

    def test_parse(self):
        self.assertEqual(brain._parse('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(brain._parse('Claro: {"a": {"b": 2}} fin {x}'), {"a": {"b": 2}})
        with self.assertRaises(ValueError):
            brain._parse("")


if __name__ == "__main__":
    unittest.main()
