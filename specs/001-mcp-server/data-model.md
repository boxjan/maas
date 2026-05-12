# Data Model: MAAS MCP Server

**Feature**: 001-mcp-server | **Branch**: `6689-mcp-server`

> **Note**: The MCP server has **no database**. This document defines the in-memory domain models used
> as Pydantic schemas for data flowing between the MAAS API v3 responses and MCP tool outputs.
> There are no table definitions, no Alembic migrations, and no SQLAlchemy constructs.

---

## Session (In-Memory, Connection-Scoped)

Not a Pydantic model — managed by the ASGI middleware `ContextVar`.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | UUID generated at connection time; used in all log events |
| `api_key` | `str` | MAAS API key (`<jwt-token>`); never logged |
| `api_key_hash` | `str` | SHA-256 hex digest of `api_key`; used in `session.opened` log event |

**Lifetime**: Exists for the duration of the HTTP/SSE connection. Destroyed on disconnect. Never persisted.

---

## Machine Domain Models (`models/machines.py`)

### `MachineSummary`

Returned by `list_machines`. Subset of full machine record.

| Field | Type | Nullable | Source (API v3 field) |
|-------|------|----------|-----------------------|
| `system_id` | `str` | No | `system_id` |
| `hostname` | `str` | No | `hostname` |
| `status` | `str` | No | `status` (e.g., `Ready`, `Allocated`, `Deployed`) |
| `zone` | `str` | No | `zone.name` |
| `pool` | `str` | No | `pool.name` |
| `architecture` | `str` | No | `architecture` |
| `cpu_count` | `int` | No | `cpu_count` |
| `memory_mb` | `int` | No | `memory` (MiB) |
| `owner` | `str \| None` | Yes | `owner` |
| `power_state` | `str \| None` | Yes | `power_state` |
| `tags` | `list[str]` | No | `tag_names` |

### `InterfaceSummary`

Embedded in `MachineDetail.interfaces`.

| Field | Type | Nullable | Source |
|-------|------|----------|-----------------------|
| `id` | `int` | No | `id` |
| `name` | `str` | No | `name` |
| `type` | `str` | No | `type` (physical/bond/vlan/bridge) |
| `mac_address` | `str` | No | `mac_address` |
| `enabled` | `bool` | No | `enabled` |
| `vlan_id` | `int \| None` | Yes | `vlan.id` |
| `ip_addresses` | `list[str]` | No | `links[].ip_address` |

### `BlockDevice`

Embedded in `MachineDetail.block_devices`.

| Field | Type | Nullable | Source |
|-------|------|----------|-----------------------|
| `id` | `int` | No | `id` |
| `name` | `str` | No | `name` |
| `type` | `str` | No | `type` (physical/virtual) |
| `size_gb` | `float` | No | `size` (bytes → GB) |
| `model` | `str \| None` | Yes | `model` |
| `serial` | `str \| None` | Yes | `serial` |

### `MachineDetail`

Returned by `get_machine`. Extends `MachineSummary`.

| Field | Type | Nullable | Source |
|-------|------|----------|-----------------------|
| *(all MachineSummary fields)* | | | |
| `fqdn` | `str` | No | `fqdn` |
| `osystem` | `str` | No | `osystem` |
| `distro_series` | `str` | No | `distro_series` |
| `power_type` | `str` | No | `power_type` |
| `locked` | `bool` | No | `locked` |
| `description` | `str` | No | `description` |
| `error_description` | `str` | No | `error_description` |
| `storage_gb` | `float` | No | Computed from `block_devices[].size` sum |
| `interfaces` | `list[InterfaceSummary]` | No | `interfaces` |
| `block_devices` | `list[BlockDevice]` | No | `blockdevice_set` |

---

## MAAS Info Models (`models/info.py`)

### `RackController`

| Field | Type | Nullable | Source (API v3 field) |
|-------|------|----------|-----------------------|
| `hostname` | `str` | No | `hostname` |
| `rack_id` | `str` | No | `system_id` |
| `connection_state` | `str` | No | `connection_state` |

### `MAASInfo`

Returned by `get_maas_info`.

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `deployment_name` | `str` | No | From `GET /MAAS/a/v3/configurations/maas_name` → `value` field |
| `rack_controllers` | `list[RackController]` | No | From `GET /MAAS/a/v3/racks` → `items[]`; may be empty |

> **Absent fields**: `instance_uuid` and `region_controllers` are **not** included — MAAS API v3 does not expose them.

---

## Network Domain Models (`models/network.py`)

### `Fabric`

| Field | Type | Nullable | Source |
|-------|------|----------|--------|
| `id` | `int` | No | `id` |
| `name` | `str` | No | `name` |
| `description` | `str` | No | `description` |
| `class_type` | `str \| None` | Yes | `class_type` |

### `VLAN`

