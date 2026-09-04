#!/bin/sh
set -eu
ctxora uninstall --workspace "${CTXORA_WORKSPACE:-.}" --profile "${CTXORA_PROFILE:-generic}" || true
python3 -m pip uninstall -y ctxora-engine
