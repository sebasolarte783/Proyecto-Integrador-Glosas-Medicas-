"""Web scraping del catálogo oficial de glosas (Manual Único de Glosas, Devoluciones y Respuestas).

Fuente pública: Ministerio de Salud y Protección Social, Anexo Técnico No. 6 de la Resolución 3047 de 2008
(modificada por la Resolución 416 de 2009). Contiene los códigos de glosa (101 a 654), el concepto general
(Facturación, Tarifas, Soportes, Autorización, Cobertura, Pertinencia) y la descripción de cuándo aplica.

Uso:
    python scripts/scraping_catalogo.py
Genera:
    data/externos/pdf/catalogo_glosas_minsalud.csv   (una fila por código de glosa)
    data/externos/pdf/log_scraping.json              (evidencia: URL, fecha, estado HTTP, hash, filas extraídas)
    data/externos/pdf/raw/<archivo>.pdf              (copia del documento descargado)
"""
import hashlib, io, json, re, sys, time, urllib.robotparser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

URL = "https://www2.minsalud.gov.co/salud/Documents/Anexo%20tecnico%20No.%20%206%20Res%203047-08%20y%20416-09.pdf"
AGENTE = "ProyectoIntegradorGlosas/1.0"
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "externos"

GENERALES = {1: "Facturación", 2: "Tarifas", 3: "Soportes", 4: "Autorización",
             5: "Cobertura", 6: "Pertinencia", 8: "Devoluciones", 9: "Respuestas"}
ENCABEZADO = re.compile(r"^\s*([1-689])\.\s+(Facturaci[oó]n|Tarifas|Soportes|Autorizaci[oó]n(?:es)?|Cobertura|Pertinencia|"
                        r"Devoluciones|Respuestas)", re.I)


# ---------------------------------------------------------------- descarga
def permitido_por_robots(url):
    p = urlparse(url)
    ubicacion = f"{p.scheme}://{p.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        with urlopen(Request(ubicacion, headers={"User-Agent": AGENTE}), timeout=15) as respuesta:
            rp.parse(respuesta.read().decode("utf-8", errors="replace").splitlines())
        return rp.can_fetch(AGENTE, url)
    except HTTPError as error:
        if error.code in (401, 403):
            return False
        if error.code in (404, 410):
            return True
        return None
    except (URLError, TimeoutError):
        return None


def descargar(url=URL, reintentos=3):
    import requests
    for i in range(reintentos):
        try:
            r = requests.get(url, headers={"User-Agent": AGENTE}, timeout=60)
            r.raise_for_status()
            return r
        except Exception as e:
            if i == reintentos - 1:
                raise
            time.sleep(2 ** i)


def texto_del_pdf(contenido):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


# ---------------------------------------------------------------- análisis del texto
def _limpiar(lineas):
    out = []
    for l in lineas:
        s = l.strip()
        if not s or s.startswith("Continuación ANEXO") or s.startswith("RESPUESTAS - Resolución"):
            continue
        out.append(s)
    return out


def parsear_manual(texto):
    """Devuelve un DataFrame con una fila por código de glosa (3 dígitos)."""
    lineas = _limpiar(texto.splitlines())

    # Tabla 2: nombre de cada concepto específico (código de 2 dígitos)
    nombres, en_tabla = {}, False
    ultimo = None
    for l in lineas:
        if "Tabla No. 2" in l:
            en_tabla = True; continue
        if en_tabla and ("RESPUESTAS DE GLOSA" in l or "Tabla No. 3" in l):
            break
        if en_tabla:
            m = re.match(r"^(\d{2})\s+(.+)$", l)
            if m:
                ultimo = m.group(1); nombres[ultimo] = m.group(2).strip()
            elif ultimo and not l.startswith("Código"):
                nombres[ultimo] += " " + l

    # Manual de uso: secciones 1..6 con registros que empiezan por el código de 3 dígitos
    inicio = next((i for i, l in enumerate(lineas) if l.startswith("Manual de Uso")), 0)
    registros, general, actual = [], None, None
    for l in lineas[inicio:]:
        h = ENCABEZADO.match(l)
        if h and len(l) < 120 and not re.match(r"^\d\.\s+(El|Los|La|Las|Se)\b", l):
            general = int(h.group(1)); actual = None
            continue
        if general not in (1, 2, 3, 4, 5, 6):
            continue
        m = re.match(r"^(\d{3})\b(?!\s*[/%.,])\s*(.*)$", l)
        if m and int(m.group(1)[0]) == general and m.group(1)[1:] in nombres:
            actual = {"codigo": m.group(1), "general": general, "texto": [m.group(2)]}
            registros.append(actual)
        elif actual is not None:
            actual["texto"].append(l)

    filas = []
    for r in registros:
        esp = r["codigo"][1:]
        filas.append({"codigo": r["codigo"], "concepto_general_cod": r["general"],
                      "concepto_general": GENERALES[r["general"]], "especifico_cod": esp,
                      "concepto_especifico": nombres.get(esp, ""),
                      "texto": re.sub(r"\s+", " ", " ".join(r["texto"])).strip()})
    if not filas:
        raise ValueError("No se encontraron códigos de glosa en el PDF.")
    return pd.DataFrame(filas).drop_duplicates("codigo").reset_index(drop=True)


# ---------------------------------------------------------------- ejecución
def main():
    # La extracción alternativa del PDF conserva su propia evidencia.
    salida = SALIDA / "pdf"
    (salida / "raw").mkdir(parents=True, exist_ok=True)
    log = {"url": URL, "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "user_agent": AGENTE, "robots_txt_permite": permitido_por_robots(URL)}
    if log["robots_txt_permite"] is False:
        sys.exit("robots.txt no permite la descarga; no se continúa.")
    r = descargar()
    log.update(estado_http=r.status_code, bytes=len(r.content), sha256=hashlib.sha256(r.content).hexdigest(),
               content_type=r.headers.get("Content-Type"))
    (salida / "raw" / "anexo6_res3047_2008.pdf").write_bytes(r.content)

    cat = parsear_manual(texto_del_pdf(r.content))
    cat.to_csv(salida / "catalogo_glosas_minsalud.csv", index=False, encoding="utf-8-sig")
    log.update(filas_extraidas=len(cat), por_concepto_general=cat["concepto_general"].value_counts().to_dict())
    (salida / "log_scraping.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(log, ensure_ascii=False, indent=2))
    esperado = {"Facturación": 29, "Tarifas": 11, "Soportes": 21, "Autorización": 9, "Cobertura": 9, "Pertinencia": 10}
    obtenido = cat["concepto_general"].value_counts().to_dict()
    dif = {k: (obtenido.get(k, 0), v) for k, v in esperado.items() if obtenido.get(k, 0) != v}
    print(f"\nCódigos extraídos: {len(cat)} (el manual lista 89 en los conceptos 1 a 6).")
    if dif:
        print("AVISO: difieren (obtenido, esperado):", dif, "→ revisa el formato del PDF en parsear_manual().")
    return cat


if __name__ == "__main__":
    main()
