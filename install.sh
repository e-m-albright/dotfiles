#!/usr/bin/env bash
set -euo pipefail

# Preserve the documented bootstrap path and arguments.
# shellcheck source=scripts/install.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/install.sh" "$@"
