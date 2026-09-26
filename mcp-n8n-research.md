# Connecting an AI Agent to a Local n8n Instance via MCP

Research scope: Windows 11, n8n installed locally (data dir `C:\Users\kimbo\.n8n`, sqlite DB exists) but not running (port 5678 does not respond); Node.js at `C:\Program Files\nodejs` (not on PATH); MCP client is Cherry Studio (stdio `{command, args, env}` and remote `{baseUrl, headers}`). Research only — nothing was installed, run, or modified.

---

## 1. Official n8n MCP server — **yes, it exists and is built in**

Source: <https://docs.n8n.io/connect/connect-to-n8n-mcp-server> (markdown: append `.md`), client examples: <https://docs.n8n.io/connect/connect-to-n8n-mcp-server/mcp-client-examples>, tools reference: <https://docs.n8n.io/connect/connect-to-n8n-mcp-server/mcp-server-tools-reference>

**Enable:** log in as owner/admin → **Settings > Instance-level MCP** → **Enable MCP access**. [cite:0a1bb323-1]

**Exact endpoint:** the **Server URL** "ends in `/mcp-server/http`", e.g. `http://localhost:5678/mcp-server/http`. The docs explicitly state: "If your instance serves plain HTTP, such as a local install at `http://localhost:5678`, use `http://` instead." This is *not* the address of your n8n editor — "Don't paste the URL from your browser's address bar." [cite:0a1bb323-1][cite:27f7ce33-1][cite:0a1bb323-2]

Current docs no longer document an `/sse` endpoint path; only `/mcp-server/http` is canonical.

**Auth (two options):**
- **OAuth (recommended)** — the client is taken through a sign-in/approve flow; connected clients appear under **Connected clients** and can be revoked individually. Per-client setup steps exist from n8n 2.33.0.
- **API key** — in **Connect a client > API key** tab, n8n auto-generates a personal access token tied to your user account, and shows a **Configuration JSON** block "already filled in with your server URL and an `Authorization: Bearer` header carrying your token". Sent as header `Authorization: Bearer <YOUR_N8N_MCP_TOKEN>`. Once you leave the tab, n8n only shows a redacted token; rotate it with the button next to the redacted value (rotation revokes the previous token). [cite:0a1bb323-1][cite:0a1bb323-2]

**Versions:**
- Instance-level MCP announced in beta on 2025-11-18; `search_workflows` / `get_workflow_details` shipped as of n8n **1.120**, `execute_workflow` as of **1.121**. [cite:27f7ce33-2]
- Building/editing workflows via MCP available from n8n **2.13.0**. [cite:27f7ce33-1]
- Workflow tags filtering from **2.27.0**; `detailLevel` from **2.35.0**; folder filtering from **2.37.0**. [cite:119b32d3-1]
- The **Connect a client** dialog and the three-section settings layout (**Connection details**, **Access**, **Connected clients**) plus **Allowed callback URLs** are available from n8n **2.33.0**. On older versions the page shows a simpler layout without per-client setup steps. [cite:27f7ce33-1]
- czlonkowski's integration doc states instance-level MCP needs n8n **2.18.4 or later**, the agents module needs **2.34+**, and native `diff` needs **2.36**. [cite:51755dec-1 / OFFICIAL_MCP_SETUP]

**Self-hosted local instance:** yes — the docs section is titled "For Cloud and self-hosted instances". Requires instance owner or admin permissions. [cite:27f7ce33-1] MCP settings can also be managed via environment variables on self-hosted instances; complete disablement via `N8N_DISABLED_MODULES=mcp`, which "removes MCP endpoints and hides all related UI elements". [cite:27f7ce33-1]

**Exposure model (important):** enabling MCP does *not* expose all workflows. You must toggle **Available in MCP** per workflow (Workflow → Settings). Only published workflows containing a webhook, form, schedule, or chat trigger are eligible. Exception: `search_workflows` can list every workflow the current user may view — but only previews, not full workflow data. Most MCP tools work on unpublished workflows; `execute_workflow` defaults to production mode (published version) and also supports a `manual` mode. [cite:0a1bb323-1][cite:27f7ce33-2]

