#!/usr/bin/env bash
# Export tailored CV + cover letter PDFs with submission-ready filenames.
#
# Filename format:
#   (YYYY.MM.DD) Gia Bao Bui - <role> - <company>.pdf
#   (YYYY.MM.DD) Gia Bao Bui - Cover letter - <company>.pdf
#
# Usage:
#   tools/export.sh <slug>                       # writes to ~/Desktop/, today's date
#   tools/export.sh <slug> --date 2026-05-02     # override the date stamp
#   tools/export.sh <slug> --dest ~/Applications # override the destination dir
#   tools/export.sh <slug> --cv-only             # skip the cover letter
#
# Reads `company` and `role` from job-ads/<slug>/spec.yml. Errors out if the
# corresponding PDFs are missing — run `tools/compile.sh <slug>` first.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <slug> [--date YYYY-MM-DD] [--dest <dir>] [--cv-only]" >&2
  exit 64
fi

slug="$1"
shift

date_arg=""
dest="$HOME/Desktop"
cv_only=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)    date_arg="$2"; shift 2 ;;
    --dest)    dest="$2"; shift 2 ;;
    --cv-only) cv_only=1; shift ;;
    *)         echo "error: unknown arg: $1" >&2; exit 64 ;;
  esac
done

spec="job-ads/$slug/spec.yml"
cv_pdf="outputs/$slug/cv.pdf"
cover_pdf="outputs/$slug/cover.pdf"

[[ -f "$spec" ]]   || { echo "error: spec not found: $spec" >&2; exit 66; }
[[ -f "$cv_pdf" ]] || { echo "error: $cv_pdf not found — run tools/compile.sh $slug first" >&2; exit 66; }

# Date stamp
if [[ -z "$date_arg" ]]; then
  date_str="$(date +%Y.%m.%d)"
else
  date_str="${date_arg//-/.}"
fi

# Read company + role from the spec via the venv's PyYAML
read_yaml="$(.venv/bin/python -c "
import shlex, sys, yaml
spec = yaml.safe_load(open(sys.argv[1])) or {}
def clean(s):
    return (s or '').strip().replace('/', '-').replace('\"', \"'\")
print('COMPANY=' + shlex.quote(clean(spec.get('company'))))
print('ROLE='    + shlex.quote(clean(spec.get('role'))))
" "$spec")"
eval "$read_yaml"

if [[ -z "${COMPANY:-}" || -z "${ROLE:-}" ]]; then
  echo "error: spec is missing 'company' or 'role'" >&2
  exit 65
fi

_page_count() {
  local pdf="$1"
  if [[ -x .venv/bin/python ]]; then
    .venv/bin/python -c "import sys; from pypdf import PdfReader; print(len(PdfReader(sys.argv[1]).pages))" "$pdf" 2>/dev/null || echo "?"
  else
    echo "?"
  fi
}

_warn_if_multipage() {
  local pdf="$1" label="$2"
  local pages
  pages=$(_page_count "$pdf")
  if [[ "$pages" != "?" && "$pages" -gt 1 ]]; then
    echo "  warning: $label is ${pages} pages — target is 1 page." >&2
  fi
}

mkdir -p "$dest"

cv_out="${dest}/(${date_str}) Gia Bao Bui - ${ROLE} - ${COMPANY}.pdf"
cp "$cv_pdf" "$cv_out"
echo "wrote $cv_out"
_warn_if_multipage "$cv_out" "CV"

if [[ "$cv_only" == 0 && -f "$cover_pdf" ]]; then
  cover_out="${dest}/(${date_str}) Gia Bao Bui - Cover letter - ${COMPANY}.pdf"
  cp "$cover_pdf" "$cover_out"
  echo "wrote $cover_out"
  _warn_if_multipage "$cover_out" "cover letter"
elif [[ "$cv_only" == 0 ]]; then
  echo "note: $cover_pdf not found; skipping cover letter export"
fi
