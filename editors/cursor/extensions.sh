#!/bin/bash
# Cursor extension installer (uses shared extensions.sh)
set -eo pipefail
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$SCRIPT_DIR/../extensions.sh" cursor
