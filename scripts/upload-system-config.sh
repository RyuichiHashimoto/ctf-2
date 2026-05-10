#!/bin/bash
set -euo pipefail

ENDPOINT="http://localhost:8000/graph/upload"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path-to-json>" >&2
  exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
  echo "Error: file not found: $FILE" >&2
  exit 1
fi

case "$FILE" in
  *.json) ;;
  *)
    echo "Error: file must be a .json file: $FILE" >&2
    exit 1
    ;;
esac

RESPONSE=$(curl -sf -X POST "$ENDPOINT" -F "file=@$FILE")
STATUS=$?

if [ $STATUS -ne 0 ]; then
  echo "Error: upload failed (curl exit code: $STATUS)" >&2
  exit 1
fi

FILE_ID=$(echo "$RESPONSE" | grep -o '"file_id":"[^"]*"' | cut -d'"' -f4)

echo "Upload successful."
echo "  File : $FILE"
echo "  ID   : ${FILE_ID:-unknown}"
