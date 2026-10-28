"""CLI: python -m rsa <comando>"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from . import brief
from .engine import AGENT_DIR, Engine
from .tools import invoke

for st in (sys.stdout, sys.stderr):
    try:
        st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def table(ver):
    print(f"\nv{ver['v']} · {ver['evento']} · {len(ver['fuentes'])} fuentes")
    print(f"{'#':<3}{'ID':<5}{'Score':>6}  {'Madurez':<8}{'Fuentes':<26}Señal")
    for i, s in enumerate(ver["signals"], 1):
        print(f"{i:<3}{s['id']:<5}{s['score']:>6}  {s['confianza']:<8}{','.join(s['fuentes']):<26}{s['titulo']}")
    print("Descartadas:", ", ".join(f"{d['fuente']}" for d in ver["descartadas"]) or "—")


def show_diff(ver):
    d = ver.get("diff")
    if not d:
        return
    print("\n=== QUÉ CAMBIÓ Y POR QUÉ ===")
    for line in d["explicacion"] or ["Sin cambios materiales en señales."]:
        print(" ", line)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rsa", description="Revenue Signals Agent")
    ap.add_argument("--paquete")
    ap.add_argument("--out")
    ap.add_argument("--llm", action="store_true", help="resumen ejecutivo con Claude (requiere ANTHROPIC_API_KEY)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run").add_argument("--reset", action="store_true")
    sub.add_parser("senales")
    p = sub.add_parser("investigar"); p.add_argument("sid")
    p = sub.add_parser("incorporar"); p.add_argument("archivos", nargs="+")
    p = sub.add_parser("consultar"); p.add_argument("producto"); p.add_argument("canal"); p.add_argument("parametro")
    sub.add_parser("reporte").add_argument("--abrir", action="store_true")
    p = sub.add_parser("demo"); p.add_argument("--caso", default="contradice", choices=["contradice", "confirma", "ruido", "todos"])
    p = sub.add_parser("app", help="interfaz gráfica local"); p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p = sub.add_parser("sync", help="reconstruye e incorpora todos los .md de una carpeta (CI)"); p.add_argument("carpeta")
    sub.add_parser("deshacer")
    p = sub.add_parser("preguntar"); p.add_argument("pregunta")
    p = sub.add_parser("config", help="guarda la API key de Claude en .env"); p.add_argument("--key"); p.add_argument("--model")
    sub.add_parser("llm-test")
    a = ap.parse_args(argv if argv is not None else (sys.argv[1:] or ["app"]))
    eng = Engine(a.paquete, a.out, a.llm)

    if a.cmd == "run":
        if a.reset:
            eng.reset()
        v = eng.run()
        table(v); show_diff(v)
        print(f"\nBriefs: {eng.out / 'briefs'}\nReporte: {eng.out / 'reporte.html'}")
    elif a.cmd == "senales":
        table(eng.latest() if eng.state["versiones"] else eng.run())
    elif a.cmd == "investigar":
        v = eng.latest() if eng.state["versiones"] else eng.run()
        s = next((x for x in v["signals"] if x["id"].lower() == a.sid.lower()), None)
        if not s:
            sys.exit(f"Señal {a.sid} no existe. Usa: python -m rsa senales")
        by = {f["id"]: type("S", (), f) for f in v["fuentes"]}
        print(brief.render(s, by)); print(brief.trace(s, v["log"]))
    elif a.cmd == "incorporar":
        for f in a.archivos:
            v = eng.incorporar(path=f)
            table(v); show_diff(v)
    elif a.cmd == "consultar":
        r = invoke(eng.paquete / "herramientas" / "consultar_parametros.py", a.producto, a.canal, a.parametro)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        if eng.state["versiones"]:
            eng.latest()["log"].append({"accion": "consulta_manual", **r})
            eng.state_f.write_text(json.dumps(eng.state, ensure_ascii=False, indent=1), encoding="utf-8")
    elif a.cmd == "reporte":
        from . import report
        report.write(eng.state, eng.out / "reporte.html")
        print(eng.out / "reporte.html")
        if a.abrir:
            webbrowser.open((eng.out / "reporte.html").resolve().as_uri())
    elif a.cmd == "demo":
        eng.reset()
        table(eng.run())
        casos = {"contradice": ["F19_contradice.md"], "confirma": ["F20_confirma.md"], "ruido": ["F21_ruido.md"],
                 "todos": ["F19_contradice.md", "F20_confirma.md", "F21_ruido.md"]}[a.caso]
        for c in casos:
            v = eng.incorporar(path=AGENT_DIR / "demo" / c)
            table(v); show_diff(v)
        print(f"\nReporte: {eng.out / 'reporte.html'}")
    elif a.cmd == "app":
        from .server import serve
        serve(eng, a.port, not a.no_browser)
    elif a.cmd == "sync":
        v = eng.sync(a.carpeta)
        table(v)
        print(f"Versiones: {len(eng.state['versiones'])} · Reporte: {eng.out / 'reporte.html'}")
    elif a.cmd == "deshacer":
        print("Retirada:", eng.deshacer()); table(eng.latest())
    elif a.cmd == "preguntar":
        from . import llm
        from .search import search
        v = eng.latest() if eng.state["versiones"] else eng.run()
        hits = search(v, a.pregunta)
        for h in hits:
            print(f"[{h['sid']}] ({h['senal'] or '-'}, {h['estado'] or '-'}) {h['texto']}")
        if a.llm and hits:
            r = llm.answer(a.pregunta, hits)
            print("\nClaude:", r["respuesta"], f"\n(citas válidas: {r['aceptada']} · USD {r['costo_usd']})")
    elif a.cmd == "config":
        from . import llm
        llm.save_cfg(a.key, a.model); print(llm.status())
    elif a.cmd == "llm-test":
        from . import llm
        print(llm.status()); print(llm.test())


if __name__ == "__main__":
    main()
