#!/bin/sh
D=/usr/local/lib/node_modules/n8n/node_modules/.pnpm
echo "=== dirs matching GoogleSheetsTrigger ==="
find $D -maxdepth 8 -type d -name 'GoogleSheetsTrigger' 2>/dev/null
echo "=== .js files ==="
find $D -path '*GoogleSheetsTrigger*' -name '*.js' 2>/dev/null | head -20