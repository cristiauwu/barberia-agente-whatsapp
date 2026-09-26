#!/bin/sh
B="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/n8n-nodes-base@file++++home+runner+_work+n8n+n8n+packages+nodes-base/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet/v2"
echo "=== v2 actions/resource operations ==="
grep -rn "value: 'delete\|value: 'remove\|value: 'appendOrUpdate\|value: 'append'\|value: 'update'\|value: 'clear'\|value: 'deleteRows'\|deleteRows\|removeRows" "$B/actions" 2>/dev/null | head -40
echo "=== resource options ==="
grep -rn "name: 'resource'" -A 30 "$B/actions/versionDescription.js" 2>/dev/null | head -60