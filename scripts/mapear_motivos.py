"""Cruza los motivos de objeción del hospital con el catálogo oficial de glosas (scraping).

Para cada motivo busca el código de glosa más parecido (TF-IDF + similitud del coseno). El concepto general se fija por prefijo
("TARIFAS - ...") o por palabras clave de las definiciones del manual; el código específico, por similitud.
"""
import re, unicodedata
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PREFIJOS = {"FACTURACION": 1, "TARIFAS": 2, "SOPORTES": 3, "AUTORIZACION": 4, "AUTORIZACIONES": 4,
            "COBERTURA": 5, "PERTINENCIA": 6}
STOP = set("de la el los las y o en que a por con para un una se al del lo su sus es son ser como mas".split())


# Señales del texto de cada concepto general, tomadas de sus definiciones en el manual (se evalúan en este orden)
SENALES = [
    (3, r"ausencia|ilegib|enmendadura|inconsisten"),                       # Soportes
    (4, r"autorizad|autorizacion|orden o autorizacion"),                   # Autorización
    (6, r"pertinen|justificacion medica"),                                 # Pertinencia
    (5, r"respectiva cobertura|respectivo plan|hacen parte integral|servicio no pactado|poliza"),# Cobertura
    (2, r"pactad|tarifa|recargo"),                                         # Tarifas
    (1, r"cantidades|facturad|copago|cuota moderadora|usuario|capitacion"),# Facturación
]


def inferir_general(motivo):
    """Concepto general (1-6) según el prefijo explícito o las palabras clave del manual; None si no hay señal."""
    m = str(motivo)
    pref = re.match(r"^\s*([A-Za-zÁÉÍÓÚáéíóú]+)\s*-", m)
    if pref and PREFIJOS.get(normalizar(pref.group(1)).upper()):
        return PREFIJOS[normalizar(pref.group(1)).upper()], "prefijo"
    n = normalizar(m)
    for cod, patron in SENALES:
        if re.search(patron, n):
            return cod, "palabras clave"
    return None, "similitud"


def normalizar(t):
    t = unicodedata.normalize("NFKD", str(t).lower()).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return " ".join(w for w in t.split() if w not in STOP)


def mapear_motivos(motivos, catalogo, umbral=0.20, margen_min=0.03):
    motivos = pd.Series(list(motivos)).dropna().astype(str).unique()
    columnas = ["motivo", "codigo", "concepto_general", "concepto_especifico", "score", "margen", "regla", "revisar"]
    if not len(motivos):
        return pd.DataFrame(columns=columnas)
    if catalogo.empty:
        raise ValueError("El catálogo está vacío.")
    catalogo = catalogo.reset_index(drop=True)
    docs = (catalogo["concepto_especifico"].fillna("") + " " + catalogo["texto"].fillna("")).map(normalizar)
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    M = vec.fit_transform(list(docs) + [normalizar(m) for m in motivos])
    S = cosine_similarity(M[len(docs):], M[:len(docs)])
    gen = catalogo["concepto_general_cod"].to_numpy()

    filas = []
    for i, m in enumerate(motivos):
        s = S[i].copy()
        fijo, regla = inferir_general(m)
        if fijo is not None and (gen == fijo).any():
            s = np.where(gen == fijo, s, -1)
        elif fijo is not None:
            regla = "similitud"
        orden = np.argsort(-s, kind="stable")
        b = orden[0]
        segundo = max(0.0, s[orden[1]]) if len(orden) > 1 else 0.0
        filas.append({"motivo": m, "codigo": catalogo.loc[b, "codigo"],
                      "concepto_general": catalogo.loc[b, "concepto_general"],
                      "concepto_especifico": catalogo.loc[b, "concepto_especifico"],
                      "score": round(float(s[b]), 3), "margen": round(float(s[b] - segundo), 3),
                      "regla": regla})
    out = pd.DataFrame(filas)
    out["revisar"] = (out["score"] < umbral) | ((out["margen"] < margen_min) & (out["regla"] == "similitud"))
    return out


def agregar_concepto_general(df, mapa, col="Concepto de Objecion"):
    """Añade codigo_glosa y concepto_general (oficial) al DataFrame del hospital."""
    m = mapa.set_index("motivo")[["codigo", "concepto_general"]].rename(columns={"codigo": "codigo_glosa"})
    return df.join(m, on=col)
