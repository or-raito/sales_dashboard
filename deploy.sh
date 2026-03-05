#!/bin/bash
# Raito Dashboard — Build & Deploy
# Run this after updating data files to regenerate and deploy the dashboard.

set -e

echo "🔄 Regenerating dashboard..."
python3 process_data.py

echo "📋 Copying to docs/ for GitHub Pages..."
cp dashboard.html docs/index.html

echo "📦 Committing and pushing..."
git add docs/index.html supply_chain_summary.xlsx
git commit -m "Update dashboard $(date '+%Y-%m-%d %H:%M')"
git push

echo "✅ Done! Dashboard will be live at:"
echo "   https://or-raito.github.io/raito-dashboard/"
