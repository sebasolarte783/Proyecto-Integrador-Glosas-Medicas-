#!/usr/bin/env bash
# Ejecutar en AWS CloudShell después del despliegue, en la misma región.
set -euo pipefail
export AWS_PAGER=""
stack=${1:-glosas-api}
dir=${2:-"evidencia/aws/$(date -u +%Y%m%dT%H%M%SZ)"}
destino=$dir
mkdir -p "$(dirname "$destino")"
if [[ -e "$destino" ]]; then
    echo "Ya existe la carpeta de esta ejecución: $destino" >&2
    exit 1
fi
dir=$(mktemp -d "$(dirname "$destino")/.ejecucion-XXXXXXXX")
trap 'rm -rf -- "$dir"' EXIT
aws cloudformation describe-stacks --stack-name "$stack" --query 'Stacks[0].{Nombre:StackName,Estado:StackStatus,Creado:CreationTime,Salidas:Outputs}' --output json > "$dir/stack.json"
url=$(aws cloudformation describe-stacks --stack-name "$stack" --query "Stacks[0].Outputs[?OutputKey=='UrlApi'].OutputValue | [0]" --output text)
recurso() {
    aws cloudformation describe-stack-resource --stack-name "$stack" --logical-resource-id "$1" --query StackResourceDetail.PhysicalResourceId --output text
}
grupo=$(recurso GrupoDestino)
asg=$(recurso Asg)
aws elbv2 describe-target-health --target-group-arn "$grupo" --output json > "$dir/targets.json"
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$asg" --query 'AutoScalingGroups[0].{Deseada:DesiredCapacity,Min:MinSize,Max:MaxSize,Instancias:Instances[].LifecycleState}' --output json > "$dir/auto_scaling.json"
curl --fail --silent --show-error --max-time 30 "$url/health" > "$dir/health.json"
curl --fail --silent --show-error --max-time 30 -H 'Content-Type: application/json' -d '{"motivo":"Ejemplo académico","entidad":"Ejemplo","especialidad":"General","valor_objetado":250000,"regimen":"CON","centro_costo":"Prueba"}' "$url/predict" > "$dir/predict.json"
python3 - "$dir" <<'PYTHON'
import json
import sys
from pathlib import Path

base = Path(sys.argv[1])
def leer(nombre):
    return json.loads((base / (nombre + ".json")).read_text())

estado = leer("stack")["Estado"]
destinos = leer("targets")["TargetHealthDescriptions"]
grupo = leer("auto_scaling")
salud = leer("health")
resultado = leer("predict")
if estado not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
    sys.exit(f"Stack en estado {estado}")
if sum(d["TargetHealth"]["State"] == "healthy" for d in destinos) < 2:
    sys.exit("Se requieren al menos dos destinos sanos.")
if grupo["Deseada"] < 2 or grupo["Instancias"].count("InService") < 2:
    sys.exit("El Auto Scaling Group aún no tiene dos instancias en servicio.")
if salud.get("status") != "ok" or salud.get("modelo") != resultado.get("modelo"):
    sys.exit("Las respuestas de salud y predicción son inconsistentes.")
if resultado.get("prioridad") not in {"normal", "alta"}:
    sys.exit("Respuesta de prioridad inesperada.")
if resultado["modelo"] == "baseline_regla_valor" and resultado["prioridad"] != "alta":
    sys.exit("La regla no asignó prioridad alta al caso de prueba.")
PYTHON
mv -T -- "$dir" "$destino"
echo "Evidencia verificada en $destino"
