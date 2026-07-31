#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

rg -q 'static/images/data-generation.webp' index.html
rg -Fq 'static/css/site.css?v=20260731-aligned' index.html
rg -q 'width="700" height="238"' index.html
rg -U -q '\.dataset-figure img \{[^}]*height: auto;' static/css/site.css
rg -q 'data-step="segment"' index.html
rg -q 'data-step="describe"' index.html
rg -q 'data-step="assign"' index.html
test -f static/images/data-generation.webp
rg -q 'From visible surfaces to a complete 3D field' index.html
rg -q 'static/images/visibility-extraction.webp' index.html
rg -q 'static/images/interior-filling.webp' index.html
rg -q 'class="volumetric-stages"' index.html
test -f static/images/visibility-extraction.webp
test -f static/images/interior-filling.webp
rg -Fq 'grid-template-columns: repeat(2, minmax(0, 1fr));' static/css/site.css
rg -Fq 'aspect-ratio: 16 / 9;' static/css/site.css
rg -q 'accumulated transmittance' index.html
rg -q 'six-direction boundary checks' index.html
rg -q 'even-odd rule' index.html
rg -q 'nearest-neighbor' index.html

if rg -q 'Preserve structure, including what the camera cannot see|class="check-list"' index.html; then
  echo "legacy volumetric copy or checklist is still present" >&2
  exit 1
fi

if rg -q 'metric-band|metric-inner|class="metric"' index.html static/css/site.css; then
  echo "context-free metric strip is still present" >&2
  exit 1
fi

if rg -q 'dataset-facts' index.html static/css/site.css; then
  echo "legacy dataset fact grid is still present" >&2
  exit 1
fi
