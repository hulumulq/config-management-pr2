#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONPATH="$APP_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
    exec "${PYTHON:-python3}" "$APP_ROOT/src/main.py" "$@"
