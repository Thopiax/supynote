#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source .env

rm -rf dist/
uv build
uv publish
