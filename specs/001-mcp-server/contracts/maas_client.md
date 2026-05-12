# MAAS HTTP Client Contract

**Feature**: 001-mcp-server | **Branch**: `6689-mcp-server`

Defines the `MAASClient` interface used by all tool modules.

---

## `MAASClient` Interface (`client.py`)

```python
class MAASClient:
    def __init__(
        self,
        base_url: str,           # e.g. "http://maas.example.com:5240"
        api_key: str,            # "<jwt-token>"
        timeout: int = 30,       # MAAS_REQUEST_TIMEOUT
        tls_verify: bool = True, # MAAS_TLS_VERIFY
    ): ...

    async def get(self, path: str, params: dict | None = None) -> dict: ...
    async def post(self, path: str, body: dict | None = None) -> dict: ...
    async def put(self, path: str, body: dict | None = None) -> dict: ...
    async def delete(self, path: str) -> dict: ...
```

### Behaviour

- **OAuth header**: Every request has `Authorization: Bearer <jwt-token>` header computed from `api_key`
- **Timeout**: `httpx.Timeout(timeout)` applied unconditionally to every request
- **On timeout**: Raises `MAASUnreachableError(url_pattern, "connection_timeout")`
- **On connection refused**: Raises `MAASUnreachableError(url_pattern, "connection_refused")`
- **On HTTP 4xx/5xx**: Raises `MAASAPIError(http_status, response_body)` (caller maps to appropriate MCP error)
- **No retries**: Single attempt; any retry is the AI client's or operator's responsibility
- **Log events emitted**: `maas.request` (before call) + `maas.response` (after call, including on error)

### `url_pattern` convention

`url_pattern` in log events and error messages uses path template form with `{id}` placeholders — never the resolved URL with actual IDs or query strings. Examples:
- `GET /MAAS/a/v3/machines` (not `/MAAS/a/v3/machines?page=1&size=50`)
- `GET /MAAS/a/v3/machines/{system_id}` (not `/MAAS/a/v3/machines/abc123`)
- `POST /MAAS/a/v3/fabrics/{fabric_id}/vlans`

---

## MAAS API v3 Endpoints Used

| Tool(s) | Method | Endpoint |
|---------|--------|----------|
| `list_machines` | GET | `/MAAS/a/v3/machines` |
| `get_machine` | GET | `/MAAS/a/v3/machines/{system_id}` |
| `get_machine` (interfaces) | GET | `/MAAS/a/v3/machines/{node_id}/interfaces` |
| `get_machine_power_state` | GET | `/MAAS/a/v3/machines/{system_id}` |
| `list_resource_pools` | GET | `/MAAS/a/v3/resource_pools` |
| `list_zones` | GET | `/MAAS/a/v3/zones` |
| `get_machine_events` | GET | `/MAAS/a/v3/events` |
| `get_script_results` | GET | `/MAAS/a/v3/machines/{system_id}/...` |
| `get_maas_info` (name) | GET | `/MAAS/a/v3/configurations/maas_name` |
| `get_maas_info` (racks) | GET | `/MAAS/a/v3/racks` |
| `list_fabrics` | GET | `/MAAS/a/v3/fabrics` |
| `get_fabric` | GET | `/MAAS/a/v3/fabrics/{fabric_id}` |
| `create_fabric` | POST | `/MAAS/a/v3/fabrics` |
| `update_fabric` | PUT | `/MAAS/a/v3/fabrics/{fabric_id}` |
| `delete_fabric` | DELETE | `/MAAS/a/v3/fabrics/{fabric_id}` |
| `list_vlans` | GET | `/MAAS/a/v3/fabrics/{fabric_id}/vlans` |
| `get_vlan` | GET | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}` |
| `create_vlan` | POST | `/MAAS/a/v3/fabrics/{fabric_id}/vlans` |
| `update_vlan` | PUT | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}` |
| `delete_vlan` | DELETE | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}` |
| `list_subnets` | GET | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets` |
| `get_subnet` | GET | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{subnet_id}` |
| `create_subnet` | POST | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets` |
| `update_subnet` | PUT | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{subnet_id}` |
| `delete_subnet` | DELETE | `/MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{subnet_id}` |
| `list_boot_sources` | GET | `/MAAS/a/v3/boot_sources` |
| `trigger_boot_source_sync` | POST | `/MAAS/a/v3/boot_sources/{boot_source_id}/selections/{selection_id}:sync` |
| `delete_boot_source` | DELETE | `/MAAS/a/v3/boot_sources/{boot_source_id}` |
