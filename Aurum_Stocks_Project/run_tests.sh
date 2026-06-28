#!/usr/bin/env bash
# Run the full Aurum Stocks test suite from the src layout.
set -e
export PYTHONPATH="$(cd "$(dirname "$0")/src" && pwd)"
for f in $(find "$(dirname "$0")/tests" -name 'test_*.py' | sort); do
  echo "=== $f ==="; python "$f"
done
