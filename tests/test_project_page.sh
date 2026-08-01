#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

rg -q 'static/images/data-generation.webp' index.html
rg -Fq 'static/css/site.css?v=20260801-overview-align' index.html
rg -q 'Resolving visual ambiguity with language' index.html
rg -q 'class="intro-copy-grid"' index.html
rg -U -q '\.intro-copy-grid \{[^}]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\);[^}]*align-items: start;' static/css/site.css
rg -U -q '(?s)@media \(max-width: 900px\).*?\.intro-copy-grid \{[^}]*grid-template-columns: 1fr;' static/css/site.css

if rg -q 'Appearance alone does not determine physics|class="section-inner intro-grid"' index.html; then
  echo "legacy oversized overview heading or split layout is still present" >&2
  exit 1
fi
rg -q 'width="700" height="238"' index.html
rg -U -q '\.dataset-figure img \{[^}]*height: auto;' static/css/site.css
rg -q 'data-step="segment"' index.html
rg -q 'data-step="describe"' index.html
rg -q 'data-step="assign"' index.html
test -f static/images/data-generation.webp
rg -q 'Part-aware supervision for text-conditioned physics' index.html
rg -q '1,700 3D assets' index.html
rg -q 'eight text-and-property annotations' index.html
rg -q '15 upper-hemisphere views' index.html
rg -q 'five segmentation candidates' index.html
rg -q 'class="section-heading dataset-heading"' index.html
rg -U -q '\.dataset-layout \{[^}]*display: block;' static/css/site.css

if rg -q 'dataset-copy|dataset-visual' index.html static/css/site.css; then
  echo "legacy split dataset layout is still present" >&2
  exit 1
fi
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
rg -q 'On the real-world ABO-500 benchmark' index.html
rg -q 'Highlighted row marks the best result' index.html

if rg -q 'abo-callout' index.html static/css/site.css; then
  echo "disconnected benchmark callouts are still present" >&2
  exit 1
fi

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
