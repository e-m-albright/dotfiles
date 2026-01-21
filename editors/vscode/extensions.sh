#!/bin/bash
# VS Code extension installer (uses shared extensions.sh)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$SCRIPT_DIR/../extensions.sh" code
