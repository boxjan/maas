# Research: MAAS MCP Server

**Feature**: 001-mcp-server | **Branch**: `6689-mcp-server` | **Date**: 2025-07-22

---

## Decision 1: Module Architecture — Standalone Adapter, No Database

**Decision**: `src/maasmcpserver/` is a standalone Python module that is a pure MCP-to-MAAS-API-v3 protocol adapter. It has **no database**, no SQLAlchemy, no Alembic migrations, and no service/repository layers.

**Rationale**: The MCP server's only "data source" is the MAAS HTTP API v3. Introducing a local database would add operational complexity (DB provisioning, migrations, connection pooling) for zero benefit — all state is authoritative in MAAS. The architecture constitution's 3-tier rule applies to MAAS feature modules that own persisted data; this module is explicitly an exception.

**Alternatives considered**:
- *Caching layer (Redis/SQLite)*: Rejected. Caching MAAS state would introduce stale-data risk and violate FR-3 (MAAS API v3 is sole source of truth).
- *Embedding in `maasapiserver`*: Rejected. MCP protocol is independent from the MAAS REST API; embedding would couple unrelated concerns and violate FR-8 (operational independence).

---

## Decision 2: MCP Transport — Streamable-HTTP Only

**Decision**: The server uses `streamable-http` as its sole transport (MCP Python SDK `FastMCP.run(transport="streamable-http", ...)`). stdio is not supported (TC-3 hard constraint).

**Rationale**: TC-3 is a hard constraint — stdio transport is explicitly prohibited. The HTTP/SSE model is the correct choice for a persistent, multi-user network service. Removing stdio simplifies the entry point and eliminates an entire class of deployment errors.

**Alternatives considered**:
- *Both stdio and HTTP*: Rejected. TC-3 explicitly prohibits stdio transport with no exceptions.
- *SSE-only (no StreamableHTTP)*: The MCP SDK's `streamable-http` transport covers both SSE streaming and standard JSON responses; it is the recommended production transport from SDK v1.

---

## Decision 3: Per-Session MAAS API Key — HTTP Authorization Header

**Decision**: The MAAS API key is passed by the MCP client as an HTTP `Authorization: Bearer <api-key>` header on the initial connection request. An ASGI middleware layer extracts it, validates the format (must be `<jwt-token>`), stores it in a `contextvars.ContextVar`, and makes it available to tool handlers throughout the session lifetime.

**Rationale**: HTTP headers are the standard transport-level mechanism for per-connection credentials in HTTP-based protocols. The `Authorization` header is universally supported by HTTP clients and MCP client libraries, and correctly implements the multi-user token-delegation model required by FR-2.

**Alternatives considered**:
- *MCP `initialize` request params*: The MCP protocol's `initialize` message carries `clientInfo` and optional `meta`. Passing the API key here is possible but requires SDK-level hooks to access init params, which is more complex and less standard than HTTP headers.
- *Dedicated `initialize_session` tool*: Requires a mandatory first tool call before any other tools work. This is a poor UX and non-standard.
- *App-level config (single key)*: Explicitly forbidden by FR-2 (no centralized service accounts; per-user session isolation required).

**Session lifetime**: Connection-scoped (FR-11). When the HTTP/SSE connection closes, the session and its API key reference are torn down immediately.

---

## Decision 4: MAAS HTTP Authentication — JWT Bearer Token

**Decision**: MAAS API v3 uses JWT Bearer token authentication. The user's JWT token is forwarded directly in the `Authorization: Bearer <jwt-token>` header on every outbound MAAS API v3 request. No signing, no OAuth handshake — the token is passed through as-is.

**Rationale**: MAAS API v3 authenticates via JWT, not OAuth 1.0a (which is the v2 format). Bearer token forwarding is trivial to implement — it requires no third-party signing library, no per-request computation, and no additional Ubuntu archive dependency beyond `httpx`. This also simplifies the auth middleware: it only needs to extract and validate that a non-empty token is present, not parse a structured key format.

**Alternatives considered**:
- *OAuth 1.0a via `oauthlib`*: This is the MAAS v2 authentication model. Rejected — incorrect for API v3.
- *Custom token parsing/validation*: Rejected — the MCP server must forward the token to MAAS as-is; MAAS is the authority on token validity.

---

## Decision 5: MAAS HTTP Client — `httpx.AsyncClient`

**Decision**: All MAAS API v3 HTTP calls go through `MAASClient`, a thin async wrapper around `httpx.AsyncClient`. Per-request timeout is enforced unconditionally via `httpx.Timeout(timeout=MAAS_REQUEST_TIMEOUT)`. On `httpx.TimeoutException` or `httpx.ConnectError`, the client raises `MAASUnreachableError` without retrying (FR-11).

