# MCP Tool Contracts

**Feature**: 001-mcp-server | **Branch**: `6689-mcp-server`

All tools return `str` (formatted text) on success or `CallToolResult(is_error=True)` on failure.
Tool parameters are passed as keyword arguments by MCP clients.

---

## Fleet Discovery Tools (`tools/fleet.py`) — FR-4, US2

### `list_machines`

```
list_machines(
    status: str | None = None,         # e.g. "Ready", "Allocated", "Deployed"
    zone: str | None = None,           # Zone name
    pool: str | None = None,           # Resource pool name
    architecture: str | None = None,   # e.g. "amd64/generic"
    tags: str | None = None,           # Comma-separated tag names
    owner: str | None = None,          # MAAS username
    power_state: str | None = None,    # e.g. "on", "off", "unknown"
    page: int = 1,
    page_size: int = 50,
) -> str
```

MAAS API: `GET /MAAS/a/v3/machines?page={page}&size={page_size}` (filters as query params)

Success output: Markdown list of machines with hostname, status, zone, pool, architecture, CPUs, memory, owner.

---

### `get_machine`

```
get_machine(
    identifier: str,    # machine hostname or system_id
) -> str
```

MAAS API: `GET /MAAS/a/v3/machines/{system_id}` + `GET /MAAS/a/v3/machines/{system_id}/interfaces`

Success output: Full machine detail (hardware, OS, interfaces, block devices).

---

### `list_resource_pools`

```
list_resource_pools(
    page: int = 1,
    page_size: int = 100,
) -> str
```

MAAS API: `GET /MAAS/a/v3/resource_pools?page={page}&size={page_size}`

---

### `list_zones`

```
list_zones(
    page: int = 1,
    page_size: int = 100,
) -> str
```

MAAS API: `GET /MAAS/a/v3/zones?page={page}&size={page_size}`

---

### `get_machine_power_state`

```
get_machine_power_state(
    identifier: str,    # hostname or system_id
) -> str
```

MAAS API: `GET /MAAS/a/v3/machines/{system_id}` (extracts `power_state` field)

---

## Diagnostic Tools (`tools/diagnostics.py`) — FR-5, US4

### `get_machine_events`

```
get_machine_events(
    identifier: str,          # hostname or system_id
    since_hours: int = 24,    # Events from last N hours
    page: int = 1,
    page_size: int = 100,
) -> str
```

MAAS API: `GET /MAAS/a/v3/events?system_id={system_id}&page={page}&size={page_size}`

Success output: Chronological event list with type, description, timestamp.

---

### `get_script_results`

```
get_script_results(
    identifier: str,                        # hostname or system_id
    script_type: str = "commissioning",     # "commissioning" or "testing"
) -> str
```

MAAS API: `GET /MAAS/a/v3/machines/{system_id}/...` (confirm endpoint in openapi-spec.json)

Success output: Script name, exit status, stdout/stderr output.

---

## MAAS Info Tool (`tools/info.py`) — FR-12, US3

### `get_maas_info`

```
get_maas_info() -> str
```

MAAS API calls (concurrent):
1. `GET /MAAS/a/v3/configurations/maas_name` → `deployment_name`
2. `GET /MAAS/a/v3/racks` → `rack_controllers[]`

Success output: Deployment name + rack controller list (hostname, rack_id, connection_state).

Error output (timeout): `maas_unreachable` with target URL pattern and failure mode.

**Absent from response**: `instance_uuid`, `region_controllers` (not available in API v3).

---

## Network Tools (`tools/network.py`) — FR-13, US5

### Read Tools

```
list_fabrics(page: int = 1, page_size: int = 100) -> str
```
MAAS API: `GET /MAAS/a/v3/fabrics?page={page}&size={page_size}`

```
get_fabric(fabric_id: int) -> str
```
MAAS API: `GET /MAAS/a/v3/fabrics/{fabric_id}`

```
list_vlans(fabric_id: int, page: int = 1, page_size: int = 100) -> str
```
MAAS API: `GET /MAAS/a/v3/fabrics/{fabric_id}/vlans?page={page}&size={page_size}`

```
get_vlan(fabric_id: int, vlan_id: int) -> str
```
MAAS API: `GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}`

```
list_subnets(fabric_id: int, vlan_id: int, page: int = 1, page_size: int = 100) -> str
```
MAAS API: `GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets?page={page}&size={page_size}`

```
get_subnet(fabric_id: int, vlan_id: int, subnet_id: int) -> str
```
MAAS API: `GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{subnet_id}`

---

### Write Tools — Fabrics

```
create_fabric(name: str, description: str = "", class_type: str | None = None) -> str
```
MAAS API: `POST /MAAS/a/v3/fabrics`  Body: `{name, description, class_type}`