**Tools exposed** include: `search_workflows`, `get_workflow_details`, `execute_workflow`, workflow builder tools, agent management tools, and data table tools. [cite:119b32d3-1]

⚠️ **Unverified:** the installed n8n version is unknown, so whether this local instance actually exposes the feature cannot be confirmed.

---

## 2. Community option — `n8n-mcp` by czlonkowski

Repo: <https://github.com/czlonkowski/n8n-mcp> · self-hosting guide: <https://github.com/czlonkowski/n8n-mcp/blob/main/docs/SELF_HOSTING.md> · env template: <https://github.com/czlonkowski/n8n-mcp/blob/main/.env.example> · official-MCP bridge doc: <https://github.com/czlonkowski/n8n-mcp/blob/main/docs/OFFICIAL_MCP_SETUP.md>

**Exact npm package name:** `n8n-mcp` (current version 2.89.0; `bin` maps `n8n-mcp` → `./dist/mcp/stdio-wrapper.js`). [cite:51755dec-1]

**Exact stdio launch command and args:** `npx n8n-mcp` — documented in both the README and `docs/SELF_HOSTING.md`: "Run directly with npx (no installation needed!)". [cite:51755dec-3] Add `-y` to suppress the npx install prompt (harmless; useful for non-interactive clients).

**Required environment variables** (values shown are self-hosting-doc examples):

| Variable | Example value | Notes |
|---|---|---|
| `MCP_MODE` | `stdio` | **Required** for stdio clients. "Without it, you will see JSON parsing errors like `Unexpected token...` in the UI. This variable ensures that only JSON-RPC messages are sent to stdout, preventing debug logs from interfering with the protocol." [cite:51755dec-3] |
| `LOG_LEVEL` | `error` | The name actually read by the code (`process.env.LOG_LEVEL` in `src/utils/logger.ts`). [cite:51755dec-1] |
| `DISABLE_CONSOLE_OUTPUT` | `true` | Read by `src/utils/logger.ts` to suppress all console output in stdio mode. |
| `N8N_API_URL` | `http://localhost:5678` | Base URL of the instance — **no** `/api/v1` suffix. [cite:51755dec-3] |
| `N8N_API_KEY` | `your-api-key` | Required only for the n8n management tools. [cite:51755dec-3] |
| `N8N_MCP_ACCESS_TOKEN` | official MCP token | Optional, purely additive. Enables `n8n_manage_agents`, `n8n_explore_node_resources`, and the team-project fallback in `n8n_list_catalog`; also routes `n8n_test_workflow` (`prepare`/`pinned`/`direct`), `n8n_workflow_versions` (`source: 'native'`) and `n8n_manage_datatable` column actions to n8n's own MCP server. Separate secret from `N8N_API_KEY`. The MCP endpoint is derived from `N8N_API_URL`. [cite:51755dec-1] |
| `npm_config_cache` | a unique directory path | Only needed when running n8n-mcp from multiple MCP clients concurrently (npm cache-lock conflicts). |

Other documented variables: `NODE_DB_PATH` (default `./data/nodes.db`), `NODE_ENV`, `REBUILD_ON_START`, `MCP_SERVER_PORT`, `MCP_SERVER_HOST`, `MCP_AUTH_TOKEN`, `PORT`/`HOST`/`AUTH_TOKEN`/`CORS_ORIGIN` (HTTP mode), `BASE_URL`/`PUBLIC_URL`, `TRUST_PROXY`, `N8N_CF_CLIENT_ID` / `N8N_CF_CLIENT_SECRET` (Cloudflare Access), `DISABLED_TOOLS`, `DISABLED_TOOL_OPERATIONS`. [cite:51755dec-2][cite:51755dec-1]

⚠️ **Documented inconsistency:** `.env.example` lists `MCP_LOG_LEVEL=info`, but `src/utils/logger.ts` reads `LOG_LEVEL`. The published configs in `docs/SELF_HOSTING.md`, `docs/CLAUDE_CODE_SETUP.md` and `docs/OFFICIAL_MCP_SETUP.md` all use `LOG_LEVEL`. Use `LOG_LEVEL`.

