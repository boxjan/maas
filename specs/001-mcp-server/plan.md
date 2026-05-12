# Implementation Plan: MAAS MCP Server

**Branch**: `6689-mcp-server` | **Date**: 2025-07-22 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/001-mcp-server/spec.md`

## Summary

A new, standalone Python module `src/maasmcpserver/` that implements a Model Context Protocol (MCP) server bridging AI assistants to MAAS bare-metal infrastructure. The server communicates exclusively with MAAS HTTP API v3 via per-session token delegation — every tool call is made under the requesting user's own MAAS API key with no credential substitution. Transport is HTTP/SSE (streamable-http) only; stdio is prohibited. The module has **no database dependency** — all data flows through MAAS API v3 via `httpx` async HTTP calls. Machine lifecycle write operations are fully deferred (TC-2); network management (fabric/VLAN/subnet) and boot-source operations are in scope.

## Technical Context

**Language/Version**: Python 3.14  
**Primary Dependencies**:
- `python3-mcp` (Ubuntu archive — TC-1, **NOT** PyPI): MCP Python SDK (`FastMCP` / `MCPServer`)
- `httpx` (async HTTP client for MAAS API v3 calls)
- `pydantic` v2 (response models, config via `pydantic-settings`)
- `uvicorn` (ASGI server for streamable-http transport)
- `python3-jwt` (MAAS API v3 JWT Bearer token authentication — no signing required, forwarded as-is)

**Database**: **None** — the MCP server has no direct database dependency; all state is sourced from MAAS API v3.  
**Testing**: `pytest` + `pytest-asyncio` + `httpx` (`AsyncMock`) — no `db_connection` fixture needed.  
**Target Component**: `src/maasmcpserver/` — new standalone module, NOT part of `maasapiserver` or `maasservicelayer`.  
**Architecture Pattern**: **Exception to 3-tier constitution rule** (documented below). This module is a thin adapter layer: MCP protocol ↔ MAAS HTTP API v3. No service layer, no repository layer, no database.  
**Import boundary (hard constraint)**: `maasmcpserver` may only import from `maascommon`. Imports from `maasservicelayer`, `maasapiserver`, `maasserver`, or any other MAAS component are **not permitted**.  
**Scale/Scope**: 1 standalone server module, ~30 MCP tools, 5 tool-group files, 1 async HTTP client, `structlog`-based structured logging (pattern from `maasservicelayer`, implemented locally), 1 Pydantic config, 1 session-auth middleware.

## Constitution Check

*Gate: Verify compliance before Phase 1 research.*

- ✅ **Architecture exception documented**: `maasmcpserver` is a new standalone module, not a MAAS v3 API feature. The 3-tier architecture (API → Service → Repository) does not apply. This module has no database, no ORM, no SQLAlchemy, and no service/repository layers. **Rationale**: The MCP server is a protocol adapter; its "data layer" is the external MAAS HTTP API v3.
- ✅ **No database migrations required**: No schema changes; no Alembic migration needed. MCP server is stateless (no persistent storage).
- ✅ **Testing strategy**: `pytest` + `pytest-asyncio`; tool tests mock the MAAS HTTP client (`httpx.AsyncClient`); integration tests use a live MAAS endpoint (optional). No `db_connection` fixture.
- ✅ **Conventional Commits scope**: New scope `mcp` maps to `src/maasmcpserver/`. **Action required**: Add `mcp` to `scopes.md` before first commit.
- ✅ **Ruff formatting**: 79 chars, double quotes — enforced as per constitution.
- ✅ **No ORM in repositories**: N/A — no repositories. No SQLAlchemy at all in this module.
- ✅ **TC-1**: `python3-mcp` sourced from Ubuntu archive only. No PyPI `pip install mcp`.
- ✅ **TC-2**: Machine lifecycle write tools absent from tool listing and implementation.
- ✅ **TC-3**: HTTP/SSE (streamable-http) transport only; stdio transport not implemented.
- ✅ **TC-4**: No TLS configuration on MCP listener; plain HTTP only; operator uses reverse proxy.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-mcp-server/
├── spec.md              # User stories and requirements (input)
├── plan.md              # This file
├── research.md          # Phase 0: Architecture & API decisions
├── data-model.md        # Phase 1: Domain models (no DB schema)
├── quickstart.md        # Phase 1: Getting started guide
├── contracts/
│   ├── tools.md         # MCP tool contracts (all 30 tools)
│   ├── maas_client.md   # MAAS API v3 HTTP client interface
│   └── config.md        # Configuration schema (env vars)
└── tasks.md             # Phase 2: Actionable task list
```

