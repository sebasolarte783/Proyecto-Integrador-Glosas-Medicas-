import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from scraping_catalogo import parsear_manual
from mapear_motivos import mapear_motivos

MUESTRA = """ANEXO TÉCNICO No. 6 MANUAL ÚNICO DE GLOSAS, DEVOLUCIONES Y RESPUESTAS
Tabla No. 2. Codificación Concepto Específico
Código Concepto Específico
01 Estancia
02 Consultas, interconsultas y visitas médicas
06 Materiales
07 Medicamentos
08 Ayudas diagnósticas
45 Servicio no pactado
Continuación ANEXO TÉCNICO No. 6 MANUAL ÚNICO DE GLOSAS, DEVOLUCIONES Y
RESPUESTAS - Resolución 3047 de 2008 modificada por la Resolución 416 de 2009
RESPUESTAS DE GLOSA O DEVOLUCION
96 Glosa o devolución injustificada
Manual de Uso
1. Facturación
Se presentan glosas por facturación cuando hay diferencias al comparar el tipo y volumen.
101 Estancia Aplica cuando:
1. El cargo por estancia, en cualquier tipo de internación, presenta diferencia con las cantidades que fueron facturadas.
107 Medicamentos Aplica cuando:
1. Los cargos por medicamentos que vienen relacionados en el detalle de cargos y/o los soportes, presentan diferencias con las cantidades que fueron facturadas.
2. Tarifas
Se consideran glosas por tarifas, todas aquellas que se generan por existir diferencias.
207 Medicamentos Aplica cuando los cargos por medicamentos presentan diferencias con los valores que fueron pactados.
3. Soportes
307 Medicamentos Existe ausencia total o parcial, enmendaduras o ilegibilidad en la hoja de administración de medicamentos.
4. Autorizaciones
401 Estancia Aplica cuando:
1. El número de horas en observación, o días en habitación, presenta diferencia con los días autorizados.
5. Cobertura
545 Servicio no pactado Aplica cuando en la factura se cobra un servicio que no se encuentra establecido entre las partes.
"""

def test_parser():
    df = parsear_manual(MUESTRA)
    assert list(df["codigo"]) == ["101", "107", "207", "307", "401", "545"]
    assert df.set_index("codigo").loc["307", "concepto_general"] == "Soportes"
    assert df.set_index("codigo").loc["545", "concepto_especifico"] == "Servicio no pactado"

def test_mapeo():
    df = parsear_manual(MUESTRA)
    r = mapear_motivos([
        "LOS CARGOS POR MEDICAMENTOS QUE VIENEN RELACIONADOS EN EL DETALLE DE CARGOS PRESENTAN DIFERENCIAS CON LOS VALORES PACTADOS",
        "EXISTE AUSENCIA TOTAL, PARCIAL O ENMENDADURAS EN LA HOJA DE ADMINISTRACION DE MEDICAMENTOS",
        "EL NÚMERO DE DIAS EN OBSERVACIÓN O HABITACION PRESENTA DIFERENCIA CON LOS DIAS AUTORIZADOS",
        "COBERTURA - SERVICIO NO PACTADO"], df).set_index("motivo")
    g = list(r["concepto_general"])
    assert g == ["Tarifas", "Soportes", "Autorización", "Cobertura"], g

if __name__ == "__main__":
    test_parser(); test_mapeo(); print("tests OK")
