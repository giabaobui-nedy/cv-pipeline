#!/usr/bin/env bash
# Render + compile a tailored CV (and optionally the cover letter) in one shot.
#
# Usage:
#   tools/compile.sh job-ads/<company>.yml         # CV; cover letter too if spec has cover_letter:
#   tools/compile.sh job-ads/<company>.yml --cv    # CV only
#   tools/compile.sh job-ads/<company>.yml --cover # cover letter only
#   tools/compile.sh outputs/<company>.tex         # compile-only
#   tools/compile.sh master                        # compile cv/main.tex
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
  echo "usage: $0 <job-ads/*.yml | outputs/*.tex | master> [--cv|--cover]" >&2
  exit 64
fi

target="$1"
mode="${2:-both}"   # both | cv-only | cover-only

compile_tex() {
  local tex="$1"
  local outdir
  outdir="$(dirname "$tex")"
  echo "compiling $tex -> $outdir/"
  tectonic -X compile --keep-logs --synctex --outdir "$outdir" "$tex"
  local pdf="${tex%.tex}.pdf"
  local log="${tex%.tex}.log"
  if [[ -f "$pdf" ]]; then
    local pages
    pages=$(grep -oE 'Output written on [^ ]+ \([0-9]+ pages?' "$log" 2>/dev/null \
      | grep -oE '\([0-9]+' | grep -oE '[0-9]+' || echo "?")
    local size
    size=$(du -h "$pdf" | cut -f1)
    echo "wrote $pdf (${pages} pages, ${size})"
    if [[ "$pages" != "?" && "$pages" -gt 1 \
          && "$tex" != *main* && "$tex" != *master* ]]; then
      echo "  warning: $(basename "$pdf") is ${pages} pages — target is 1 page." >&2
      echo "  edit the spec in job-ads/ to trim, then re-run." >&2
    fi
  fi
}

if [[ "$target" == "master" ]]; then
  cp cv/main.tex outputs/main.tex
  compile_tex "outputs/main.tex"
  exit 0
fi

if [[ "$target" == *.tex ]]; then
  compile_tex "$target"
  exit 0
fi

if [[ "$target" != *.yml ]]; then
  echo "error: target must be a .yml spec, .tex file, or 'master'" >&2
  exit 64
fi

base="$(basename "$target" .yml)"

case "$mode" in
  --cv)    do_cv=1; do_cover=0 ;;
  --cover) do_cv=0; do_cover=1 ;;
  both)    do_cv=1; do_cover=1 ;;
  *)       echo "error: unknown mode '$mode'" >&2; exit 64 ;;
esac

if [[ "$do_cv" == 1 ]]; then
  .venv/bin/python tools/render_tailored.py "$target"
  compile_tex "outputs/${base}.tex"
fi

if [[ "$do_cover" == 1 ]]; then
  if .venv/bin/python tools/render_cover_letter.py "$target" 2>/tmp/cover_render.err; then
    compile_tex "outputs/${base}.cover.tex"
  else
    rc=$?
    if [[ "$rc" == 2 ]]; then
      [[ "$mode" == "--cover" ]] && { cat /tmp/cover_render.err >&2; exit 2; }
      # Auto mode: silently skip if no cover_letter block
      :
    else
      cat /tmp/cover_render.err >&2
      exit "$rc"
    fi
  fi
fi