### Source Code (repository root)

```text
src/maasmcpserver/          # New standalone module
├── __init__.py
├── config.py               # Pydantic Settings (env vars)
├── server.py               # MCPServer factory + tool registration
├── main.py                 # Entry point (streamable-http only)
├── auth.py                 # MAAS API key extraction & OAuth signing
├── client.py               # MAAS API v3 async HTTP client (httpx)
├── logging_events.py       # FR-10 structured log event helpers (structlog)
├── errors.py               # MCP error types (maas_unreachable, etc.)
├── models/
│   ├── __init__.py
│   ├── machines.py         # Machine, MachineDetail, Interface models
│   ├── network.py          # Fabric, VLAN, Subnet models
│   ├── boot.py             # BootSource, BootSourceSelection models
│   └── info.py             # MAASInfo, RackController models
└── tools/
    ├── __init__.py
    ├── fleet.py            # US2/FR-4: list_machines, get_machine, etc.
    ├── diagnostics.py      # US4/FR-5: get_machine_events, etc.
    ├── info.py             # US3/FR-12: get_maas_info
    ├── network.py          # US5/FR-13: fabric/VLAN/subnet CRUD
    └── boot_sources.py     # US6/FR-14: list/sync/delete boot sources

src/tests/maasmcpserver/    # Test suite
├── conftest.py             # Shared fixtures (mock client, server)
├── test_config.py          # Config loading, env var defaults
├── test_auth.py            # OAuth signing, key extraction
├── test_client.py          # MAAS HTTP client (timeout, errors)
├── test_logging_events.py  # FR-10 structured field validation
├── tools/
│   ├── test_fleet_tools.py
│   ├── test_diagnostic_tools.py
│   ├── test_info_tools.py
│   ├── test_network_tools.py
│   └── test_boot_source_tools.py
└── test_integration.py     # End-to-end (live MAAS, optional)

debian/
├── maas-mcp-server.install       # Package file list
├── maas-mcp-server.service       # systemd unit
└── maas-mcp-server.dirs          # Directory ownership
```

---

## Implementation Phases

### Phase 0: Research & Discovery ✅ COMPLETE

**Goal**: Resolve all open architecture questions before implementation.

**Deliverables**: `research.md` — see that file for all decisions.

**Go/No-Go**: ✅ All blockers resolved. Proceed to Phase 1.

---

### Phase 1: Foundation — Config, Auth, Client, Logging

**Goal**: Build the non-tool infrastructure that all tools depend on.

**Deliverables**: `config.py`, `auth.py`, `client.py`, `logging_events.py`, `errors.py`, updated `server.py` and `main.py`.

