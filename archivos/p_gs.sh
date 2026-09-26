D=/usr/local/lib/node_modules/n8n/node_modules/.pnpm
find $D -path "*Google/Sheet/v2*" -name "*.js" 2>/dev/null | head -5
echo "--- buscando el mensaje ---"
grep -rl "Sheet with ID" $D 2>/dev/null | head -3