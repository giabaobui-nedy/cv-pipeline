#!/usr/bin/env bash
# Render + compile a tailored CV in one shot.
#
# Usage:
#   tools/compile.sh job-ads/<company>.yml
#   tools/compile.sh outputs/<company>.tex     # compile only, skip render
#   tools/compile.sh master                    # compile cv/main.tex
#
# Requires: .venv/ with PyYAML, and `tectonic` on PATH.

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v tectonic >/dev/null 2>&1; then
  echo "error: tectonic not found on PATH" >&2
  echo "       install with: brew install tectonic" >&2
  exit 127
fi

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <job-ads/*.yml | outputs/*.tex | master>" >&2
  exit 64
fi

target="$1"

if [[ "$target" == "master" ]]; then
  tex="cv/main.tex"
  outdir="outputs"
  cp cv/main.tex outputs/main.tex
  tex="outputs/main.tex"
elif [[ "$target" == *.yml ]]; then
  .venv/bin/python tools/render_tailored.py "$target"
  base="$(basename "$target" .yml)"
  tex="outputs/${base}.tex"
  outdir="outputs"
elif [[ "$target" == *.tex ]]; then
  tex="$target"
  outdir="$(dirname "$tex")"
else
  echo "error: target must be a .yml spec, .tex file, or 'master'" >&2
  exit 64
fi

echo "compiling $tex -> $outdir/"
tectonic -X compile --keep-logs --synctex --outdir "$outdir" "$tex"

pdf="${tex%.tex}.pdf"
log="${tex%.tex}.log"

if [[ -f "$pdf" ]]; then
  pages=$(grep -oE 'Output written on [^ ]+ \([0-9]+ pages' "$log" 2>/dev/null | grep -oE '[0-9]+ pages' | grep -oE '[0-9]+' || echo "?")
  size=$(du -h "$pdf" | cut -f1)
  echo "wrote $pdf (${pages} pages, ${size})"
  if [[ "$pages" != "?" && "$pages" -gt 1 && "$target" != *main* && "$target" != "master" ]]; then
    echo "  warning: tailored CV is ${pages} pages — target is 1 page." >&2
    echo "  edit the spec in job-ads/ to drop bullets, then re-run." >&2
  fi
fi
