import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from app import app as servicio


class PruebasAPI(unittest.TestCase):
    def setUp(self):
        self.cliente = TestClient(servicio.app)
        self.datos = dict(motivo="Prueba", especialidad="General", entidad="Ejemplo",
                          valor_objetado=100000, regimen="CON", centro_costo="Prueba")

    def test_prioridad_sin_clasificador(self):
        with patch.object(servicio, "modelo", None):
            self.assertEqual(self.cliente.get("/health").json()["modelo"], "baseline_regla_valor")
            for valor, prioridad in [(0, "normal"), (99999, "normal"), (100000, "alta")]:
                respuesta = self.cliente.post("/predict", json=dict(self.datos, valor_objetado=valor))
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.json()["prioridad"], prioridad)
                self.assertIsNone(respuesta.json()["prediccion"])
                self.assertIsNone(respuesta.json()["probabilidad_no_recuperada"])

    def test_importe_invalido(self):
        for valor in [-1, "NaN", "Infinity"]:
            self.assertEqual(self.cliente.post("/predict", json=dict(self.datos, valor_objetado=valor)).status_code, 422)

    def test_orden_de_clases(self):
        for clases, probs in [(["No recuperada", "Recuperada"], [0.8, 0.2]), ([0, 1], [0.2, 0.8])]:
            with patch.object(servicio, "modelo") as modelo:
                modelo.classes_ = clases
                modelo.predict_proba.return_value = np.array([probs])
                r = self.cliente.post("/predict", json=self.datos).json()
                self.assertEqual(r["prediccion"], "No recuperada")
                self.assertEqual(r["probabilidad_no_recuperada"], 0.8)
