#!/bin/sh
set -eu
python3 -m pip install "${1:-.}"
ctxora doctor --workspace "${CTXORA_WORKSPACE:-.}"
