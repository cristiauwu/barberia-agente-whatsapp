#!/bin/sh
B="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/n8n-nodes-base@file++++home+runner+_work+n8n+n8n+packages/nodes-base/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet/v2"
B="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/n8n-nodes-base@file++++home+runner+_work+n8n+n8n+packages+nodes-base/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet/v2"
echo "=== Sheet.resource.js lines 55-130 ==="
sed -n '55,130p' "$B/actions/sheet/Sheet.resource.js"
echo "=== delete operation params ==="
ls "$B/actions/sheet"
echo "---"
find "$B/actions/sheet" -name "*delete*" -o -name "*remove*" | head
echo "=== delete.operation.js ==="
cat "$B/actions/sheet/delete.operation.js" 2>/dev/null | head -80