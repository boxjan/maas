# Quickstart: MAAS MCP Server

**Feature**: 001-mcp-server | **Branch**: `6689-mcp-server`

---

## Prerequisites

- Ubuntu LTS (Noble 24.04 or later)
- A running MAAS deployment with API v3 enabled
- A MAAS user account with an API key
- An MCP-compatible AI client (Claude Desktop, a custom LLM host, etc.)

---

## 1. Install

```bash
sudo apt install maas-mcp-server
```

> The package depends on `python3-mcp` from the Ubuntu archive (TC-1). No pip install required.

**Development install** (from repo root):

```bash
pip install -e ".[mcp-server]"
```

---

## 2. Configure

Create `/etc/maas/mcp-server.env` (or set environment variables directly):

```bash
# Required: URL of your MAAS API v3 endpoint
MAAS_URL=http://maas.example.com:5240

# Optional: Listening address and port (default: 0.0.0.0:8765)
MCP_HOST=0.0.0.0
MCP_PORT=8765

# Optional: Timeout (seconds) for each MAAS API v3 request (default: 30)
MAAS_REQUEST_TIMEOUT=30

# Optional: TLS verification for MAAS endpoint (default: true)
# Set to false ONLY for development with self-signed certificates
MAAS_TLS_VERIFY=true
```

> **No TLS on the MCP listener**: The MCP server always listens in plain HTTP. Use a reverse proxy
> (nginx, HAProxy) to provide TLS for MCP client connections (see Section 5).

---

## 3. Start the Server

```bash
# Systemd (production)
sudo systemctl enable --now maas-mcp-server
sudo systemctl status maas-mcp-server

# Or run directly
MAAS_URL=http://maas.example.com:5240 maas-mcp-server

# Or from source
MAAS_URL=http://maas.example.com:5240 python -m maasmcpserver.main
```

Confirm the server is running:

```bash
curl -s http://localhost:8765/health
# → {"status": "ok"}
```

View structured logs:

```bash
sudo journalctl -u maas-mcp-server -f | python3 -m json.tool
```

---

## 4. Get Your MAAS API Key

In the MAAS web UI:
1. Log in as the user whose permissions the AI assistant should operate under
2. Go to **Account** → **API Keys**
3. Copy the key — it has the format `<jwt-token>`

Or via CLI:

```bash
maas apikey --generate
```

---

## 5. Connect an MCP Client

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`~/.config/claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "maas": {
      "url": "http://localhost:8765/mcp",
      "headers": {
        "Authorization": "Bearer <jwt-token>"
      }
    }
  }
}
```

Replace `<jwt-token>` with your actual MAAS API key.

### Custom MCP Client

```python
import mcp

client = mcp.Client(
    url="http://localhost:8765/mcp",
    headers={"Authorization": "Bearer <jwt-token>"},
)
async with client:
    tools = await client.list_tools()
    result = await client.call_tool("list_machines", {"status": "Ready"})
```

---

## 6. Verify the Connection

Ask the AI assistant:

> "What MAAS instance am I connected to?"

Expected: The assistant calls `get_maas_info` and returns the deployment name and rack controllers.

> "List all machines in the Ready state."

Expected: The assistant calls `list_machines(status="Ready")` and returns the fleet list.

---

## 7. TLS Setup (Production)

The MCP server listens in plain HTTP. For production, place a TLS-terminating reverse proxy in front.

**nginx example** (`/etc/nginx/sites-available/maas-mcp`):

```nginx
server {
    listen 443 ssl;
    server_name mcp.maas.example.com;

    ssl_certificate     /etc/ssl/certs/maas-mcp.crt;
    ssl_certificate_key /etc/ssl/private/maas-mcp.key;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Required for SSE streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }
}
```

Then configure your MCP client to use `https://mcp.maas.example.com/mcp`.

---

## 8. Troubleshooting

### Server won't start

```bash
# Check MAAS_URL is reachable
curl -s "$MAAS_URL/MAAS/a/v3/machines" -H "Authorization: Bearer $YOUR_KEY"

# Check port is available
ss -tlnp | grep 8765
```

### "maas_unreachable" errors

- MAAS API v3 is not reachable from the server's network location
- `MAAS_URL` is incorrect (missing port, wrong scheme)
- `MAAS_REQUEST_TIMEOUT` too short for slow networks — increase it

### Authentication errors

- API key format must be `<jwt-token>` (a JWT token)
- The API key may have been revoked in MAAS — generate a new one
- Confirm the key has the permissions needed for the operation

### No tools visible in AI client

- The client may be caching an old tool list — reconnect
- Machine lifecycle write tools are intentionally absent (TC-2 deferral)

---

## 9. Available Tools Reference

| Tool | Description |
|------|-------------|
| `get_maas_info` | MAAS deployment name and rack controllers |
| `list_machines` | List machines with optional filters (status, zone, pool, architecture, tags, owner) |
| `get_machine` | Full hardware details for one machine |
| `list_resource_pools` | List all resource pools |
| `list_zones` | List all availability zones |
| `get_machine_power_state` | Current power state of a machine |
| `get_machine_events` | Event history for a machine (optional: `since_hours`) |
| `get_script_results` | Commissioning/hardware test script output |
| `list_fabrics` | List network fabrics |
| `get_fabric` | Details of one fabric |
| `create_fabric` | Create a new fabric |
| `update_fabric` | Update a fabric |
| `delete_fabric` | Delete a fabric |
| `list_vlans` | List VLANs in a fabric |
| `get_vlan` | Details of one VLAN |
| `create_vlan` | Create a VLAN in a fabric |
| `update_vlan` | Update a VLAN |
| `delete_vlan` | Delete a VLAN |
| `list_subnets` | List subnets under a fabric+VLAN |
| `get_subnet` | Details of one subnet |
| `create_subnet` | Create a subnet under a fabric+VLAN |
| `update_subnet` | Update a subnet |
| `delete_subnet` | Delete a subnet |
| `list_boot_sources` | List boot sources and their selections |
| `trigger_boot_source_sync` | Trigger sync for a boot source selection |
| `delete_boot_source` | Delete a boot source |

> **Not available** (TC-2): commission, deploy, release, abort, rescue, tag mutation, pool reassignment, power parameter update. These will be added when MAAS API v3 exposes the corresponding write endpoints.
