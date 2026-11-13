"""Extrae las filas del manual histórico publicadas en Mis Cuentas Médicas."""
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from lxml import html
import pandas as pd

from scraping_catalogo import GENERALES, SALIDA, permitido_por_robots

URL = "https://www.miscuentasmedicas.com/Resolucion-3047-de-2008-anexo-tecnico-6-manual-de-glosas-devoluciones-y-respuestas"


def extraer(contenido):
    pagina = html.fromstring(contenido.decode("utf-8-sig"))
    filas = []
    for tr in pagina.xpath("//table//tr"):
        celdas = [" ".join(td.text_content().split()) for td in tr.xpath("./td|./th")]
        if len(celdas) != 3 or not re.fullmatch(r"[1-6]\d{2}", celdas[0]):
            continue
        codigo, nombre, descripcion = celdas
        grupo = int(codigo[0])
        filas.append(dict(codigo=codigo, concepto_general_cod=grupo, concepto_general=GENERALES[grupo],
                          especifico_cod=codigo[1:], concepto_especifico=nombre, texto=descripcion))
    df = pd.DataFrame(filas)
    if df.empty or df.codigo.duplicated().any() or set(df.concepto_general_cod) != set(range(1, 7)):
        raise ValueError("La estructura del catálogo cambió. Revisa las tablas de la fuente.")
    return df


def main():
    permitido = permitido_por_robots(URL)
    if permitido is False:
        raise RuntimeError("Descarga excluida por robots.txt")
    with urlopen(Request(URL, headers={"User-Agent": "ProyectoIntegradorGlosas/1.0"}), timeout=40) as respuesta:
        contenido = respuesta.read()
        log = dict(url=respuesta.geturl(), estado_http=respuesta.status, content_type=respuesta.headers.get_content_type())
    catalogo = extraer(contenido)
    log.update(fuente="Mis Cuentas Médicas · transcripción del Anexo Técnico 6", fecha_utc=datetime.now(timezone.utc).isoformat(),
               bytes=len(contenido), sha256=hashlib.sha256(contenido).hexdigest(), robots_txt_permite=permitido,
               filas_extraidas=len(catalogo), por_concepto_general=catalogo.concepto_general.value_counts().to_dict())
    SALIDA.mkdir(parents=True, exist_ok=True)
    catalogo.to_csv(SALIDA / "catalogo_glosas_minsalud.csv", index=False, encoding="utf-8-sig")
    (SALIDA / "log_scraping.json").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False, indent=2))
    return catalogo


if __name__ == "__main__":
    main()
