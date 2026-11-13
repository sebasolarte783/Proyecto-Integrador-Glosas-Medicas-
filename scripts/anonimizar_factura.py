"""Seudonimiza solo Factura. El CSV resultante sigue siendo privado."""
import argparse
import hashlib
import hmac
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd


def exportar(entrada, salida, clave):
    if entrada.resolve() == salida.resolve():
        raise ValueError("Elige un archivo de salida distinto del original.")
    temporal = None
    try:
        with NamedTemporaryFile(dir=salida.parent, delete=False, mode="w", newline="", encoding="utf-8-sig") as archivo:
            temporal = Path(archivo.name)
            # Mantener ceros iniciales, literales NA y representación del resto de columnas.
            for i, bloque in enumerate(pd.read_csv(entrada, dtype=str, keep_default_na=False, chunksize=100_000)):
                bloque["Factura"] = bloque["Factura"].map(
                    lambda v: "F" + hmac.new(clave, v.encode(), hashlib.sha256).hexdigest() if v else "")
                bloque.to_csv(archivo, index=False, header=i == 0)
        temporal.replace(salida)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrada", type=Path)
    parser.add_argument("salida", type=Path)
    args = parser.parse_args()
    clave = os.environ.get("SALT_GLOSAS")
    if not clave:
        parser.error("Define SALT_GLOSAS en el entorno.")
    exportar(args.entrada, args.salida, clave.encode())