| Field | Type | Nullable | Source |
|-------|------|----------|--------|
| `id` | `int` | No | `id` |
| `vid` | `int` | No | `vid` (VLAN ID, 0–4094) |
| `name` | `str` | No | `name` |
| `fabric_id` | `int` | No | `fabric` → `id` |
| `mtu` | `int` | No | `mtu` |
| `dhcp_on` | `bool` | No | `dhcp_on` |
| `relay_vlan` | `int \| None` | Yes | `relay_vlan` → `id` |

### `Subnet`

| Field | Type | Nullable | Source |
|-------|------|----------|--------|
| `id` | `int` | No | `id` |
| `name` | `str` | No | `name` |
| `cidr` | `str` | No | `cidr` (e.g., `10.0.0.0/24`) |
| `fabric_id` | `int` | No | Context from URL path |
| `vlan_id` | `int` | No | `vlan` → `id` |
| `gateway_ip` | `str \| None` | Yes | `gateway_ip` |
| `dns_servers` | `list[str]` | No | `dns_servers` |
| `rdns_mode` | `int` | No | `rdns_mode` |
| `allow_proxy` | `bool` | No | `allow_proxy` |
| `allow_dns` | `bool` | No | `allow_dns` |

---

## Boot Source Models (`models/boot.py`)

### `BootSourceSelection`

| Field | Type | Nullable | Source |
|-------|------|----------|--------|
| `id` | `int` | No | `id` |
| `os` | `str` | No | `os` |
| `release` | `str` | No | `release` |
| `arches` | `list[str]` | No | `arches` |
| `subarches` | `list[str]` | No | `subarches` |
| `labels` | `list[str]` | No | `labels` |

### `BootSource`

| Field | Type | Nullable | Source |
|-------|------|----------|--------|
| `id` | `int` | No | `id` |
| `url` | `str` | No | `url` (image source URL) |
| `keyring_filename` | `str` | No | `keyring_filename` |
| `keyring_data` | `str` | No | `keyring_data` (base64) |
| `selections` | `list[BootSourceSelection]` | No | `selections` |

---

## Error Models (`errors.py`)

Not Pydantic models — Python exceptions that produce `CallToolResult(is_error=True)`.

### `MAASUnreachableError`

Raised when `httpx` times out or connection is refused.

| MCP Response Field | Value |
|-------------------|-------|
| `error_code` | `"maas_unreachable"` |
| `message` | `"MAAS API at {url_pattern} is unreachable: {failure_mode} (timeout={timeout}s)"` |

### `MCPNotImplementedError`

Raised if a TC-2-deferred tool is somehow invoked.

| MCP Response Field | Value |
|-------------------|-------|
| `error_code` | `"not_implemented"` |
| `message` | `"Machine lifecycle write operations are not available: API v3 does not currently expose write endpoints for machine lifecycle management (TC-2). Tool '{tool_name}' is deferred."` |

### `MAASAuthenticationError`

Raised when MAAS API v3 returns HTTP 401 or 403.

| MCP Response Field | Value |
|-------------------|-------|
| `error_code` | `"authentication_error"` |
| `message` | `"MAAS API rejected the request: {http_status} {detail}"` |

---

## Log Event Schemas (FR-10)

These are the JSON objects emitted to stdout per log event. Not Pydantic models — constructed in `logging.py` helper functions.

### `session.opened`
```json
{
  "event": "session.opened",
  "session_id": "<uuid>",
  "user_token_hash": "<sha256-hex>",
  "timestamp": "2026-05-12T10:00:00.123Z"
}
```

### `tool.received`
```json
{
  "event": "tool.received",
  "session_id": "<uuid>",
  "tool_name": "list_machines",
  "params": {"status": "Ready", "api_key": "[REDACTED]"},
  "timestamp": "2026-05-12T10:00:00.124Z"
}
```

### `maas.request`
```json
{
  "event": "maas.request",
  "session_id": "<uuid>",
  "method": "GET",
  "url_pattern": "/MAAS/a/v3/machines",
  "timestamp": "2026-05-12T10:00:00.125Z"
}
```

### `maas.response`
```json
{
  "event": "maas.response",
  "session_id": "<uuid>",
  "http_status": 200,
  "duration_ms": 142,
  "timestamp": "2026-05-12T10:00:00.267Z"
}
```
*On timeout/connection refused*: `"http_status": 0, "error": "maas_unreachable"`

### `tool.outcome`
```json
{
  "event": "tool.outcome",
  "session_id": "<uuid>",
  "tool_name": "list_machines",
  "status": "ok",
  "timestamp": "2026-05-12T10:00:00.268Z"
}
```
*On error*: `"status": "error", "error_code": "maas_unreachable"`

### `session.closed`
```json
{
  "event": "session.closed",
  "session_id": "<uuid>",
  "timestamp": "2026-05-12T10:00:00.300Z"
}
```
