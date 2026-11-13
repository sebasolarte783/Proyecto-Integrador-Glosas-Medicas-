# Auditoría con el reporte real · 13 de noviembre de 2026

| Criterio | Verificación realizada |
|---|---|
| Limpieza | Notebook 01 ejecutado sobre el CSV de esta versión: 370.332 filas, 40 columnas. Se separaron 53.046 pendientes y 684 anuladas. Los 316.602 confirmados tuvieron resultado y fecha de objeción válidos. |
| EDA | Notebook 02 ejecutado de principio a fin. Las siete filas de la tabla mensual suman 316.602. Marzo concentró el 45,7 % del valor cedido. Julio es parcial y llega al día 17. |
| Extracción web | Notebook 00 ejecutado con el catálogo de 89 códigos y los datos reales. Se cruzaron 174 motivos. El indicador de revisión señaló 66 motivos, equivalentes al 7,8 % de los ítems. La validación independiente por especialistas queda abierta. |
| Clustering | Sección 12 del notebook 02 ejecutada sobre los confirmados. K = 5, silueta de 0,490 en la muestra de evaluación. El segmento de alto valor y objeción total reunió 60.188 ítems (19,01 %) y el 99,06 % del dinero cedido. ARI de 0,999, redondeado, en el ajuste con media muestra. |
| Arquitectura cloud | Diagrama, plantilla validada con cfn-lint para us-east-1 y pruebas locales de la API. |
| Ejecución cloud | Se verificó localmente el recolector con respuestas simuladas. Para acreditar el despliegue se necesita el ZIP generado en la cuenta AWS. |

## Correcciones que afectan la interpretación

Se retiraron de las vistas de limpieza filas originales, identificadores y ejemplos de observaciones en texto libre. El análisis conserva estadísticas agregadas. Los CSV privados de trabajo pueden contener información identificable aun después de retirar columnas personales o seudonimizar la factura.

La API en modo de regla devuelve prioridad alta a partir de 100.000 COP. La predicción y la probabilidad quedan vacías hasta cargar un clasificador. El 99,1 % representa la proporción histórica del dinero cedido concentrada en un segmento. Ordenar los ítems por valor objetado también concentró el 99,3 % de la pérdida en el 19 % de mayor valor. Ninguno de estos porcentajes mide la exactitud predictiva.

## Evidencia pendiente para cerrar la entrega

Desde AWS CloudShell, seguir los pasos de despliegue en despliegue_aws.md. Descargar el ZIP generado en la cuenta y entregar sus resultados junto con este repositorio. Las salidas de los tres notebooks corresponden a la ejecución con los datos reales. La copia privada conserva el CSV fuente; la copia para el repositorio excluye los archivos privados y conserva el catálogo público.
