#!/usr/bin/env bash
# Render + compile a tailored CV (and optionally the cover letter) in one shot.
#
# Usage:
#   tools/compile.sh <slug>                         # shorthand for job-ads/<slug>/spec.yml
#   tools/compile.sh job-ads/<slug>/spec.yml        # CV; cover letter too if spec has cover_letter:
#   tools/compile.sh job-ads/<slug>/spec.yml --cv   # CV only
#   tools/compile.sh job-ads/<slug>/spec.yml --cover # cover letter only
#   tools/compile.sh outputs/<slug>/cv.tex          # compile-only
#   tools/compile.sh master                         # render + compile cv/master.yml (whole bank)
#
# Outputs land in outputs/<slug>/{cv,cover}.{tex,pdf}.
# Page limit comes from the spec's page_mode: one (default), two, or master (no limit).
#
# Requires: PyYAML + pypdf (.venv/ if present, else python3), `tectonic`, and
# `pdftotext` (poppler) for the text-layer check.

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v tectonic >/dev/null 2>&1; then
  echo "error: tectonic not found on PATH" >&2
  echo "       install with: brew install tectonic" >&2
  exit 127
fi

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <slug | job-ads/<slug>/spec.yml | outputs/<slug>/*.tex | master> [--cv|--cover]" >&2
  exit 64
fi

target="$1"
mode="${2:-both}"   # both | cv-only | cover-only

PY=python3
[[ -x .venv/bin/python ]] && PY=.venv/bin/python

# Page limit for the CV being compiled; set from the spec before compile_tex runs.
max_pages=1

page_limit() {
  "$PY" -c "import sys,yaml; m=(yaml.safe_load(open(sys.argv[1])) or {}).get('page_mode','one'); print({'one':1,'two':2,'master':0}.get(m,1))" "$1"
}

# ATS parsers read the PDF text layer, so check it the way they see it.
check_text_layer() {
  local pdf="$1"
  if ! command -v pdftotext >/dev/null 2>&1; then
    echo "  note: pdftotext not found (brew install poppler); text-layer check skipped" >&2
    return 0
  fi
  local txt
  txt="$(pdftotext -enc UTF-8 "$pdf" - 2>/dev/null)"
  local problems=()
  printf '%s' "$txt" | grep -qi "gia bao bui" || problems+=("name not found in extracted text")
  if [[ "$(basename "$pdf")" == cv.pdf ]]; then
    [[ "$txt" == *"Experience"* || "$txt" == *"EXPERIENCE"* ]] || problems+=("Experience heading not extractable")
  fi
  if printf '%s' "$txt" | LC_ALL=C grep -q $'\xef\xac[\x80-\x86]'; then problems+=("ligature glyphs (fi/fl) in text layer"); fi
  if printf '%s' "$txt" | grep -q '(cid:'; then problems+=("unmapped glyphs (cid:) in text layer"); fi
  if (( ${#problems[@]} )); then
    printf '  error: text layer check failed for %s:\n' "$(basename "$pdf")" >&2
    printf '    - %s\n' "${problems[@]}" >&2
    return 1
  fi
  echo "  text layer ok ($(printf '%s' "$txt" | wc -w | tr -d ' ') words extractable)"
}

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
    pages=$("$PY" -c "import sys; from pypdf import PdfReader; print(len(PdfReader(sys.argv[1]).pages))" "$pdf" 2>/dev/null || echo "?")
    local size
    size=$(du -h "$pdf" | cut -f1)
    echo "wrote $pdf (${pages} pages, ${size})"
    if [[ "$pages" != "?" && "$max_pages" -gt 0 && "$pages" -gt "$max_pages" ]]; then
      echo "  warn: $(basename "$pdf") is ${pages} pages; target is ${max_pages}." >&2
      echo "  edit the spec in job-ads/<slug>/ to trim, then re-run." >&2
    fi
    # A two-page CV should fill at least half of page two (tailor-cv page_mode test).
    if [[ "$max_pages" == 2 && "$pages" == 2 ]] && command -v pdftotext >/dev/null 2>&1; then
      local p1 p2
      p1=$(pdftotext -f 1 -l 1 "$pdf" - | grep -c .)
      p2=$(pdftotext -f 2 -l 2 "$pdf" - | grep -c .)
      if (( p2 * 2 < p1 )); then
        echo "  warn: page 2 is under half full (${p2} vs ${p1} lines); fill it or switch to page_mode: one" >&2
      fi
    fi
    check_text_layer "$pdf"
  fi
}

"$PY" tools/lint_bank.py >/dev/null || { "$PY" tools/lint_bank.py | grep '^error' >&2; exit 65; }

if [[ "$target" == "master" ]]; then
  max_pages=0
  "$PY" tools/render_tailored.py cv/master.yml -o outputs/_master/cv.tex
  compile_tex "outputs/_master/cv.tex"
  exit 0
fi

if [[ "$target" == *.tex ]]; then
  compile_tex "$target"
  exit 0
fi

# Shorthand: bare slug -> expand to job-ads/<slug>/spec.yml
if [[ "$target" != *.yml && -d "job-ads/$target" ]]; then
  target="job-ads/$target/spec.yml"
fi

if [[ "$target" != *.yml ]]; then
  echo "error: target must be a slug, .yml spec, .tex file, or 'master'" >&2
  exit 64
fi

if [[ ! -f "$target" ]]; then
  echo "error: spec not found: $target" >&2
  exit 66
fi

slug="$(basename "$(dirname "$target")")"

case "$mode" in
  --cv)    do_cv=1; do_cover=0 ;;
  --cover) do_cv=0; do_cover=1 ;;
  both)    do_cv=1; do_cover=1 ;;
  *)       echo "error: unknown mode '$mode'" >&2; exit 64 ;;
esac

if [[ "$do_cv" == 1 ]]; then
  max_pages="$(page_limit "$target")"
  "$PY" tools/render_tailored.py "$target"
  compile_tex "outputs/${slug}/cv.tex"
fi

if [[ "$do_cover" == 1 ]]; then
  # Capture output so warnings (e.g. over 350 words) always show, without a temp file.
  rc=0
  cover_out="$("$PY" tools/render_cover_letter.py "$target" 2>&1)" || rc=$?
  if [[ "$rc" == 0 ]]; then
    printf '%s\n' "$cover_out"
    max_pages=1
    compile_tex "outputs/${slug}/cover.tex"
  elif [[ "$rc" == 2 ]]; then
    # No cover_letter block: an error only when the letter was asked for explicitly.
    [[ "$mode" == "--cover" ]] && { printf '%s\n' "$cover_out" >&2; exit 2; }
  else
    printf '%s\n' "$cover_out" >&2
    exit "$rc"
  fi
fi