**Tasks**:
- [ ] T101: `config.py` — `MaasServerConfig` Pydantic Settings: `MAAS_URL`, `MAAS_REQUEST_TIMEOUT` (int, default 30), `MCP_HOST` (default `0.0.0.0`), `MCP_PORT` (int, default 8765). Remove `maas_mcp_api_key`, `maas_mcp_db_dsn`, `maas_mcp_transport` from existing skeleton (TC-3/TC-4 violations).
- [ ] T102: `auth.py` — `extract_token(request)` extracts JWT from `Authorization: Bearer` header; `build_auth_header(token) → dict` returns `{"Authorization": "Bearer <token>"}` for use by `MAASClient`. `hash_token(token) → str` returns SHA-256 hex digest (for logging — never log the raw token).
- [ ] T103: `client.py` — `MAASClient(base_url, api_key, timeout)` async context manager wrapping `httpx.AsyncClient`. Methods: `get()`, `post()`, `put()`, `delete()` — each adds `Authorization: Bearer` header, enforces timeout, emits `maas.request` + `maas.response` log events. On timeout or connection refused, raises `MAASUnreachableError`.
- [ ] T104: `logging_events.py` — implement `configure_logging()` following the `maasservicelayer.logging.configure` pattern (`structlog` + `pythonjsonlogger.json.JsonFormatter` on `StreamHandler(sys.stdout)`). Use `maascommon.logging.security.hash_token_for_logging()` for token hashing in `session.opened` events. Emit all six FR-10 mandatory events as `structlog.getLogger()` calls with keyword fields. **Do not import from `maasservicelayer`** — only `maascommon` imports are permitted.
- [ ] T105: `errors.py` — `MAASUnreachableError(url_pattern, failure_mode)`, `MCPNotImplementedError(tool_name)`. Both produce `CallToolResult(is_error=True)` with correct `error_code` fields.
- [ ] T106: `server.py` — Rewrite to create `FastMCP` server with lifespan context providing `MaasServerConfig`. Tool modules register via `register_*_tools(server)`. Replace dynamic plugin loading with explicit imports.
- [ ] T107: `main.py` — Rewrite entry point: `asyncio.run(serve())` calls `mcp.run(transport="streamable-http", host=cfg.mcp_host, port=cfg.mcp_port)`. Remove all stdio code paths (TC-3). Remove TLS config (TC-4).
- [ ] T108: Auth middleware — ASGI middleware extracts `Authorization` header, validates format, stores API key in `contextvars.ContextVar` before passing to MCP handler. Returns HTTP 401 if missing or malformed.

**Quality Gates**:
- `python3-mcp` imported, not `pip install mcp`
- No stdio code path exists anywhere
- No TLS config keys in config schema
- `MAAS_REQUEST_TIMEOUT` enforced on all httpx calls
- Raw API key never appears in any log line (SHA-256 hash only)

**Duration**: ~3 days

---

### Phase 2: Fleet Discovery & Diagnostic Tools (US2, US4)

**Goal**: Implement all read-only machine and diagnostic tools (FR-4, FR-5).

**Deliverables**: `tools/fleet.py`, `tools/diagnostics.py`, `models/machines.py`.

**Tasks**:
- [ ] T201: `models/machines.py` — `MachineSummary`, `MachineDetail`, `InterfaceSummary`, `StorageDevice`, `BlockDevice` Pydantic models matching MAAS API v3 response schema.
- [ ] T202: `tools/fleet.py` — Register tools: `list_machines` (filters: status, zone, pool, architecture, tags, owner, power_state; pagination via page/size), `get_machine` (full hardware detail: interfaces, storage, block devices), `list_resource_pools`, `list_zones`, `get_machine_power_state`. Each tool fetches from `MAASClient` and returns a formatted string.
- [ ] T203: `tools/diagnostics.py` — Register tools: `get_machine_events` (with `since_hours` filter using `GET /MAAS/a/v3/events?system_id=X`), `get_script_results` (commissioning/hardware test output).
- [ ] T204: Tests for fleet tools — mock `MAASClient`, assert correct endpoint URLs, pagination forwarded, empty results handled gracefully.
- [ ] T205: Tests for diagnostic tools — mock `MAASClient`, assert time filter applied, commissioning vs hardware test type distinction.

**Quality Gates**:
- Pagination parameters (`page`, `size`) forwarded to all list endpoints
- Empty result returns clear message, not error
- All tests pass with `pytest-asyncio`

**Duration**: ~3 days

---

### Phase 3: MAAS Instance Identification (US3 / FR-12)

**Goal**: Implement `get_maas_info` tool.

**Deliverables**: `tools/info.py`, `models/info.py`.

**Tasks**:
- [ ] T301: `models/info.py` — `RackController(hostname, rack_id, connection_state)`, `MAASInfo(deployment_name, rack_controllers)`. No `instance_uuid` or `region_controllers` fields (API v3 constraint, not available).
- [ ] T302: `tools/info.py` — Register `get_maas_info` tool: calls `GET /MAAS/a/v3/configurations/maas_name` + `GET /MAAS/a/v3/racks` concurrently (via `asyncio.gather`). Returns `MAASInfo`. If either times out, returns `maas_unreachable` error.
- [ ] T303: Tests — mock both API calls, assert concurrent invocation, assert response excludes `instance_uuid`, assert timeout propagates as `maas_unreachable`.

