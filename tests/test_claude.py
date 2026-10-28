"""Modo Claude-first con un stub de la API (sin red): valida cableado, validación de IDs, auditoría y comité."""
import json
import os
import re
import tempfile
import unittest
from unittest import mock

from rsa import llm
from rsa.engine import AGENT_DIR, Engine

FUENTE_EN = """# Fee de onboarding

**ID:** F19
**Fecha:** 2026-09-26
**Tipo:** Teams
**Área:** Banca Mayorista

FYI, the onboarding fee is not being charged in the digital channel since the last release. Pending confirmar con IT si aplica a todas las cuentas.
"""


def fake_call(prompt, max_tokens=500, system=None, temperature=None):
    """Stub determinístico que imita el contrato JSON de cada tipo de llamada."""
    meta = {"modelo": "stub", "tokens": {"input_tokens": 100, "output_tokens": 50}, "costo_usd": 0.00003, "ms": 1}
    sids = re.findall(r"^(F\d+\.\d+) \|", prompt, re.M)
    if prompt.startswith("Fuente "):
        low = prompt.split("Palancas económicas conocidas")[0].lower()
        ruido = any(k in low for k in ("no cambia ninguna", "no existe vínculo", "no afectará", "no se modificarán"))
        pal = ("Comisiones de baja frecuencia sin conciliar" if re.search(r"\bfee\b|comisi|tarifa", low) else
               "Posible desviación en cobro de seguro" if re.search(r"desgravamen|prima|rate_input", low) else
               "Exoneración de membresía: retención vs. ingreso" if "membres" in low else
               "Cambio de calendario / día de pago" if re.search(r"fecha|calendario|día de pago", low) else None)
        ora = []
        for s in sids:
            line = re.search(rf"^{re.escape(s)} \| (.*)$", prompt, re.M).group(1).lower()
            tipo = ("faltante" if re.search(r"pending|no se ha confirmado|se solicita|falta", line) else
                    "correccion" if re.search(r"en realidad|aclara|maqueta|actually", line) else
                    "hipotesis" if re.search(r"parece|podría|planea|estaría", line) else "hecho")
            ora.append({"sid": s, "tipo": tipo, "accion": tipo == "faltante", "razon": "stub"})
        ora.append({"sid": "F99.9", "tipo": "hecho"})  # ID inventado: debe descartarse
        d = {"relevante": not ruido and pal is not None, "motivo_ruido": "sin vínculo (stub)" if ruido else None,
             "sid_ruido": sids[-1] if ruido else None, "palanca": pal, "operacional": "not being charged" in low,
             "producto": None, "canal": "Web" if "digital" in low else None, "parametro": None,
             "terminos": ["comisión", "cobro", "canal digital"] if "fee" in low else [], "oraciones": ora}
    elif prompt.startswith("Señal:") and "relaciones" in prompt:
        d = {"relaciones": [{"de": "F99.1", "a": "F01.1", "relacion": "refuta", "motivo": "ID inválido"}],
             "cautelas": ["No cuantificar sin conciliación (stub)"]}
        if "F19.1" in sids and "F17.3" in sids:
            d["relaciones"].append({"de": "F19.1", "a": "F17.3", "relacion": "confirma", "motivo": "stub"})
    elif "Argumenta la postura" in prompt:
        d = {"argumento": "stub " + sids[0] if sids else "stub"}
    elif "juez imparcial" in prompt:
        d = {"veredicto": "si", "motivo": "stub"}
    elif '"resumen"' in prompt:
        d = {"resumen": f"Resumen stub [{sids[0]}] y [{sids[1]}]."}
    else:
        d = {}
    return json.dumps(d, ensure_ascii=False), meta


class ClaudeFirst(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.pop("RSA_MODO", None)
        self.p = [mock.patch.object(llm, "call", fake_call),
                  mock.patch.object(llm, "cfg", lambda: {"key": "sk-test", "model": "stub", "price_in": 0.1, "price_out": 0.5}),
                  mock.patch("rsa.engine.AGENT_DIR", AGENT_DIR)]
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

    def test_motor_claude_y_auditoria(self):
        v = self.eng.run()
        self.assertEqual(v["motor"]["modo"], "claude")
        self.assertEqual({d["fuente"] for d in v["descartadas"]}, {"F13", "F14", "F15", "F16"})
        s = v["signals"][0]
        self.assertIn("auditoria", s)
        self.assertTrue(all(c["sid"] != "F99.9" for c in s["claims"]))          # ID inventado descartado
        self.assertTrue(all(not x["de"].startswith("F99") for x in s["contradicciones"]))
        self.assertTrue(any("stub" in m for m in s["no_afirmo"]))                # cautelas de Claude
        self.assertTrue(s.get("resumen_llm"))

    def test_fuente_en_ingles(self):
        self.eng.run()
        p = self.eng.preview(FUENTE_EN)
        self.assertIsNone(p["descartada"])                                       # reglas la descartarían
        s2 = next(s for s in p["ranking"] if "Comisiones" in s["titulo"])
        self.assertTrue(s2)
        tipos = {c["sid"]: c["tipo"] for c in p["clasificacion"]}
        self.assertEqual(tipos["F19.2"], "faltante")                             # "Pending" entendido

    def test_cache(self):
        self.eng.run()
        v2 = self.eng.run()
        self.assertEqual(v2["motor"]["llamadas"], 0)
        self.assertGreater(v2["motor"]["cache"], 0)

    def test_fallback_sin_key(self):
        e = Engine(out=os.path.join(self.tmp.name, "out2"), solo_reglas=True)
        self.assertEqual(e.run()["motor"]["modo"], "reglas")
