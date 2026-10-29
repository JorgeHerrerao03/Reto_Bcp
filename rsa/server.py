"""App local: servidor HTTP (stdlib) + la misma UI del reporte en 'modo app'.
python -m rsa app → abre el navegador en http://127.0.0.1:8765 (solo escucha en localhost)."""
from __future__ import annotations

import base64
import json
import re
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import llm
from .brain import PROMPT_VER
from .engine import AGENT_DIR, Engine
from .search import search

LOCK = threading.Lock()
DEMOS = {"contradice": "F19_contradice.md", "confirma": "F20_confirma.md", "ruido": "F21_ruido.md"}


def make_handler(eng: Engine):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *a):
            print("[app]", self.command, self.path, a[1] if len(a) > 1 else "")

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else (
                body.encode() if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode())
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                try:  # se regenera con el código de interfaz actual (recarga report.py: no hace falta reiniciar)
                    import importlib
                    from . import report, tools
                    importlib.reload(tools)
                    importlib.reload(report)
                    with LOCK:
                        report.write(eng.state, eng.out / "reporte.html")
                except Exception:
                    traceback.print_exc()
                html = (eng.out / "reporte.html").read_text(encoding="utf-8")
                return self._send(200, html.replace("<head>", "<head><script>window.RSA_APP=true</script>", 1),
                                  "text/html; charset=utf-8")
            if self.path == "/api/status":
                return self._send(200, self.status())
            if self.path.startswith("/api/brief/") and ".docx" in self.path:
                from urllib.parse import urlparse, parse_qs
                u = urlparse(self.path)
                sid = u.path.rsplit("/", 1)[-1].replace(".docx", "")
                vs = eng.state["versiones"]
                q = (parse_qs(u.query).get("v") or [""])[0]
                ver = next((x for x in vs if str(x["v"]) == q), None) or (vs[-1] if vs else None)  # pestaña vieja → última
                if not ver or not any(x["id"] == sid for x in ver["signals"]):
                    return self._send(404, {"error": f"La señal {sid} no existe en la versión {q or 'actual'}. "
                                                      "Recarga la página (Ctrl+F5) e inténtalo de nuevo."})
                vi = vs.index(ver)
                try:
                    with LOCK:
                        data = eng.docx(sid, ver)
                except Exception as e:
                    traceback.print_exc()
                    return self._send(500, {"error": f"No se pudo generar el Word: {type(e).__name__}: {e}"})
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.send_header("Content-Disposition", f'attachment; filename="{sid}_brief_v{vi + 1}.docx"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if self.path.startswith("/api/brief/"):
                sid = self.path.rsplit("/", 1)[-1].replace(".md", "")
                f = eng.out / "briefs" / f"{sid}_brief.md"
                if f.exists():
                    return self._send(200, f.read_bytes(), "text/markdown; charset=utf-8")
            self._send(404, {"error": "no encontrado"})

        def status(self):
            return {"versiones": len(eng.state["versiones"]), "incorporadas": eng.state["incorporadas"],
                    "next_id": eng.next_id(), "llm": llm.status(),
                    "motor": eng.motor_mode()}

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "JSON inválido"})
            route = {"/api/preview": self.preview, "/api/incorporar": self.incorporar,
                     "/api/deshacer": self.deshacer, "/api/reset": self.reset, "/api/demo": self.demo,
                     "/api/preguntar": self.preguntar, "/api/config": self.config, "/api/llm/test": self.llm_test,
                     "/api/llm/resumenes": self.resumenes}.get(self.path)
            if not route:
                return self._send(404, {"error": "ruta no existe"})
            try:
                with LOCK:
                    return self._send(200, route(body))
            except (ValueError, RuntimeError, FileNotFoundError) as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:
                traceback.print_exc()
                return self._send(500, {"error": f"{type(e).__name__}: {e}"})

        # ---- acciones ----
        def _md(self, b):
            if b.get("markdown"):
                return b["markdown"]
            data = base64.b64decode(b["b64"]) if b.get("b64") else b.get("texto", "")
            md = eng.build_md(data=data, filename=b.get("filename", ""), meta=b.get("meta") or {})
            return eng.free_id(md)  # ID ocupado o inválido → siguiente libre

        def preview(self, b):
            return eng.preview(self._md(b))

        def incorporar(self, b):
            v = eng.incorporar(md=self._md(b))
            return {"ok": True, "v": v["v"], "explicacion": v["diff"]["explicacion"], "cambios": list(v["diff"]["cambios"])}

        def deshacer(self, b):
            return {"ok": True, "retirada": eng.deshacer()}

        def reset(self, b):
            eng.reset()
            eng.run()
            return {"ok": True}

        def demo(self, b):
            p = AGENT_DIR / "demo" / DEMOS[b.get("caso", "contradice")]
            v = eng.incorporar(md=eng.free_id(eng.build_md(path=p)))  # repetir una demo → siguiente ID libre
            return {"ok": True, "v": v["v"], "explicacion": v["diff"]["explicacion"], "cambios": list(v["diff"]["cambios"])}

        def preguntar(self, b):
            q = (b.get("q") or "").strip()
            if not q:
                raise ValueError("Escribe una pregunta")
            hits = search(eng.latest(), q, 8)
            out = {"hits": hits, "llm": None}
            if b.get("llm") and llm.status()["configurada"] and hits:
                try:
                    out["llm"] = llm.answer(q, hits)
                except Exception as e:
                    out["llm"] = {"error": str(e)}
            return out

        def config(self, b):
            llm.save_cfg(b.get("key"), b.get("model"))
            return llm.status()

        def llm_test(self, b):
            return llm.test()

        def resumenes(self, b):
            v = eng.run(evento="re-análisis con Claude")
            return {"ok": True, "aceptados": sum(1 for s in v["signals"] if s.get("resumen_llm")),
                    "total": len(v["signals"])}

    return H