**Rationale**: `httpx` is the modern async Python HTTP client with first-class timeout support, connection pooling, and a clean API. It is available in the Ubuntu archive (`python3-httpx`). The no-retry policy is a hard spec requirement.

**Alternatives considered**:
- *`aiohttp`*: Functionally equivalent; `httpx` preferred for cleaner API and better Ubuntu archive availability.
- *`requests` (sync)*: Rejected. Sync HTTP would block the async event loop, violating FR-11's hard timeout guarantee.

---

## Decision 6: Structured Logging — Local `configure_logging()` following `maasservicelayer` pattern

**Decision**: The MCP server implements its own `configure_logging()` in `logging_events.py`, following the identical pattern used by `maasservicelayer.logging.configure` — `structlog` + `pythonjsonlogger` (`CustomJsonFormatter`) on the root logger's `StreamHandler(sys.stdout)`. It cannot import from `maasservicelayer` directly (only `maascommon` imports are permitted).

For token hashing in `session.opened` events, use `maascommon.logging.security.hash_token_for_logging()` — this is already the canonical SHA-256 helper for this purpose.

All log statements use `structlog.getLogger()` with keyword-argument structured fields, consistent with the rest of the MAAS codebase.

**Rationale**: `maasservicelayer` is out of bounds for the MCP server. Replicating the ~40-line `configure_logging()` locally is the right approach — it keeps the JSON-to-stdout format consistent with the MAAS observability stack without introducing a forbidden dependency. `maascommon` imports are permitted and provide `hash_token_for_logging()` out of the box.

**Alternatives considered**:
- *Import `maasservicelayer.logging.configure` directly*: Rejected — `maasservicelayer` imports are not permitted from the MCP server.
- *Custom `NdjsonFormatter` from scratch*: Rejected — unnecessary; the `structlog` + `pythonjsonlogger` pattern is already established and both packages are in the Ubuntu archive.

---

## Decision 7: MCP SDK Tool Context Injection

**Decision**: Tool functions accept `ctx: Context[ServerSession, AppLifespan]` as an injected parameter (automatically provided by the `FastMCP` framework). The session's MAAS API key is retrieved from the `ContextVar` set by the auth middleware. `MAASClient` is instantiated per tool call (not per session) using the session's API key and the server-level config.

**Rationale**: The MCP SDK auto-injects `Context` when it sees the type annotation. The `ContextVar` approach for the API key cleanly isolates per-session credentials without requiring the SDK's session store, which has limited customizability in v1.

---

## Decision 9: Tool Inventory Scope

In-scope tools (30 total):

**Fleet (FR-4, US2)**:
- `list_machines`, `get_machine`, `list_resource_pools`, `list_zones`, `get_machine_power_state`

**Diagnostics (FR-5, US4)**:
- `get_machine_events`, `get_script_results`

**MAAS Info (FR-12, US3)**:
- `get_maas_info`

**Network (FR-13, US5)** — 15 tools:
- `list_fabrics`, `get_fabric`, `create_fabric`, `update_fabric`, `delete_fabric`
- `list_vlans`, `get_vlan`, `create_vlan`, `update_vlan`, `delete_vlan`
- `list_subnets`, `get_subnet`, `create_subnet`, `update_subnet`, `delete_subnet`

**Boot Sources (FR-14, US6)**:
- `list_boot_sources`, `trigger_boot_source_sync`, `delete_boot_source`

**Deferred (TC-2)** — not implemented, not listed:
- All machine lifecycle write tools from FR-6 (commission, deploy, release, abort, rescue, tag mutations, pool reassignment, power parameter updates, ownership changes)

---

## Decision 10: Conventional Commits Scope

**Decision**: New scope `mcp` maps to `src/maasmcpserver/`. Must be added to `scopes.md` before the first commit on this branch.

**Example commits**:
- `feat(mcp): add list_machines tool with status/zone/pool filters`
- `feat(mcp): implement NDJSON structured logging`
- `fix(mcp): enforce MAAS_REQUEST_TIMEOUT on all httpx calls`
- `test(mcp): add session isolation tests`
- `docs(mcp): add quickstart guide`

---

## Open Items (Low Risk)

1. **`python3-mcp` Ubuntu archive availability**: Verify the package exists for the target Ubuntu LTS series. If not yet published, raise a blocker — TC-1 prohibits PyPI install.
2. **Machine filter query parameters**: MAAS API v3 `GET /MAAS/a/v3/machines` may accept filter parameters differently from v2 (POST-body filter vs. query string). Verify against `openapi-spec.json` `GET /MAAS/a/v3/machines` parameter definitions before implementing `list_machines`.
3. **Script results endpoint**: Commissioning/hardware test script results endpoint in API v3 needs to be confirmed (`GET /MAAS/a/v3/machines/{system_id}/...`). Look for `/script_results` in openapi-spec.json.
