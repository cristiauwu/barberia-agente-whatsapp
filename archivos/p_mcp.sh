echo "=== herramientas MCP disponibles ==="
grep -rhoE "'(search_workflows|get_workflow_details|execute_workflow|create_workflow|update_workflow|create_credential|list_credentials|set_credential)'" /usr/local/lib/node_modules/n8n/dist 2>/dev/null | sort -u | head -30
echo "=== nombres de tools registrados ==="
grep -rhoE "name: '(search|get|create|update|delete|execute|list|set)_[a-z_]+'" /usr/local/lib/node_modules/n8n/dist/modules/mcp 2>/dev/null | sort -u