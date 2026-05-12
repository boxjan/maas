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

**Decision**: The server uses `streamable-http` as its sole transport (MCP Python SDK `FastMCP.run(transport="streamable-http", ...)`). The existing skeleton's `stdio` code path is a **TC-3 violation** and must be removed entirely.

**Rationale**: TC-3 is a hard constraint — stdio transport is explicitly prohibited. The HTTP/SSE model is the correct choice for a persistent, multi-user network service. Removing stdio simplifies the entry point and eliminates an entire class of deployment errors.

**Alternatives considered**:
- *Both stdio and HTTP*: Rejected. TC-3 explicitly prohibits stdio transport with no exceptions.
- *SSE-only (no StreamableHTTP)*: The MCP SDK's `streamable-http` transport covers both SSE streaming and standard JSON responses; it is the recommended production transport from SDK v1.

---

## Decision 3: Per-Session MAAS API Key — HTTP Authorization Header

**Decision**: The MAAS API key is passed by the MCP client as an HTTP `Authorization: Bearer <api-key>` header on the initial connection request. An ASGI middleware layer extracts it, validates the format (must be `<jwt-token>`), stores it in a `contextvars.ContextVar`, and makes it available to tool handlers throughout the session lifetime.

**Rationale**: HTTP headers are the standard transport-level mechanism for per-connection credentials in HTTP-based protocols. The `Authorization` header is universally supported by HTTP clients and MCP client libraries. The app-level `maas_mcp_api_key` config field in the existing skeleton is incorrect — it would create a single-user server rather than the multi-user, token-delegation model required by FR-2.

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

## Decision 6: Structured Logging — Custom `NdjsonFormatter`

**Decision**: A custom `NdjsonFormatter` Python log formatter serializes every log record as a single-line JSON object terminated by `\n`. The formatter is installed on the root logger's `StreamHandler(sys.stdout)`. Six mandatory event types are emitted via dedicated helper functions that set the correct structured fields. The raw API key is **never** logged; only its SHA-256 hex digest (`user_token_hash`) appears in `session.opened` events.

**Rationale**: FR-10 mandates NDJSON to stdout for all log entries. A custom formatter is the simplest, most maintainable approach — it plugs into Python's standard `logging` module and requires no additional dependencies.

**Alternatives considered**:
- *`structlog`*: Popular structured logging library. Added as a dependency solely for logging seems unnecessary when a ~50-line custom formatter achieves the same result.
- *`python-json-logger`*: Another option; custom formatter avoids any additional Ubuntu archive availability risk.

---

## Decision 7: Existing Code Skeleton Assessment

The `src/maasmcpserver/` directory contains compiled `.pyc` files (no `.py` sources) representing a proof-of-concept skeleton. The following components must be **rewritten or removed**:

| File | Assessment | Action |
|------|-----------|--------|
| `config.py` | Has `maas_mcp_api_key`, `maas_mcp_db_dsn`, `maas_mcp_transport` — spec violations | Rewrite: remove these fields, add `MAAS_URL`, `MCP_HOST`, `MCP_PORT` |
| `main.py` | Supports both stdio and streamable-http — TC-3 violation | Rewrite: streamable-http only |
| `server.py` | Uses dynamic plugin loading (fragile); no lifespan context | Rewrite: explicit imports, lifespan |
| `services/context.py` | asyncpg database pool — no DB needed per spec | **Delete**: incompatible with spec |
| `tools/deployments.py` | allocate/deploy/release — TC-2 violations | **Delete**: machine lifecycle writes deferred |
| `tools/machines.py` | Stub with hardcoded test data; wrong tool names | Rewrite as `tools/fleet.py` |
| `tools/networking.py` | Interface-level tools; missing fabric/VLAN/subnet CRUD | Rewrite as `tools/network.py` (FR-13) |
| `tools/images.py` | Custom image upload tool — not in spec scope | Rewrite as `tools/boot_sources.py` (FR-14 only) |
| `tools/capacity.py` | check_capacity/hardware test failures — partial coverage | Fold into `tools/fleet.py` and `tools/diagnostics.py` |
| `models/responses.py` | Partial, inconsistent models | Rewrite per `models/` structure in plan |

---

## Decision 8: MCP SDK Tool Context Injection

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