**Is an n8n API key required?** No. `docs/SELF_HOSTING.md`: "The n8n API credentials are optional. Without them, you'll have access to all documentation tools." [cite:51755dec-3]

**Can it run without a live n8n instance?** Yes — documentation-only mode. The npm package bundles a pre-built database: "The package includes a pre-built database with all n8n node information" covering 2,864 nodes (836 core + 2,028 community), 2,352 workflow templates, etc. Management tools obviously require a live instance and a valid key. [cite:51755dec-3][cite:51755dec-1]

**Creating the n8n API key:** n8n → **Settings > n8n API** → **Create an API key** → choose a **Label** and an **Expiration** (Enterprise customers also choose **Scopes**) → copy **My API Key**. It is sent to the REST API as a header named `X-N8N-API-KEY`. Note: "The n8n API isn't available during the free trial." [cite:7e8d580b-1]

---

## 3. Exact JSON config blocks to paste into Cherry Studio

**Option A — community stdio (works even with n8n stopped):**
```json
{
  "command": "npx",
  "args": ["-y", "n8n-mcp"],
  "env": {
    "MCP_MODE": "stdio",
    "LOG_LEVEL": "error",
    "DISABLE_CONSOLE_OUTPUT": "true",
    "N8N_API_URL": "http://localhost:5678",
    "N8N_API_KEY": "your-api-key"
  }
}
```

**Option A2 — community stdio, absolute Windows path (recommended, since `npx` is not on PATH):**
```json
{
  "command": "C:\\Program Files\\nodejs\\npx.cmd",
  "args": ["-y", "n8n-mcp"],
  "env": {
    "MCP_MODE": "stdio",
    "LOG_LEVEL": "error",
    "DISABLE_CONSOLE_OUTPUT": "true",
    "N8N_API_URL": "http://localhost:5678",
    "N8N_API_KEY": "your-api-key"
  }
}
```

**Option B — official remote (n8n must be running), streamableHttp:**
```json
{
  "baseUrl": "http://localhost:5678/mcp-server/http",
  "headers": {
    "Authorization": "Bearer <YOUR_N8N_MCP_TOKEN>"
  }
}
```

**Option C — official remote via stdio bridge** (from n8n's own Claude Desktop example, adapted to Cherry Studio's stdio shape):
```json
{
  "command": "npx",
  "args": [
    "-y",
    "supergateway",
    "--streamableHttp",
    "http://localhost:5678/mcp-server/http",
    "--header",
    "Authorization:Bearer <YOUR_N8N_MCP_TOKEN>"
  ],
  "env": {}
}
```

Reference (upstream n8n docs, unmodified) for the `supergateway` variant:
```json
"mcpServers": {
  "n8n-mcp": {
    "command": "npx",
    "args": [
    "-y",
    "supergateway",
    "--streamableHttp",
    "https://<your-n8n-domain>/mcp-server/http",
    "--header",
    "Authorization:Bearer <YOUR_N8N_MCP_TOKEN>"
    ]
  }
}
```
[cite:0a1bb323-2]

---

## 4. Windows-specific gotchas

- **`npx` not on PATH.** Cherry Studio spawns `command` directly; if `npx` cannot be resolved the server silently fails to start. Use the absolute path `C:\\Program Files\\nodejs\\npx.cmd` — on Windows npm ships `npx.cmd`, not a bare `npx` executable. [cite:51755dec-3]
- **Node version:** the project's CHANGELOG states "**Declared runtime engine is now Node 20 or newer**" (`package.runtime.json`), and `@supabase/supabase-js` is deliberately held below 2.110 because "2.110.0 onwards declares Node 22 as its minimum". So Node **20 or newer** is required; Node 20/21 is the safest. Verify with `node --version`. [cite:7a77698c-3] The README's own Docker note says the image contains "NO n8n dependencies". [cite:51755dec-3]
- **npm cache-lock conflicts:** "Launching n8n-mcp via `npx` from two clients simultaneously can hit npm cache lock conflicts. Give each client a different `npm_config_cache` directory (the path must be unique per client — don't reuse one path) in its `env`." [cite:51755dec-3]
- **First-run download latency:** npx downloads the package on first launch; pre-warm it from a shell so the client's MCP startup timeout isn't hit.
- **Historical Windows bug:** issue #204, "[Bug] 'Differential update failed' when modifying workflows with n8n v1.111.0 on Windows" — relevant if you see workflow-update failures on an older combination. [cite:7a77698c-1]
- **ESM:** the published `bin` is a plain `.js` wrapper (`./dist/mcp/stdio-wrapper.js`); no user-facing ESM flags are needed. [cite:51755dec-1]
- **WSL not required.** Native Windows is supported; the docs provide native PowerShell variants for Claude Code setup. [cite:35a4ae3c-1]
- **Docker alternative:** if you'd rather run n8n-mcp in Docker, use `http://host.docker.internal:5678` as `N8N_API_URL` when n8n runs on the host. [cite:51755dec-3]

