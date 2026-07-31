#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

rg -q 'static/images/data-generation.webp' index.html
rg -q 'width="700" height="238"' index.html
rg -q 'data-step="segment"' index.html
rg -q 'data-step="describe"' index.html
rg -q 'data-step="assign"' index.html
test -f static/images/data-generation.webp

if rg -q 'metric-band|metric-inner|class="metric"' index.html static/css/site.css; then
  echo "context-free metric strip is still present" >&2
  exit 1
fi

if rg -q 'dataset-facts' index.html static/css/site.css; then
  echo "legacy dataset fact grid is still present" >&2
  exit 1
fi
