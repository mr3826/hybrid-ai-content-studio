#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Running Content Studio Test Suite                     "
echo "=========================================================="

echo "[1/2] Running Backend & Worker unit tests with pytest..."
uv run pytest apps/api/tests worker/tests -v

echo "[2/2] Running Frontend build & TypeScript validation..."
npm --prefix apps/web run build

echo "=========================================================="
echo " All local tests and builds passed successfully!         "
echo "=========================================================="
