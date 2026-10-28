"""Normalización, tokenización y TF-IDF (stdlib, determinístico)."""
import math
import re
import unicodedata
from collections import Counter

STOP = set("""a al algo algunas algunos ante antes aun aunque cada como con contra cual cuando de del desde donde dos e el ella
ellas ellos en entre era es esa ese eso esta estan estar este esto estos fue ha han hay la las le les lo los mas me mi muy
no nos o otra otro otros para pero poco por que quien se sea segun ser si sin sobre su sus tambien tan te tiene todo toda
todos tras un una uno unos y ya debe deben puede podria cierto cierta ningun ninguna ningunos esa esas mismo misma
mediante solo vez aun todavia ademas asi dato datos parte""".split())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def stem(w: str) -> str:
    # stemmer liviano ES: suficiente para agrupar plurales/derivados frecuentes
    for suf in ("aciones", "acion", "amiento", "imientos", "imiento", "ables", "able", "idades", "idad",
                "ados", "adas", "ado", "ada", "idos", "idas", "ido", "ida", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(s: str):
    return [stem(w) for w in re.findall(r"[a-z_]{3,}", norm(s)) if w not in STOP]


def sentences(text: str):
    text = re.sub(r"\s+", " ", text).strip()
    return [p.strip() for p in re.split(r"(?<=[.;!?])\s+(?=[A-ZÁÉÍÓÚÑ«\"])", text) if p.strip()]


class TfIdf:
    def __init__(self, docs: dict):
        self.tf = {k: Counter(tokens(v)) for k, v in docs.items()}
        n = len(docs)
        df = Counter(t for c in self.tf.values() for t in c)
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
        self.vec = {}
        for k, c in self.tf.items():
            v = {t: (1 + math.log(f)) * self.idf[t] for t, f in c.items()}
            nrm = math.sqrt(sum(x * x for x in v.values())) or 1
            self.vec[k] = {t: x / nrm for t, x in v.items()}

    def cos(self, a, b):
        va, vb = self.vec[a], self.vec[b]
        if len(va) > len(vb):
            va, vb = vb, va
        return sum(x * vb.get(t, 0) for t, x in va.items())

    def top_terms(self, keys, n=5):
        acc = Counter()
        for k in keys:
            for t, x in self.vec[k].items():
                acc[t] += x
        return [t for t, _ in acc.most_common(n)]

    def query(self, q: str, keys=None):
        qt = Counter(tokens(q))
        out = []
        for k in keys or self.vec:
            s = sum(self.vec[k].get(t, 0) * self.idf.get(t, 0) for t in qt)
            if s > 0:
                out.append((s, k))
        return sorted(out, reverse=True)
