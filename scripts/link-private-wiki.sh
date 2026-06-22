#!/usr/bin/env bash
set -euo pipefail

# Link local private wiki clone into this repo as ./wiki.
# Default target: ../ccw-private-wiki/wiki (sibling to this repo).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$REPO_ROOT/../ccw-private-wiki/wiki}"
LINK_PATH="$REPO_ROOT/wiki"

if [[ ! -d "$TARGET" ]]; then
  echo "Private wiki target not found: $TARGET" >&2
  echo "Usage: scripts/link-private-wiki.sh [ABSOLUTE_OR_RELATIVE_WIKI_PATH]" >&2
  exit 1
fi

if [[ -L "$LINK_PATH" || -e "$LINK_PATH" ]]; then
  rm -rf "$LINK_PATH"
fi

ln -s "$TARGET" "$LINK_PATH"

echo "Linked $LINK_PATH -> $TARGET"
