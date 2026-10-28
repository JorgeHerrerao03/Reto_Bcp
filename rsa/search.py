"""Recuperación de oraciones (TF-IDF) sobre la versión vigente: base de 'Preguntar a las fuentes'."""
from __future__ import annotations

from .text import TfIdf


def search(ver, q, k=8):
    sents = {s["sid"]: (f, s) for f in ver["fuentes"] for s in f["sents"]}
    if not sents:
        return []
    tf = TfIdf({sid: s["texto"] + " " + f["titulo"] for sid, (f, s) in sents.items()})
    sig_of = {f: s["id"] for s in ver["signals"] for f in s["fuentes"]}
    noise = {d["fuente"] for d in ver["descartadas"]}
    st = {c["sid"]: c.get("superada") or c["tipo"] for s in ver["signals"] for c in s["claims"]}
    out = []
    ranked = sorted(((sc * (1.35 if st.get(sid) == "correccion" else 1), sid) for sc, sid in tf.query(q)), reverse=True)
    for score, sid in ranked[:k]:
        f, s = sents[sid]
        out.append({"sid": sid, "texto": s["texto"], "fuente": f["id"], "fecha": f["fecha"], "titulo": f["titulo"],
                    "senal": sig_of.get(f["id"]) or ("ruido" if f["id"] in noise else None),
                    "estado": st.get(sid), "score": round(score, 3)})
    return out
