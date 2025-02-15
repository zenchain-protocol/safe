#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

WRENCH="\xf0\x9f\x94\xa7"
FOLDERS="\xf0\x9f\x97\x82"

# TODO install jq, xargs
if [[ -z "$ENVIRONMENT_NAME" ]]; then
    echo "Must provide ENVIRONMENT_NAME in environment" 1>&2
    exit 1
fi

if [[ -z "$AWS_PROFILE" ]]; then
    echo "Must provide AWS_PROFILE in environment" 1>&2
    exit 1
fi

if [[ -z "$AWS_REGION" ]]; then
    export AWS_REGION="us-east-1"
fi


SECRET_ID=$(aws secretsmanager list-secrets --query "SecretList[?Tags[?Key=='environment' && Value=='${ENVIRONMENT_NAME}']]" --filters Key=name,Values=SafeSharedSecrets --query "SecretList[0].ARN" --output text)

SECRETS=$(aws secretsmanager get-secret-value --secret-id ${SECRET_ID} | jq --raw-output '.SecretString')

# CGW
export NEXT_PUBLIC_GATEWAY_URL_PRODUCTION=https://safe.host.zenchain.io/cgw
# Production build
export NEXT_PUBLIC_IS_PRODUCTION=true
# Latest supported safe version, used for upgrade prompts
export NEXT_PUBLIC_SAFE_VERSION=1.4.1
export NEXT_PUBLIC_IS_OFFICIAL_HOST=false

# Secret environment variables
export NEXT_PUBLIC_INFURA_TOKEN=$(echo $SECRETS | jq -r .UI_INFURA_TOKEN | xargs)
export NEXT_PUBLIC_SAFE_APPS_INFURA_TOKEN=$(echo $SECRETS | jq -r .UI_SAFE_APPS_RPC_INFURA_TOKEN | xargs)

while read -r LB_ARN DNS_NAME; do
    IS_TX_MAINNET_LB=$(aws elbv2 describe-tags --resource-arns ${LB_ARN} --query "TagDescriptions[?Tags[?Key=='environment' && Value=='${ENVIRONMENT_NAME}']] && TagDescriptions[?Tags[?Key=='Name' && Value=='Safe Transaction Mainnet']]" --output text)
    IS_CGW_LB=$(aws elbv2 describe-tags --resource-arns ${LB_ARN} --query "TagDescriptions[?Tags[?Key=='environment' && Value=='${ENVIRONMENT_NAME}']] && TagDescriptions[?Tags[?Key=='Name' && Value=='Safe Client Gateway']]" --output text)
    echo

    if [[ -n $IS_CGW_LB ]]; then
        NEXT_PUBLIC_GATEWAY_URL_PRODUCTION="http://${DNS_NAME}"
        printf "Setting Client Gateway URI ${ORANGE}${NEXT_PUBLIC_GATEWAY_URL_PRODUCTION}${NC}"
    fi
done <<< "$(aws elbv2 describe-load-balancers --query "LoadBalancers[].{ID:LoadBalancerArn,NAME:DNSName}" --output text)"

printf "\n"

if [[ -z NEXT_PUBLIC_GATEWAY_URL_PRODUCTION ]]; then
    echo "NEXT_PUBLIC_GATEWAY_URL_PRODUCTION not found" 1>&2
    exit 1
fi

export PUBLIC_URL="/"

printf "${WRENCH} ${GREEN}Building UI${NC}\n"

printf "${WRENCH} ${GREEN}Creating an optimized production build...${NC}\n"
yarn --cwd safe-wallet-monorepo/apps/web install
yarn --cwd safe-wallet-monorepo/apps/web build

printf "${FOLDERS} ${GREEN}Moving UI build for docker${NC}\n"
BUILD_DIRECTORY=build_${ENVIRONMENT_NAME}
rm -rf ./builds/${BUILD_DIRECTORY}
mv ./safe-wallet-monorepo/apps/web/build ./builds/${BUILD_DIRECTORY}

printf "${FOLDERS} ${GREEN}Reverting configuration changes${NC}\n"
git submodule foreach git reset --hard
