"""Prioridad de revisión de glosas y clasificación opcional con un pipeline entrenado."""
import math
import os
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Glosas médicas")
ruta = Path(os.environ.get("RUTA_MODELO", "/opt/glosas/model.joblib"))
modelo = joblib.load(ruta) if ruta.is_file() else None
umbral = float(os.environ.get("UMBRAL", "0.5"))
if not 0 <= umbral <= 1:
    raise ValueError("UMBRAL debe estar entre 0 y 1.")


def indice_no_recuperada(clases):
    etiquetas = list(clases)
    if len(etiquetas) == 2:
        if set(etiquetas) == {"Recuperada", "No recuperada"}:
            return etiquetas.index("No recuperada")
        if set(etiquetas) == {0, 1}:
            return etiquetas.index(1)
    raise ValueError("El modelo requiere clases Recuperada/No recuperada o 0/1 (1 = no recuperada).")


if modelo is not None:
    indice_no_recuperada(modelo.classes_)


class Objecion(BaseModel):
    motivo: str = Field(min_length=1)
    especialidad: str = Field(min_length=1)
    entidad: str = Field(min_length=1)
    valor_objetado: float = Field(ge=0, allow_inf_nan=False)
    regimen: str = Field(min_length=1)
    centro_costo: str = Field(min_length=1)


@app.get("/health")
def health():
    return {"status": "ok", "modelo": "pipeline" if modelo is not None else "baseline_regla_valor"}


@app.post("/predict")
def predict(o: Objecion):
    if modelo is None:
        return {"modelo": "baseline_regla_valor", "prediccion": None, "probabilidad_no_recuperada": None,
                "prioridad": "alta" if o.valor_objetado >= 100_000 else "normal"}
    fila = pd.DataFrame([{"Concepto de Objecion": o.motivo, "Especialidad": o.especialidad,
                          "Entidad": o.entidad, "Valor Objeción": o.valor_objetado,
                          "Regimen": o.regimen, "Centro de Costo": o.centro_costo}])
    prob = float(modelo.predict_proba(fila)[0, indice_no_recuperada(modelo.classes_)])
    if not math.isfinite(prob) or not 0 <= prob <= 1:
        raise ValueError("Probabilidad del modelo fuera de rango.")
    return {"modelo": "pipeline", "probabilidad_no_recuperada": round(prob, 4),
            "prediccion": "No recuperada" if prob >= umbral else "Recuperada",
            "prioridad": "alta" if prob >= 0.05 else "normal"}
