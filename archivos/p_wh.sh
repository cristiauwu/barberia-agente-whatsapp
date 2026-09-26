echo "=== Evolution incluye apikey en el payload del webhook? ==="
grep -rhoE '.{120}(apikey|apiKey).{120}' /evolution/dist/main.js 2>/dev/null | grep -iE 'webhook|server_url|instance' | head -5
echo "--- claves tipicas del payload ---"
grep -rhoE 'serverUrl[^;]{0,200}' /evolution/dist/main.js 2>/dev/null | head -3