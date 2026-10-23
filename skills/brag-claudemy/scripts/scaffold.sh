#!/bin/bash
# Create a video project from the templates.
#   scaffold.sh <project-dir> "<Name>" [concept|built]
# Copies BRIEF, DESIGN, STORYBOARD, SCRIPT, reference.json, audio-plan.json, page.html, and the founder's
# rulings (rulings.md plus rulings.json, the machine-checkable half) so every project carries all prior rulings.
set -euo pipefail
DIR="${1:?project dir}"; NAME="${2:?name}"; MODE="${3:-concept}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
case "$MODE" in concept) STATUS=CONCEPT;; built) STATUS=BUILT;; *) echo "mode must be concept or built" >&2; exit 2;; esac
mkdir -p "$DIR"/{assets,frames,renders}   # route R2 (generated shots) adds shots/ and motion/ when it starts
for f in BRIEF.md DESIGN.md STORYBOARD.md SCRIPT.md; do
  sed -e "s/{{NAME}}/$NAME/g" -e "s/{{STATUS}}/$STATUS/g" "$HERE/templates/$f" > "$DIR/$f"
done
sed -e "s/{{NAME}}/$NAME/g" "$HERE/templates/page.html" > "$DIR/index.html"
cp "$HERE/templates/reference.json" "$HERE/templates/audio-plan.json" "$DIR/"
cp "$HERE/references/rulings.md" "$DIR/rulings.md"
if [ "$STATUS" = CONCEPT ]; then
  cat > "$DIR/rulings.json" <<'J'
{
  "forbidden_words": [],
  "forbidden_patterns": ["\\$\\s?\\d", "\\b\\d+(\\.\\d+)?\\s?%", "\\b\\d+x\\b"],
  "note": "CONCEPT mode: no prices, no percentages, no multipliers on screen. Add forbidden words (client names, confidential material) here."
}
J
else
  cat > "$DIR/rulings.json" <<'J'
{
  "forbidden_words": [],
  "forbidden_patterns": [],
  "note": "Add forbidden words (client names, confidential material) here. Real copy only: every on-screen line traces to the product."
}
J
fi
echo "scaffolded $DIR ($STATUS). Next: fill BRIEF.md, then reference, design, storyboard, script."