def serve(eng: Engine, port=8765, open_browser=True):
    last = (eng.latest().get("motor") or {}).get("modo") if eng.state["versiones"] else None
    if not eng.state["versiones"]:
        print("  Analizando las fuentes" + (" con Claude (20-40 s la primera vez)…" if eng.motor_mode() == "claude" else "…"))
        eng.run()
    elif eng.motor_mode() == "claude" and (last != "claude" or
                                           (eng.latest().get("motor") or {}).get("prompt_ver") != PROMPT_VER):
        print("  Hay API key y la última versión se hizo con reglas o con una versión anterior del motor: "
              "re-analizando con Claude (20-40 s)…", flush=True)
        v = eng.run(evento="re-análisis con Claude")
        print("  Motor:", (v.get("motor") or {}).get("modo"), "·", (v.get("motor") or {}).get("aviso", "ok"))
    else:  # regenerar siempre la UI con el código actual (evita servir un reporte viejo)
        from . import report
        print("  Revenue Signals Agent · preparando briefs y reporte (con Claude puede tardar 10-30 s)…", flush=True)
        n = eng.ensure_briefs()
        if n:
            print(f"  Briefs estratégicos completados para {n} señales de la versión guardada")
        try:  # reescribe out/briefs (md, traza, docx) y reporte con el código actual
            eng._write(eng.latest(), {s.id: s for s in eng.sources()})
        except Exception as e:
            print("  Aviso: no se pudieron regenerar los briefs:", e)
            report.write(eng.state, eng.out / "reporte.html")
    print("  Motor activo:", "Claude decide, reglas auditan" if eng.motor_mode() == "claude" else
          "solo reglas (no hay ANTHROPIC_API_KEY en .env o se forzó --solo-reglas)")
    for p in range(port, port + 20):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), make_handler(eng))
            break
        except OSError:
            continue
    else:
        raise SystemExit("No hay puertos libres")
    url = f"http://127.0.0.1:{p}/"
    print(f"\n  Revenue Signals Agent · app en {url}\n  (Ctrl+C para cerrar)\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")
