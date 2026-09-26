# n8n LangChain OpenAI Chat Model → Uncensored AI (uncensored.com)

## 1. How the base URL is configured in n8n 1.x

**It is set on the credential, not on the node.**

`@n8n/n8n-nodes-langchain.lmChatOpenAi` requires the `openAiApi` credential [cite:11b2f2d9-1]. That credential defines exactly three fields — **API Key**, **Organization ID (optional)**, and **Base URL** (internal name `url`, `default: 'https://api.openai.com/v1'`, description *"Override the default base URL for the API"*) — plus an optional **Add Custom Header** → **Header Name** / **Header Value** pair [cite:10611091-4].

Node source confirms precedence: `configuration.baseURL = options.baseURL` if the (legacy) node option is set, `else if (credentials.url) configuration.baseURL = credentials.url` [cite:eea2e005-1]. The node-level **Options → Base URL** (`options.baseURL`) is wrapped in `displayOptions.hide: { '@version': [{ _cnd: { gte: 1.1 } }] }` — i.e. hidden for n8n 1.x node versions ≥ 1.1 — so in current n8n you must use the **credential's Base URL** field [cite:d03b1d1f-1].

**Required suffix:** supply the API *version root*, **not** `/chat/completions`. LangChain's `ChatOpenAI` appends `/chat/completions` itself; the node's own model-discovery path strips the last path segment and appends `/models` (`baseURL.split("/").slice(-1).pop()` + `/models`) [cite:d03b1d1f-1]. So `https://host/v1` is correct and `https://host/v1/chat/completions` would produce a duplicated path.

**Docs gap:** the official n8n OpenAI credentials page documents only API Key and Organization ID — it does **not** document the Base URL field [cite:ad543f50-1][cite:42b30c9b-1]. The LangChain node page likewise only says "n8n dynamically loads models from OpenAI" [cite:f4125841-1]. So the Base URL mechanism is documented in **source code**, not official prose. Community precedent: it was a feature request that was later implemented [cite:fb33a057-3].

## 2. Credential fields and pitfalls

| Field | Notes |
|---|---|
| API Key | n8n's credential `authenticate()` sends `Authorization: Bearer <apiKey>` unconditionally [cite:10611091-4] |
| Organization ID | Sent as `OpenAI-Organization`; leave blank |
| Base URL | Version root ending in `/v1` |
| Add Custom Header | Header Name + Header Value, merged into the LangChain client's `defaultHeaders` [cite:4a4eee65-1] |

Pitfalls: (a) no trailing slash; (b) do **not** include `/chat/completions`; (c) node v1.3+ has **Use Responses API** defaulting to `true` [cite:d03b1d1f-1] — an OpenAI-compatible host with no `/v1/responses` will fail, so disable it and use Chat Completions; (d) custom-header **values containing n8n expressions break the model dropdown** ("Could not load list") even though execution still works [cite:d97c0283-2]; (e) n8n's own notice warns: *"When using non-OpenAI models via 'Base URL' override, not all models might be chat-compatible or support other features, like tools calling or JSON response format"* [cite:d03b1d1f-1].

## 3. Entering a model not in the dropdown

The **Model** field is a `resourceLocator` (node v1.2+) with modes **From List** (`searchable`, calls `searchModels`) and **ID** (`type: 'string'`, placeholder `gpt-5-mini`) [cite:d03b1d1f-1]. **Switch the mode selector to "ID" and type the model ID.** On a non-OpenAI host, the list filter intentionally includes *all* returned models [cite:d03b1d1f-1], so if `GET /v1/models` works the Uncensored IDs appear in the dropdown anyway.

## 4. Uncensored AI official API (docs.uncensored.com)

- **Base URL:** `https://api.uncensored.com/api` [cite:a4f6442f-5]
- **Chat endpoint:** `POST /v1/chat/completions`, status Live; `GET /v1/models` also Live [cite:a4f6442f-4] → full path `https://api.uncensored.com/api/v1/chat/completions`
- **Official SDK example** uses `base_url="https://api.uncensored.com/api/v1"` [cite:c84bb1d3-1]
- **Auth:** `x-api-key: YOUR_API_KEY` [cite:a4f6442f-2]. **Not** `Authorization: Bearer`. The docs contain **zero** occurrences of `Authorization` or `Bearer`.
- **Models:** live catalog at `https://api.uncensored.com/api/v1/models`; observed IDs include `aion-3-5`, `aion-3-5-mini`, `gpt-6-luna` [cite:d03b1d1f-3]. Docs say use the `Model ID` exactly as shown [cite:4a4eee65-3].
- **Tool/function calling: NOT documented.** The chat completions request-body table lists only `model`, `messages`, `temperature`, `top_p`, `max_tokens`, `stream` [cite:c84bb1d3-1]. A full-text scan of `https://docs.uncensored.com/llms-full.txt` returned **0** matches for `tools`, `tool_calls`, `tool calling`, `function calling`. The separate **Tools** area is explicitly *"Coming soon"* and covers prompt enhancement only [cite:4a4eee65-4]. **I found no documentation of function/tool calling; do not assume it works.**

## 5. Recommendation

Credential **Base URL:** `https://api.uncensored.com/api/v1`
Credential **API Key:** your Uncensored key; **Add Custom Header** → Name `x-api-key`, Value `<same key>` (static, no expression).
Node **Model:** mode **ID** → e.g. `aion-3-5` (confirm against `GET https://api.uncensored.com/api/v1/models`).
Node: **Use Responses API = off**.

**Fallback if tool calling fails** (likely, since undocumented): keep the AI Agent wired to a tool-capable provider (OpenAI gpt-4o, or any OpenAI-compatible provider with documented tool calling) and route only non-agent generation to Uncensored. Alternatively replace the AI Agent with a plain prompt chain + an HTTP Request node calling Uncensored directly — Auth header `x-api-key`, body `{"model":"aion-3-5","messages":[...]}` [cite:8a182be7-2]. This is my inference, not documented provider behavior.