---

## 5. Verification procedure

**Official n8n MCP server:**
Call **`search_workflows`** (parameters: `query`, `projectId`, `tags`, `limit` default 200 max 200, `sortBy` default `"updatedAt:desc"`, `folderId`, `includeSubfolders` default true). A successful result is an object containing:
- `data[]` — workflow previews with `id`, `name`, `description`, `active`, `createdAt`, `updatedAt`, `triggerCount`, `availableInMCP`, `parentFolderId`, `tags[]`
- `count` — integer total of matching workflows

An auth failure means the Bearer token is wrong/expired or the OAuth grant was revoked. [cite:119b32d3-1]

**Community n8n-mcp server:**
Call **`n8n_health_check`** — "Check n8n API connectivity and features, including `officialMcp` status when `N8N_MCP_ACCESS_TOKEN` is configured." With the official token set, the response includes an `officialMcp` block with `configured` (true once `N8N_MCP_ACCESS_TOKEN` is set), `reachable` (whether the last check reached n8n's MCP server), and `toolCount` (how many tools n8n's own MCP server advertises, i.e. n8n's list rather than n8n-mcp's). [cite:51755dec-1][cite:OFFICIAL_MCP_SETUP]

**Docs-only smoke test (no running n8n needed):** call **`search_nodes`** (e.g. `{query: 'trigger'}`) or `get_node` (`{nodeType, detail: 'minimal'}`). Success proves the MCP transport and bundled node database work independently of n8n availability. Paired tools for a fuller check: `validate_node({nodeType, config, mode: 'minimal'})`, `get_node({nodeType, detail: 'standard', includeExamples: true})`, `search_templates`. [cite:51755dec-1]

**Tool count expectation:** upstream screenshots show ~39 tools available in a connected client; `n8n_list_catalog` lists instance-level projects or tags. [cite:35a4ae3c-1][cite:51755dec-1]

---

## Uncertainties / could not verify

1. **Installed n8n version is unknown** — this determines whether the official instance-level MCP server exists locally at all (needs ≈2.18.4+, ideally 2.33.0+ for the Connect-a-client dialog and current settings layout).
2. **`MCP_LOG_LEVEL` vs `LOG_LEVEL`** — `.env.example` documents `MCP_LOG_LEVEL`, but `src/utils/logger.ts` reads `LOG_LEVEL`; all official sample configs use `LOG_LEVEL`. Use `LOG_LEVEL`.
3. **Cherry Studio's exact remote-server schema** — the user supplied `{baseUrl, headers}`; whether Cherry Studio supports `streamableHttp` MCP natively (vs. requiring the `supergateway` stdio bridge) could not be confirmed from Cherry Studio documentation in this research pass.
4. **`/sse` endpoint** — current n8n docs no longer mention an `/sse` path for the official server; only `/mcp-server/http` is documented. Do not assume `/sse` works.
5. **Publishing behavior of the official server** — whether `search_workflows` previews are sufficient for the agent's read/modify goal depends on per-workflow "Available in MCP" toggles, which must be set manually in the n8n UI (or via n8n-mcp's `exposeToMcp: true` consent flow).
6. No installs, no n8n runs, and no file modifications were performed — research only.