# Configuration Contract

**Feature**: 001-mcp-server | **Branch**: `6689-mcp-server`

---

## Environment Variables (`config.py` — `MaasServerConfig`)

All configuration is via environment variables (or `.env` file for development).
No source code editing required.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `MAAS_URL` | `str` | — | **Yes** | Base URL of the MAAS API v3 endpoint (e.g. `http://maas.example.com:5240`) |
| `MAAS_REQUEST_TIMEOUT` | `int` | `30` | No | Seconds to wait for each MAAS API v3 HTTP response. Enforced unconditionally; no overrides. |
| `MAAS_TLS_VERIFY` | `bool` | `true` | No | Verify TLS certificate for MAAS endpoint. Set `false` only in development with self-signed certs. |
| `MCP_HOST` | `str` | `0.0.0.0` | No | Address the MCP HTTP server binds to. |
| `MCP_PORT` | `int` | `8765` | No | Port the MCP HTTP server listens on. |
| `LOG_LEVEL` | `str` | `INFO` | No | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

### Deliberately absent variables

| Variable | Reason absent |
|----------|--------------|
| `MAAS_API_KEY` / `MAAS_MCP_API_KEY` | TC-1 violation — app-level key would create single-user server. API key is per-session via HTTP `Authorization` header. |
| `MAAS_MCP_TRANSPORT` | TC-3 violation — transport is always `streamable-http`; not configurable. |
| `TLS_CERT`, `TLS_KEY`, `TLS_CA` | TC-4 violation — MCP listener never provides native TLS; operator uses reverse proxy. |
| `DATABASE_URL` / `DB_DSN` | No database — MCP server is stateless; all data from MAAS API v3. |

---

## Pydantic Settings Schema

```python
class MaasServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    maas_url: str                        # Required
    maas_request_timeout: int = 30
    maas_tls_verify: bool = True
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8765
    log_level: str = "INFO"
```

---

## `systemd` Environment File Template

`/etc/maas/mcp-server.env`:

```bash
# REQUIRED
MAAS_URL=http://maas.example.com:5240

# OPTIONAL
MCP_HOST=0.0.0.0
MCP_PORT=8765
MAAS_REQUEST_TIMEOUT=30
MAAS_TLS_VERIFY=true
LOG_LEVEL=INFO
```
