#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/workspace"
NESTED_DIR="/workspace/workspace"

if [ -f "${APP_DIR}/package.json" ]; then
  echo "Using existing Angular app in ${APP_DIR}"
elif [ -f "${NESTED_DIR}/package.json" ]; then
  APP_DIR="${NESTED_DIR}"
  echo "Using existing Angular app in ${APP_DIR}"
else
  echo "Initializing Angular app in ${APP_DIR}"
  npx -y @angular/cli@latest new frontend-angular --routing=false --style=css --skip-git --directory "."
fi

cd "${APP_DIR}"

npm install

exec npm run start -- --host 0.0.0.0 --port 4200
