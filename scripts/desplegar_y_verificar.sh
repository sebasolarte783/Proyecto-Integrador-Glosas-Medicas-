#!/usr/bin/env bash
# AWS CloudShell. Usa la VPC predeterminada y dos de sus subredes predeterminadas.
set -euo pipefail
export AWS_PAGER=""
cd "$(dirname "$0")/.."
stack=glosas-api
vpc=$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
if [[ "$vpc" == None || -z "$vpc" ]]; then
    echo "Esta región no tiene VPC predeterminada. Usa el despliegue con parámetros de docs/despliegue_aws.md." >&2
    exit 1
fi
subredes=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc" Name=default-for-az,Values=true Name=map-public-ip-on-launch,Values=true --query 'Subnets[].[AvailabilityZone,SubnetId]' --output text |
    awk '!vistas[$1]++ && n<2 {ids = ids (n ? "," : "") $2; n++} END {if (n==2) print ids}')
if [[ -z "$subredes" ]]; then
    echo "Se necesitan dos subredes públicas en zonas distintas. Revisa docs/despliegue_aws.md." >&2
    exit 1
fi
aws cloudformation validate-template --template-body file://infra/template.yaml >/dev/null
aws cloudformation deploy --stack-name "$stack" --template-file infra/template.yaml --capabilities CAPABILITY_IAM \
    --parameter-overrides "VpcId=$vpc" "SubnetIds=$subredes" InstanceType=t3.micro --no-fail-on-empty-changeset
grupo=$(aws cloudformation describe-stack-resource --stack-name "$stack" --logical-resource-id GrupoDestino --query StackResourceDetail.PhysicalResourceId --output text)
for intento in {1..60}; do
    sanos=$(aws elbv2 describe-target-health --target-group-arn "$grupo" --query "length(TargetHealthDescriptions[?TargetHealth.State=='healthy'])" --output text)
    if (( sanos >= 2 )); then
        carpeta="evidencia/aws/$(date -u +%Y%m%dT%H%M%SZ)"
        bash scripts/evidencia_aws.sh "$stack" "$carpeta"
        zip -j "$HOME/evidencia-glosas-$(basename "$carpeta").zip" "$carpeta"/*.json
        exit 0
    fi
    echo "Destinos sanos: $sanos. Esperando dos."
    sleep 15
done
echo "Si terminas la práctica, elimina el stack glosas-api para detener sus cargos." >&2
echo "El stack existe, pero no se verificaron dos destinos sanos. Revisa el grupo de destino y los eventos del stack." >&2
exit 1