**Duration**: ~1 day

---

### Phase 4: Network Management Tools (US5 / FR-13)

**Goal**: Implement full fabric/VLAN/subnet CRUD tools.

**Deliverables**: `tools/network.py`, `models/network.py`.

**Tasks**:
- [ ] T401: `models/network.py` — `Fabric`, `VLAN`, `Subnet` Pydantic models matching API v3 response schemas.
- [ ] T402: `tools/network.py` — Register 15 tools:
  - Read: `list_fabrics`, `get_fabric`, `list_vlans`, `get_vlan`, `list_subnets`, `get_subnet`
  - Write: `create_fabric`, `update_fabric`, `delete_fabric`, `create_vlan`, `update_vlan`, `delete_vlan`, `create_subnet`, `update_subnet`, `delete_subnet`
  - Delete success responses always include deleted resource identity per FR-13 delete behaviour.
  - All write operations forward user's API key unchanged (no credential substitution).
- [ ] T403: Tests — CRUD round-trip mocks, assert correct nested URL patterns (`/fabrics/{id}/vlans/{id}/subnets`), assert delete response includes identity fields, assert permission errors surfaced as-is.

**Quality Gates**:
- Subnet tools always require `fabric_id` + `vlan_id` (no flat `/subnets` endpoint)
- No server-side confirmation gate on deletes
- Auth errors from API v3 forwarded without masking

**Duration**: ~3 days

---

### Phase 5: Boot Source Tools (US6 / FR-14)

**Goal**: Implement boot source listing, sync, and deletion tools.

**Deliverables**: `tools/boot_sources.py`, `models/boot.py`.

**Tasks**:
- [ ] T501: `models/boot.py` — `BootSource(id, url, keyring_data)`, `BootSourceSelection(id, ...)`.
- [ ] T502: `tools/boot_sources.py` — Register tools: `list_boot_sources`, `trigger_boot_source_sync`, `delete_boot_source`. Sync tool returns immediately with API response (no polling). Delete success response includes deleted source ID + URL.
- [ ] T503: Tests — mock client calls, assert sync endpoint format (`/boot_sources/{id}/selections/{id}:sync`), assert no polling loop.

**Duration**: ~1.5 days

---

### Phase 6: Session Management, Auth Flow & Logging Compliance (US1 / FR-2, FR-10)

**Goal**: Verify end-to-end session lifecycle, per-session isolation, and structured log compliance.

**Tasks**:
- [ ] T601: Session isolation test — two concurrent sessions with different API keys; confirm each `MAASClient` uses only its own key.
- [ ] T602: Structured log compliance test — execute a single tool call end-to-end, capture stdout, assert exactly 6 JSON lines in correct sequence, required fields present, no raw JWT token visible.
- [ ] T603: Auth rejection test — connect without `Authorization` header → HTTP 401; invalid key format → descriptive error.
- [ ] T604: Key revocation test — mock MAAS API returning 401 → all subsequent tool calls return `authentication_error`.
- [ ] T605: Timeout test — mock MAAS with delay > `MAAS_REQUEST_TIMEOUT` → `maas_unreachable` error within timeout, no retry in logs.

**Duration**: ~2 days

---

### Phase 7: Packaging & Deployment

**Goal**: Produce a deployable Debian package and quickstart documentation.

**Deliverables**: `debian/maas-mcp-server.*`, `quickstart.md`.

**Tasks**:
- [ ] T701: `debian/maas-mcp-server.install` — install `src/maasmcpserver/` to Python package path; install `bin/maas-mcp-server` entry point.
- [ ] T702: `debian/maas-mcp-server.service` — systemd unit (`ExecStart=/usr/bin/maas-mcp-server`, `EnvironmentFile=/etc/maas/mcp-server.env`, `Restart=on-failure`).
- [ ] T703: `debian/control` — add `maas-mcp-server` package stanza with `Depends: python3-mcp (>= 1.0), python3-httpx, python3-pydantic, uvicorn`.
- [ ] T704: `quickstart.md` — install steps, env var config, connecting Claude Desktop / GPT-4, reverse proxy TLS setup.
- [ ] T705: Register `mcp` scope in `scopes.md`.