```
update_fabric(fabric_id: int, name: str | None = None, description: str | None = None) -> str
```
MAAS API: `PUT /MAAS/a/v3/fabrics/{fabric_id}`  Body: provided fields only

```
delete_fabric(fabric_id: int) -> str
```
MAAS API: `DELETE /MAAS/a/v3/fabrics/{fabric_id}`
Success output **always includes**: `"Deleted fabric '{name}' (id={fabric_id})"` — client can verify correct target.

---

### Write Tools — VLANs

```
create_vlan(
    fabric_id: int,
    vid: int,                       # VLAN ID 0–4094
    name: str = "",
    mtu: int = 1500,
    dhcp_on: bool = False,
    relay_vlan: int | None = None,  # Relay-to VLAN ID
) -> str
```
MAAS API: `POST /MAAS/a/v3/fabrics/{fabric_id}/vlans`

```
update_vlan(
    fabric_id: int,
    vlan_id: int,
    name: str | None = None,
    mtu: int | None = None,
    dhcp_on: bool | None = None,
    relay_vlan: int | None = None,
) -> str
```
MAAS API: `PUT /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}`

```
delete_vlan(fabric_id: int, vlan_id: int) -> str
```
MAAS API: `DELETE /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}`
Success output **always includes**: `"Deleted VLAN VID={vid} '{name}' from fabric '{fabric_name}' (fabric_id={fabric_id}, vlan_id={vlan_id})"`.

---

### Write Tools — Subnets

```
create_subnet(
    fabric_id: int,
    vlan_id: int,
    cidr: str,                      # e.g. "10.0.0.0/24"
    name: str = "",
    gateway_ip: str | None = None,
    dns_servers: list[str] | None = None,
    rdns_mode: int = 2,
    allow_proxy: bool = True,
    allow_dns: bool = True,
) -> str
```
MAAS API: `POST /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets`

```
update_subnet(
    fabric_id: int,
    vlan_id: int,
    subnet_id: int,
    name: str | None = None,
    gateway_ip: str | None = None,
    dns_servers: list[str] | None = None,
) -> str
```
MAAS API: `PUT /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{subnet_id}`

```
delete_subnet(fabric_id: int, vlan_id: int, subnet_id: int) -> str
```
MAAS API: `DELETE /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{subnet_id}`
Success output **always includes**: `"Deleted subnet '{cidr}' ('{name}') from VLAN VID={vid} in fabric '{fabric_name}' (fabric_id={fabric_id}, vlan_id={vlan_id}, subnet_id={subnet_id})"`.

---

## Boot Source Tools (`tools/boot_sources.py`) — FR-14, US6

### `list_boot_sources`

```
list_boot_sources(page: int = 1, page_size: int = 100) -> str
```
MAAS API: `GET /MAAS/a/v3/boot_sources?page={page}&size={page_size}`

Success output: Each boot source's ID, URL, keyring info, and selections list.

---

### `trigger_boot_source_sync`

```
trigger_boot_source_sync(
    boot_source_id: int,
    selection_id: int,
) -> str
```
MAAS API: `POST /MAAS/a/v3/boot_sources/{boot_source_id}/selections/{selection_id}:sync`

Success output: API v3 response (accepted/queued status). **No polling** — long-running sync completes asynchronously on the MAAS side.

> The tool accepts only `boot_source_id` and `selection_id`. It does not accept source URL, image type,
> credentials, or any parameters that would configure image sources. Those are managed in MAAS directly.

---

### `delete_boot_source`

```
delete_boot_source(boot_source_id: int) -> str
```
MAAS API: `DELETE /MAAS/a/v3/boot_sources/{boot_source_id}`

Success output **always includes**: `"Deleted boot source id={boot_source_id} url='{url}'"` — client can verify correct source was removed.

---

## Error Contracts

All tools can return these errors via `CallToolResult(is_error=True)`:

| `error_code` | Trigger |
|---|---|
| `maas_unreachable` | Timeout or connection refused from MAAS API v3 |
| `authentication_error` | MAAS API v3 returns HTTP 401 or 403 |
| `not_implemented` | Machine lifecycle write tool called while TC-2 is in force |
| `maas_error` | MAAS API v3 returns HTTP 4xx/5xx (other than auth errors) |

### `maas_unreachable` format
```json
{
  "is_error": true,
  "error_code": "maas_unreachable",
  "content": [{"type": "text", "text": "MAAS API at /MAAS/a/v3/machines is unreachable: connection_timeout (timeout=30s)"}]
}
```

### `not_implemented` format
```json
{
  "is_error": true,
  "error_code": "not_implemented",
  "content": [{"type": "text", "text": "Machine lifecycle write operations are not available: API v3 does not currently expose write endpoints for machine lifecycle management (TC-2). Tool 'deploy_machine' is deferred."}]
}
```