**Duration**: ~1 day

---

## Testing Strategy

### Tier 1: Unit Tests — Tool Logic (Mocked MAAS Client)

**Command**: `make test-py -k "maasmcpserver"`

- Mock `MAASClient` with `pytest-asyncio` + `unittest.mock.AsyncMock`
- Focus: tool parameters, URL construction, response mapping, error propagation
- Fast (no network, no DB)
- Location: `src/tests/maasmcpserver/tools/`

### Tier 2: Unit Tests — Infrastructure (Config, Auth, Logging)

**Command**: `make test-py -k "maasmcpserver"`

- Config loading from env vars; auth Bearer header; structlog setup via `configure_logging()`; error types
- Location: `src/tests/maasmcpserver/`

### Tier 3: Integration Tests — Full Session Lifecycle (Optional Live MAAS)

**Command**: `make test-py -k "test_integration" -m "live_maas"`

- Require `MAAS_URL` + valid `Authorization` header in environment
- Verify session open/close, tool calls, log output
- Location: `src/tests/maasmcpserver/test_integration.py`
- Marked `@pytest.mark.live_maas` — skipped in CI unless flag set

---

## Build & Deploy

```bash
# Format + Lint
make format-py        # Auto-fix Python (Ruff)
make lint-py          # Ruff + Pyright

# Test
make test-py          # All Python tests

# Run locally
MAAS_URL=http://maas.local:5240 MCP_PORT=8765 python -m maasmcpserver.main
```

---

## Dependencies & Risks

### External Dependencies

| Package | Source | Notes |
|---------|--------|-------|
| `python3-mcp` | Ubuntu archive (TC-1) | **NOT PyPI** — hard constraint |
| `python3-httpx` | Ubuntu archive | Async HTTP client |
| `python3-pydantic` | Ubuntu archive | v2.x |
| `uvicorn` | Ubuntu archive | ASGI server for streamable-http |
| `python3-structlog` | Ubuntu archive | Structured logging (reuses `maasservicelayer.logging.configure`) |
| `python3-pythonjsonlogger` | Ubuntu archive | JSON formatter used by `configure_logging()` |
| `python3-pytest-asyncio` | Dev only | Async test support |

### Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `python3-mcp` not yet in Ubuntu archive | **HIGH** | Verify availability for target Ubuntu series. If absent, raise blocker — no PyPI workaround allowed. |
| MCP SDK `streamable-http` API changes | MEDIUM | Pin SDK version; review changelog on upgrade. |
| Per-session API key via HTTP header not supported by all MCP clients | MEDIUM | Document `Authorization: Bearer <key>` requirement in quickstart. |
| TC-2 machine lifecycle tools arriving later | LOW | Deferred tools absent from listing; runtime guard in place. Easy to add when TC-2 is lifted. |

---

## Success Criteria

- ✅ All user stories P1–P3 (US1–US6) implemented and passing acceptance scenarios
- ✅ >80% code coverage (`src/maasmcpserver/`)
- ✅ All tests pass (`make test-py`)
- ✅ Linting passes (`make lint-py`)
- ✅ No stdio code path (TC-3 compliance)
- ✅ No TLS config on MCP listener (TC-4 compliance)
- ✅ `python3-mcp` from Ubuntu archive only (TC-1 compliance)
- ✅ Machine lifecycle write tools absent from tool listing (TC-2 compliance)
- ✅ Six mandatory structured log event types emitted per tool call (via `structlog`)
- ✅ Raw API key never in any log line
- ✅ Timeout returns `maas_unreachable` error ≤ `MAAS_REQUEST_TIMEOUT` seconds
- ✅ `quickstart.md` documented (≤15-minute setup goal)
- ✅ `mcp` scope registered in `scopes.md`
- ✅ Conventional Commits followed on all commits

---

**Next Step**: Run `/speckit.tasks` to generate actionable task list per user story.
