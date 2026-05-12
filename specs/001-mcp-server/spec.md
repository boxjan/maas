# Feature Specification: MAAS MCP Server

**Feature Branch**: `6689-mcp-server`
**Created**: 2025-07-22
**Status**: Draft

## Overview

An optional, independently deployable Model Context Protocol (MCP) server that acts as a modular gateway between Large Language Models (LLMs) and MAAS bare-metal infrastructure. The server communicates exclusively with the MAAS HTTP API v3 and implements a transparent token-delegation authentication model, ensuring that every operation is governed by the requesting user's own MAAS permissions without introducing centralized service accounts.

> **Scope Constraint (TC-2 — Partially Revised)**: API v3 supports **read (GET) operations** and **select write operations**. Write operations for **network management** (fabrics, VLANs, subnets nested under VLANs) and **boot-source management** are available in API v3 and are **in scope** for this release (FR-13, FR-14). **Machine lifecycle write operations** — commission, release, abort, rescue, and deploy — are **not available** in API v3 at this time and remain deferred (TC-2). Additionally, the MCP server exposes a `get_maas_info` tool to allow clients to identify the MAAS deployment they are interacting with (FR-12).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Session Initialization via API Key Delegation (Priority: P1)

A MAAS administrator wants to connect their AI assistant (such as Claude, GPT-4, or a locally hosted model) to their MAAS environment. They start the MCP server and configure their AI client to use it. When they initiate a conversation, they provide their personal MAAS API key so that every action the AI takes on their behalf is subject to their own role-based access controls.

**Why this priority**: This is the foundational capability. All other user stories depend on a correctly authenticated, permission-scoped session being established. Without this, no MAAS resource is accessible.

**Independent Test**: Can be fully tested by starting the MCP server, pointing an MCP-compatible client at it, supplying a valid MAAS API key, and confirming the server reports a successful, permission-scoped session — without querying any MAAS resources.

**Acceptance Scenarios**:

1. **Given** an MCP-compatible AI client is connected to the MCP server, **When** the user provides a valid MAAS API key, **Then** the server establishes an authenticated session scoped to that user's permissions and confirms readiness.
2. **Given** an active session, **When** the underlying MAAS API key is revoked or expired, **Then** subsequent tool calls fail with a clear authentication error and the session is invalidated.
3. **Given** an MCP-compatible AI client is connected, **When** the user provides an invalid or malformed API key, **Then** the server rejects the session with a descriptive error message and no MAAS resources are queried.
4. **Given** multiple simultaneous users, **When** each provides their own MAAS API key, **Then** each session is isolated and operates under that user's distinct MAAS permissions.

---

### User Story 2 - Fleet Discovery via Natural Language (Priority: P2)

A MAAS administrator managing hundreds of machines wants to quickly locate resources without memorising API query syntax. They ask their AI assistant natural language questions such as "List all machines in rack A that are currently ready for deployment" or "How many machines are allocated to the staging pool?" The MCP server translates these requests into precise MAAS API v3 queries and returns structured, readable results.

**Why this priority**: Fleet visibility is the most common read-only task for operators and delivers immediate, high-frequency value with zero write risk. It establishes the pattern for all subsequent tool interactions.

**Independent Test**: Can be fully tested by issuing natural language fleet queries through an MCP client and confirming that results accurately reflect the current MAAS inventory as returned by API v3 — no provisioning or state changes required.

**Acceptance Scenarios**:

1. **Given** an authenticated session with a user who has machine-view permissions, **When** the user asks to list machines by status, pool, or rack, **Then** the MCP server returns an accurate, paginated list matching the API v3 response.
2. **Given** an authenticated session, **When** the user queries machine details (hardware specs, power state, tags, owner), **Then** the server returns the full machine record retrieved from API v3.
3. **Given** a user with restricted view permissions, **When** they query machines outside their permission scope, **Then** the server returns only the resources they are authorised to see — matching the API v3 access control behaviour exactly.
4. **Given** a fleet query that returns zero results, **When** the AI client receives the response, **Then** the server communicates an empty result clearly rather than an error.

---

### User Story 3 - MAAS Instance Identification (Priority: P2)

A MAAS administrator operating in an environment with multiple MAAS clusters wants to confirm which deployment their AI assistant is currently connected to before issuing queries or write operations. They ask "What MAAS instance am I connected to?" and receive the cluster/deployment name and a list of rack controllers — all sourced from API v3 — without leaving the chat interface.

> **API v3 Constraint (FR-12)**: MAAS API v3 does **not** expose an instance UUID endpoint or a region controller list endpoint. `get_maas_info` therefore returns `deployment_name` (from `GET /configurations/maas_name`) and `rack_controllers` (from `GET /racks`) only. There is no `instance_uuid` or `region_controllers` field available via v3.

**Why this priority**: Operators need a reliable way to identify the target MAAS deployment before acting on it. Misidentifying the environment (e.g., staging vs. production) can lead to serious operational mistakes. Exposing this information as a first-class tool is low-cost and high-value.

**Independent Test**: Can be fully tested by invoking the `get_maas_info` tool through an authenticated MCP session and confirming the response contains a non-empty `deployment_name` and a `rack_controllers` list — matched against the known target MAAS instance. Note: no UUID or region controller fields are expected (not exposed by API v3).

**Acceptance Scenarios**:

1. **Given** an authenticated MCP session, **When** the user invokes `get_maas_info`, **Then** the server returns the MAAS deployment name (sourced via `GET /MAAS/a/v3/configurations/maas_name`) and the list of rack controllers (sourced via `GET /MAAS/a/v3/racks`) retrieved from API v3. No instance UUID or region controller list is included, as these are not exposed by API v3.
2. **Given** an authenticated session, **When** `get_maas_info` is invoked and the MAAS API v3 is reachable, **Then** the response includes at minimum: `deployment_name` (string, from `GET /configurations/maas_name`) and `rack_controllers` (list of objects each with hostname, rack_id, and connection state, from `GET /racks`; list may be empty if no racks are registered). Fields `instance_uuid` and `region_controllers` are **not** present in the response (not available via API v3).
3. **Given** a user without administrator-level permissions, **When** they invoke `get_maas_info`, **Then** the server returns only the information accessible via API v3 under their permission level, or surfaces an authorisation error consistent with the API v3 permission model.
4. **Given** that the MAAS API v3 endpoint is unreachable, **When** `get_maas_info` is invoked, **Then** the server returns a structured `maas_unreachable` error within the configured `MAAS_REQUEST_TIMEOUT` interval (FR-11).

---

### User Story 4 - Hardware Troubleshooting Assistance (Priority: P3)

An operator investigating an unexpected machine failure wants to gather diagnostic information quickly. Rather than navigating multiple MAAS UI screens or running several API calls manually, they ask their AI assistant: "What events have been recorded for machine X in the last 24 hours?" or "Show me the commissioning log for node Y." The MCP server fetches the relevant logs, events, and hardware test results via API v3 and presents them in a consolidated, readable format.

**Why this priority**: Troubleshooting is a high-value, time-sensitive workflow. Consolidating multi-call diagnostic data into a single natural language interaction meaningfully reduces incident response time.

**Independent Test**: Can be fully tested by requesting event logs and commissioning output for a specific machine through the MCP client and confirming the data matches the direct API v3 responses — no provisioning changes required.

**Acceptance Scenarios**:

1. **Given** an authenticated session, **When** the user requests the event history for a specific machine, **Then** the MCP server retrieves and returns the events from API v3 in chronological order.
2. **Given** an authenticated session, **When** the user requests commissioning or testing script output for a machine, **Then** the server retrieves and returns the script results from API v3.
3. **Given** an authenticated session, **When** the user asks for hardware details (CPU, memory, storage, network interfaces) of a specific machine, **Then** the server returns the full hardware inventory from API v3.
4. **Given** a user without log-view permissions for a particular machine, **When** they request diagnostic information, **Then** the server returns an authorisation error consistent with the API v3 permission model.

---

### User Story 5 - Network Fabric, VLAN & Subnet Management (Priority: P3)

A network administrator managing the fabric topology of their MAAS environment wants to query and configure network fabrics, VLANs, and subnets through their AI assistant. They ask "List all VLANs in fabric 'prod'", "Create a new VLAN with VID 100 in the storage fabric", or "Add subnet 10.10.20.0/24 to VLAN 100 in fabric 'prod'." The MCP server translates these natural language requests into API v3 fabric, VLAN, and subnet operations and returns structured results.

> **API v3 Subnet Nesting**: In API v3, subnets are **nested under VLANs**, not a flat top-level collection. All subnet operations require both `fabric_id` and `vlan_id` context: e.g., `GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets`. IP ranges, reserved IPs, and static routes are further nested under subnets as sub-resources.

**Why this priority**: Network topology is a prerequisite for machine networking configuration. Fabric, VLAN, and subnet management write operations are available in API v3 (unlike machine lifecycle operations), so deferring them would arbitrarily restrict a functional capability. This story follows troubleshooting (P3) in priority because network changes carry side effects that require careful context.

**Independent Test**: Can be fully tested by issuing fabric/VLAN/subnet list queries and create-then-delete cycles (VLAN and subnet) through an MCP client against a live MAAS API v3, confirming responses match direct API v3 calls and that the resources appear and are removed from the MAAS inventory.

**Acceptance Scenarios**:

1. **Given** an authenticated session with network-view permissions, **When** the user asks to list fabrics, VLANs, or subnets, **Then** the MCP server returns the fabric and VLAN inventory from `GET /MAAS/a/v3/fabrics` and `GET /MAAS/a/v3/fabrics/{fabric_id}/vlans`, and subnets nested under the appropriate VLAN via `GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets`.
2. **Given** an authenticated session with network-management permissions, **When** the user instructs the server to create a VLAN (specifying VID and target fabric), **Then** the MCP server submits a create request to `POST /MAAS/a/v3/fabrics/{fabric_id}/vlans` and confirms the new VLAN's identity and attributes.
3. **Given** an authenticated session with network-management permissions, **When** the user instructs the server to create a subnet (specifying fabric ID, VLAN ID, CIDR, and optional gateway/DNS), **Then** the MCP server submits a create request to `POST /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets` and confirms the new subnet's identity and attributes. Note: subnets are nested under VLANs in API v3 — a flat `/subnets/` endpoint does not exist.
4. **Given** an authenticated session with network-management permissions, **When** the user instructs the server to update or delete a fabric, VLAN, or subnet, **Then** the MCP server submits the appropriate write request to API v3 immediately (no server-side confirmation gate); for delete operations the success response includes the deleted resource's identity (fabric name for `delete_fabric`; VLAN VID + name for `delete_vlan`; subnet CIDR + name for `delete_subnet`, including fabric + VLAN context) so the AI client can confirm the correct target was acted on.
5. **Given** a user without network-management permissions, **When** they attempt a fabric, VLAN, or subnet write operation, **Then** the server surfaces the API v3 authorisation error without retrying or escalating credentials.
6. **Given** a deletion request that references a non-existent VLAN or subnet, **When** API v3 returns a not-found response, **Then** the MCP server surfaces a descriptive error to the user rather than silently failing.

---

### User Story 6 - Boot Source Management (Priority: P3)

A MAAS administrator needs to manage boot sources and their image selections — kernel images, initrd files, and other PXE boot resources — without navigating the MAAS UI. They instruct their AI assistant to list current boot sources, trigger a sync for a boot source selection, or remove an outdated boot source. The MCP server maps these requests to API v3 `/boot_sources/` endpoints and reports results.

**Why this priority**: Boot asset integrity is required for commissioning and deployment pipelines. The ability to query and manage boot sources via API v3 is available and fills a gap in day-to-day MAAS operations. It ranks alongside Network Management (P3) because it similarly carries limited blast radius relative to machine lifecycle operations.

**Independent Test**: Can be fully tested by listing boot sources (`GET /MAAS/a/v3/boot_sources`), triggering a sync for a boot source selection (`POST /MAAS/a/v3/boot_sources/{id}/selections/{id}:sync`), and confirming the updated selection appears in the subsequent listing — all via MCP client calls against a running MAAS API v3, without requiring any machine provisioning.

**Acceptance Scenarios**:

1. **Given** an authenticated session, **When** the user asks to list current boot sources, **Then** the MCP server returns the full boot source inventory from `GET /MAAS/a/v3/boot_sources` including each source's URL, key-ring data, and associated selections.
2. **Given** an authenticated session with boot-source management permissions, **When** the user instructs the server to trigger a sync for a boot source selection, **Then** the MCP server submits a sync request to `POST /MAAS/a/v3/boot_sources/{boot_source_id}/selections/{selection_id}:sync` and reports the outcome.
3. **Given** an authenticated session with boot-source management permissions, **When** the user instructs deletion of a specific boot source, **Then** the MCP server submits the delete request to `DELETE /MAAS/a/v3/boot_sources/{boot_source_id}` immediately (no server-side confirmation gate); the success response includes the deleted source's ID and URL so the AI client can confirm the correct source was removed.
4. **Given** a user without boot-source management permissions, **When** they attempt a write operation on boot sources, **Then** the server surfaces the API v3 authorisation error without retrying or escalating credentials.

---

### User Story 7 - Automated Node Provisioning via Natural Language (Priority: P4) ⛔ FULLY DEFERRED

> **Hard Constraint (TC-2)**: **Machine lifecycle write operations** — commission, release, abort, rescue, and deploy — are **not available** in API v3 at this time. Because the MCP server communicates exclusively via API v3 (FR-3 / TC-2), **no machine provisioning operations can be supported**. This entire user story is deferred until API v3 exposes write endpoints for machine lifecycle management. Note: other API v3 write domains (network management via FR-13, boot-source management via FR-14) are available and covered by User Stories 7 and 8.

~~A MAAS administrator needs to provision a batch of machines for a new workload. Instead of scripting API calls or navigating the UI for each machine, they instruct their AI assistant: "Commission the three ready machines in pool 'compute'." The MCP server decomposes the request into the required sequence of API v3 operations, executes them with the user's own credentials, and reports progress at each step.~~

**Why this priority**: Automated provisioning is the highest-impact write capability. It must be built on the solid foundation of discovery (P2) and authentication (P1), and carries the greatest security implications — hence it comes after read-only capabilities are proven.

**Independent Test**: Cannot be tested until API v3 exposes write endpoints for machine lifecycle operations (commission, release, abort, rescue, deploy).

**Acceptance Scenarios**:

1. **[DEFERRED — API v3 write operations unavailable]** ~~Given an authenticated session with deploy permissions, When the user instructs the server to deploy an OS on a ready machine, Then the MCP server submits the correct API v3 deploy request and confirms the machine has entered the deploying state.~~
2. **[DEFERRED — API v3 write operations unavailable]** ~~Given an authenticated session, When the user instructs a provisioning action that the user's MAAS role does not permit, Then the MCP server returns a clear permission-denied message without partially executing the operation.~~
3. **[DEFERRED — API v3 write operations unavailable]** ~~Given an authenticated session with commission permissions, When the user instructs commissioning of one or more machines, Then the server submits the commissioning request via API v3 and reports the resulting machine state.~~
4. **[DEFERRED — API v3 write operations unavailable]** ~~Given a provisioning instruction that references a non-existent machine or pool, When the API v3 returns a not-found response, Then the MCP server surfaces a descriptive error to the user rather than silently failing.~~
5. **[DEFERRED — API v3 write operations unavailable]** ~~Given an in-progress commissioning operation, When the user requests a status update, Then the MCP server queries the current machine state via API v3 and reports it accurately.~~

---

### User Story 8 - Resource Lifecycle Management (Priority: P5) ⛔ FULLY DEFERRED

> **Hard Constraint (TC-2)**: **Machine lifecycle day-2 write operations** — tag mutations, pool reassignment, power parameter updates, and machine release — are **not available** in API v3 at this time. Because the MCP server communicates exclusively via API v3 (FR-3 / TC-2), **no machine lifecycle mutation operations can be supported**. This entire user story is deferred until API v3 exposes the corresponding write endpoints. Note: network management (fabrics, VLANs) write operations are available in API v3 and are covered by User Story 7 (FR-13).

~~An administrator managing the full lifecycle of machines in a large-scale environment wants to perform day-2 operations — tagging machines, updating power parameters, reassigning machines to pools, or releasing deployed nodes — through natural language. The MCP server maps these intents to the appropriate API v3 write operations and applies them under the user's credentials.~~

**Why this priority**: Day-2 lifecycle operations extend the utility of the MCP server beyond initial provisioning and are critical for ongoing fleet management, but they represent a wider attack surface and are lower urgency than core discovery and deployment.

**Independent Test**: Cannot be tested until API v3 exposes write endpoints for tag mutation, pool reassignment, power parameter updates, and machine release.

**Acceptance Scenarios**:

1. **[DEFERRED — API v3 write operations unavailable]** ~~Given an authenticated session with appropriate permissions, When the user asks to add or remove a tag from one or more machines, Then the MCP server updates the tags via API v3 and confirms the change.~~
2. **[DEFERRED — API v3 write operations unavailable]** ~~Given an authenticated session with appropriate permissions, When the user instructs releasing a deployed machine, Then the MCP server submits a release request via API v3 and confirms the machine transitions to the ready state.~~
3. **[DEFERRED — API v3 write operations unavailable]** ~~Given an authenticated session with pool-management permissions, When the user reassigns a machine to a different resource pool, Then the MCP server submits the update via API v3 and reports the new pool assignment.~~

---

## Functional Requirements

### FR-1: MCP Protocol Compliance

- The server implements the Model Context Protocol specification, exposing MAAS capabilities as MCP **tools** (for actions) and MCP **resources** (for read-only data).
- The server responds correctly to MCP protocol handshake, tool-listing, resource-listing, and invocation messages.
- The server operates as an MCP server that AI clients (LLM hosts) connect to; it does not initiate connections to AI clients.
- **Transport**: The server uses **HTTP/SSE (Server-Sent Events) exclusively** as its MCP transport mechanism. stdio transport is **not supported** and must not be implemented. See TC-3.

### FR-2: Token-Delegation Authentication

- The server accepts MAAS API keys provided by the user at session initialisation time.
- The server never stores MAAS API keys on disk; keys are held only in the active session context.
- Every request forwarded to MAAS API v3 includes the user's API key, with no credential substitution or elevation.
- The server supports simultaneous sessions for different users, each isolated with their own credentials and permission scope.
- When a user's API key is invalid or revoked, all tool calls within that session return an authentication error.

### FR-3: Exclusive API v3 Communication

- All MAAS data access and mutation operations go through the MAAS HTTP API v3 exclusively.
- The server does not connect to the MAAS database directly, does not use the MAAS v2 (Django) API, and does not invoke internal MAAS RPC channels.
- The server treats the MAAS API v3 as its sole source of truth for all resource state.

### FR-4: Fleet Discovery Tools

- The server exposes tools to list and filter machines by status, resource pool, availability zone, tags, owner, architecture, and power state.
- The server exposes tools to retrieve full machine detail records including hardware specifications, network interfaces, storage devices, and block devices.
- The server exposes tools to list resource pools, availability zones, tags, and subnets. Note: subnets require fabric + VLAN context in API v3 (nested path); see FR-13.
- All list operations support pagination so that large fleets do not produce truncated results.

### FR-5: Diagnostic Tools

- The server exposes tools to retrieve machine event logs, filtered by time range.
- The server exposes tools to retrieve commissioning script output and hardware test results.
- The server exposes tools to retrieve the current power state of a machine.

### FR-6: Machine Lifecycle Provisioning Tools *(Deferred — TC-2: machine lifecycle writes unavailable)*

> **Hard Constraint**: API v3 **does not** expose write endpoints for machine lifecycle management at this time. **All tools in this requirement are deferred** until API v3 exposes those endpoints. Note: write operations for network management (fabrics, VLANs) and boot-source management are available in API v3 and are covered by FR-13 and FR-14 respectively.

- **[DEFERRED]** Commission, release, abort, and rescue machine tools — blocked by API v3 machine lifecycle write unavailability (TC-2).
- **[DEFERRED]** Deploy OS image tools — blocked by API v3 machine lifecycle write unavailability (TC-2).
- **[DEFERRED]** Deployment parameter tools (OS image, kernel options, user data) — blocked by API v3 machine lifecycle write unavailability (TC-2).
- **[DEFERRED]** Tag mutation tools (add/remove tags on machines) — blocked by API v3 machine lifecycle write unavailability (TC-2).
- **[DEFERRED]** Resource pool reassignment tools — blocked by API v3 machine lifecycle write unavailability (TC-2).
- **[DEFERRED]** Ownership update tools — blocked by API v3 machine lifecycle write unavailability (TC-2).
- **[DEFERRED]** Power parameter update tools — blocked by API v3 machine lifecycle write unavailability (TC-2).

No machine lifecycle write tools will be implemented until TC-2 is lifted. While TC-2 is in force:

- Machine lifecycle write-operation tools are **not included in the MCP tool-listing response**; AI clients querying available tools will not discover any machine lifecycle write tools (network management and boot-source tools from FR-13/FR-14 are included normally).
- If a machine lifecycle write-operation tool invocation is received despite TC-2 being in force, the server **must** immediately return a structured MCP `not-implemented` error with a human-readable message identifying the tool name and stating that machine lifecycle write operations are unavailable pending API v3 write endpoint availability. No MAAS API v3 request is made and no partial state change occurs.

### FR-7: Permission Transparency

- The server surfaces MAAS API v3 permission errors directly to the AI client without masking or retrying with elevated credentials.
- The server does not cache stale permission decisions; every API v3 call reflects the current state of the user's MAAS permissions.
- **Machine lifecycle write operation pre-confirmation is deferred**: The requirement to inform the AI client before executing machine lifecycle write operations (commission, release, tag changes, etc.) is deferred alongside FR-6 until API v3 exposes machine lifecycle write endpoints (TC-2). Pre-confirmation behaviour for network management (FR-13) and boot-source (FR-14) destructive (delete) operations is resolved: the MCP server applies no server-side confirmation gate; delete operations execute immediately, and the success response always includes the deleted resource's identity so the AI client can verify the correct target was acted on. Confirmation responsibility for destructive operations lies with the AI client, not the MCP server.

### FR-8: Operational Independence

- The MCP server runs as a standalone process separate from all MAAS controller services.
- Starting, stopping, or restarting the MCP server has no effect on MAAS controller operation.
- The MCP server requires only network access to the MAAS API v3 endpoint; no shared filesystem, database connection, or MAAS internal socket is needed.

### FR-9: Configuration

- The server is configurable with the target MAAS API v3 base URL.
- TLS certificate verification for the MAAS API v3 endpoint is enabled by default, with an opt-out for self-signed certificates in development environments.
- The server listens on a configurable network address and port; it **always** runs as a network service (HTTP/SSE). stdio transport is **not supported** and cannot be activated via configuration. See TC-3.
- All configuration is provided via environment variables or a configuration file; no configuration requires editing source code.
- **No native TLS configuration on the MCP listener**: The server never provides a TLS configuration option (`TLS_CERT`, `TLS_KEY`, `TLS_CA`, or any equivalent) for its own HTTP/SSE listener. TLS termination is the operator's responsibility via a reverse proxy. See TC-4.
- `MAAS_REQUEST_TIMEOUT` (integer seconds, default: `30`): Maximum time the server will wait for any single MAAS API v3 HTTP response. On expiry the outstanding request is abandoned immediately; no retry is attempted and the error is propagated to the AI client as a structured MCP `maas_unreachable` error. See FR-11.

### FR-10: Observability — Structured Logging

- The server writes all audit and diagnostic log entries to **stdout** as newline-delimited JSON (NDJSON): one JSON object per line. No log entries are written to a dedicated log file, syslog, or stderr by default; stdout is the sole log sink so that the process supervisor or container runtime can route and retain logs.
- The following six event types are **mandatory** — a compliant deployment must produce a parseable JSON line for each:

  | Event type | Required fields |
  |---|---|
  | `session.opened` | `event`, `session_id`, `user_token_hash` (SHA-256 hex digest of the raw API key — never the raw key itself), `timestamp` |
  | `tool.received` | `event`, `session_id`, `tool_name`, `params` (sanitised: any credential-like values redacted to `"[REDACTED]"`), `timestamp` |
  | `maas.request` | `event`, `session_id`, `method`, `url_pattern` (path template form, e.g. `/MAAS/a/v3/machines/{id}` — no credential-bearing query strings), `timestamp` |
  | `maas.response` | `event`, `session_id`, `http_status`, `duration_ms`, `timestamp` |
  | `tool.outcome` | `event`, `session_id`, `tool_name`, `status` (`"ok"` or `"error"`), `error_code` (present and non-null only when `status` is `"error"`), `timestamp` |
  | `session.closed` | `event`, `session_id`, `timestamp` |

- `user_token_hash` **must** be the SHA-256 hex digest of the raw API key. The raw API key must never appear in any log field or log line under any circumstances.
- `url_pattern` must use the path template form rather than the fully resolved URL to avoid leaking machine identifiers or query parameters that could contain credentials.
- All `timestamp` values must be ISO 8601 UTC (e.g., `2026-05-12T10:00:00.123Z`).
- Additional fields beyond the mandatory minimum are permitted in any event object.
- Log output must not interleave partial JSON objects; each line must be a complete, self-contained JSON object terminated by a newline character (`\n`).

### FR-11: MAAS Reachability & Timeout Handling

- Every individual MAAS API v3 HTTP request carries a per-request timeout controlled by `MAAS_REQUEST_TIMEOUT` (default: 30 seconds). See FR-9.
- On timeout expiry **or** connection refused (MAAS unreachable), the server **immediately** returns a structured MCP error to the AI client with `error_code: "maas_unreachable"` and a human-readable description identifying the target URL pattern and the failure mode (timeout vs. connection refused).
- **No retries**: The server must not retry a timed-out or refused MAAS request. The single attempt is the final attempt; any retry logic is the responsibility of the AI client or the operator re-issuing the tool call.
- The server must never block indefinitely awaiting a MAAS response; the configured timeout is applied unconditionally to every outbound MAAS HTTP request with no override path.
- Session lifetime is **connection-scoped**: a session remains active for exactly as long as the underlying MCP client HTTP/SSE connection is open. The server performs no server-side idle expiry, heartbeat-based eviction, or keep-alive extension. When the client disconnects the session is torn down immediately and any in-flight MAAS request is cancelled.
- The `maas.response` log event (FR-10) must be emitted on timeout and connection-refused outcomes, with `http_status` set to `0` (or the sentinel value `null`) and an additional `error` field carrying `"maas_unreachable"`.

---

### FR-12: MAAS Instance Identification

- The server exposes a `get_maas_info` MCP tool (callable action) that returns identifying information about the connected MAAS deployment.
- The tool response **must** include at minimum:
  - `deployment_name` (string): the human-readable cluster or deployment name configured in MAAS, sourced from `GET /MAAS/a/v3/configurations/maas_name`.
  - `rack_controllers` (list of objects): each entry includes at minimum the rack controller's hostname, rack ID, and connection state, sourced from `GET /MAAS/a/v3/racks`.
- **API v3 Limitations**: MAAS API v3 does **not** expose an instance UUID endpoint and does **not** expose a region controller list endpoint. Consequently:
  - `instance_uuid` is **not** returned (no v3 endpoint available).
  - `region_controllers` is **not** returned (no v3 endpoint available).
  - These fields must not be fabricated or sourced from a non-v3 path.
- All data is sourced exclusively from MAAS API v3; the MCP server applies no caching or enrichment.
- The tool is always available regardless of TC-2 status (it is a read-only operation with no machine lifecycle dependency).
- Permission errors returned by API v3 when querying configuration or rack information are surfaced directly to the AI client without masking (FR-7).
- The tool must complete within the `MAAS_REQUEST_TIMEOUT` window (FR-9/FR-11); if any underlying API v3 call times out, a `maas_unreachable` error is returned.

### FR-13: Network Fabric, VLAN & Subnet Management Tools

- The server exposes tools to **list** fabrics, VLANs, and subnets: `list_fabrics` (`GET /MAAS/a/v3/fabrics`), `get_fabric` (`GET /MAAS/a/v3/fabrics/{fabric_id}`), `list_vlans` (`GET /MAAS/a/v3/fabrics/{fabric_id}/vlans`), `get_vlan` (`GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}`), `list_subnets` (`GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets`), `get_subnet` (`GET /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{id}`).
- **Subnet nesting (API v3)**: Subnets are nested under VLANs in API v3 — there is no flat `/subnets/` collection endpoint. All subnet tools require `fabric_id` and `vlan_id` as mandatory parameters. IP ranges (`/ipranges`), reserved IPs (`/reserved_ips`), and static routes (`/staticroutes`) are available as further sub-resources of subnets via API v3 and may be exposed as additional tools in a future increment.
- The server exposes tools to **create** fabrics, VLANs, and subnets: `create_fabric` (`POST /MAAS/a/v3/fabrics`), `create_vlan` (`POST /MAAS/a/v3/fabrics/{fabric_id}/vlans`, accepting at minimum: fabric ID, VID, name, MTU, DHCP relay target), `create_subnet` (`POST /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets`, accepting at minimum: fabric ID, VLAN ID, name, CIDR, gateway IP, DNS server list).
- The server exposes tools to **update** fabrics, VLANs, and subnets: `update_fabric` (`PUT /MAAS/a/v3/fabrics/{fabric_id}`), `update_vlan` (`PUT /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}`), `update_subnet` (`PUT /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{id}`).
- The server exposes tools to **delete** fabrics, VLANs, and subnets: `delete_fabric` (`DELETE /MAAS/a/v3/fabrics/{fabric_id}`), `delete_vlan` (`DELETE /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}`), `delete_subnet` (`DELETE /MAAS/a/v3/fabrics/{fabric_id}/vlans/{vlan_id}/subnets/{id}`).
- All read operations support pagination for environments with large numbers of VLANs or subnets.
- All write operations (create, update, delete) use the user's own MAAS API key with no credential substitution (FR-2).
- Permission errors from API v3 are surfaced directly to the AI client (FR-7); the server does not retry with elevated credentials.
- These tools are included in the MCP tool-listing response and are not subject to TC-2 deferral.
- **Delete behaviour (no server-side confirmation gate)**: Delete operations (`delete_fabric`, `delete_vlan`, `delete_subnet`) execute immediately upon invocation — the MCP server applies no interactive or programmatic confirmation step before submitting the delete request to API v3. The success response **always** includes the deleted resource's identity: fabric name for `delete_fabric`; VLAN VID + name for `delete_vlan`; subnet CIDR + name (with fabric + VLAN context) for `delete_subnet`. This identity payload enables the AI client to verify the correct target was acted on. **Confirmation responsibility lies with the AI client, not the MCP server.**

### FR-14: Boot Source Management Tools

- The server exposes a tool to **list** current boot sources: `list_boot_sources` (`GET /MAAS/a/v3/boot_sources` — returns each source's URL, key-ring data, and ID as provided by API v3).
- The server exposes a tool to **trigger a sync** for a boot source selection: `trigger_boot_source_sync` (`POST /MAAS/a/v3/boot_sources/{boot_source_id}/selections/{selection_id}:sync` — triggers MAAS to sync the selected boot image; returns the job or request status as returned by the API). **The tool accepts `boot_source_id` and `selection_id` as parameters; it does not accept source URL, source type, or credential parameters.** It delegates entirely to MAAS, which uses its own pre-configured image sources. The MCP server has no knowledge of, and no interface to, those source configurations.
- The server exposes a tool to **delete** a specific boot source: `delete_boot_source` (`DELETE /MAAS/a/v3/boot_sources/{boot_source_id}` — accepts boot source ID; executes immediately with no server-side confirmation gate; the success response always includes the deleted source's ID and URL so the AI client can verify the correct source was removed; **confirmation responsibility lies with the AI client, not the MCP server**).
- All operations use the user's own MAAS API key with no credential substitution (FR-2).
- Permission errors from API v3 are surfaced directly to the AI client (FR-7).
- These tools are included in the MCP tool-listing response and are not subject to TC-2 deferral.
- The sync operation is long-running on the MAAS side; the tool returns the API v3 response (accepted/queued status) immediately without polling. The AI client or operator is responsible for polling `list_boot_sources` or inspecting selections to confirm sync completion.

---

## Success Criteria

1. **Fleet queries complete quickly**: Users receive fleet discovery results within 3 seconds for fleets up to 1,000 machines under normal network conditions.
2. **Authentication is enforced end-to-end**: 100% of tool calls that result in MAAS API v3 responses use the requesting user's API key with no credential substitution, verified through MAAS audit logs.
3. **Permission model is faithfully reflected**: A user with restricted MAAS permissions receives identical access boundaries when using the MCP server as when calling the MAAS API v3 directly — no privilege escalation and no unjustified denial.
4. **Core MAAS system is unaffected**: The MCP server can be started, restarted, or stopped without causing any change to MAAS controller health, machine state, or ongoing provisioning operations.
5. **Machine lifecycle writes remain deferred**: Commissioning, deploy, release, abort, rescue, tag mutation, pool reassignment, and other machine lifecycle write operations cannot be validated until API v3 exposes the corresponding endpoints (TC-2). This criterion is entirely deferred. Network management (fabric/VLAN/subnet) and boot-source write operations are in scope and covered by criteria below.
6. **Multi-user isolation**: Multiple concurrent users each operate within their own authenticated session with no cross-session data leakage, verified by confirming that one user's credentials are never used in another user's API calls.
7. **Operational visibility**: The server emits structured JSON to stdout (NDJSON — one JSON object per line). A compliant deployment must produce a parseable JSON log line for each of the following six mandatory event types: `session.opened` (SHA-256 hash of the API key token — never the raw key), `tool.received` (tool name + sanitised parameters), `maas.request` (HTTP method + URL pattern), `maas.response` (HTTP status + `duration_ms`), `tool.outcome` (`ok` or `error` + error code on failure), and `session.closed`. Testable by executing a single tool call end-to-end against a running server instance, capturing stdout, and asserting: (a) exactly six JSON lines are emitted in the correct sequence, (b) each line parses as valid JSON, (c) each line contains its mandatory fields, and (d) no line contains the raw API key string.
8. **Adoption is low-friction**: An administrator with an existing MAAS deployment can install and connect the MCP server to their AI client in under 15 minutes using documented steps.
9. **MAAS timeout is deterministic**: An unanswered MAAS API v3 HTTP request causes the server to return a `maas_unreachable` error to the AI client within `MAAS_REQUEST_TIMEOUT` seconds (default 30 s). No tool call blocks indefinitely. Testable by pointing the server at an unreachable MAAS endpoint and confirming the error is returned in ≤30 s with `error_code: "maas_unreachable"` and no retry attempt recorded in the structured logs.
10. **MAAS instance is identifiable**: Invoking `get_maas_info` on an authenticated session returns a response containing a non-empty `deployment_name` (from `GET /configurations/maas_name`) and a `rack_controllers` list (from `GET /racks`) — all matching the known target MAAS deployment. Note: `instance_uuid` and `region_controllers` are not included in the response as MAAS API v3 does not expose these fields. Testable by comparing the tool response against known deployment name and rack inventory from the MAAS deployment under test.
11. **Network management writes succeed**: A `create_vlan` → `list_vlans` → `delete_vlan` round-trip and a `create_subnet` (with fabric_id + vlan_id) → `list_subnets` (same fabric_id + vlan_id context) → `delete_subnet` round-trip via MCP tools each produce results consistent with direct API v3 calls against the nested paths (`/fabrics/{id}/vlans/` and `/fabrics/{id}/vlans/{id}/subnets/`): the resource appears in the listing after creation and is absent after deletion. All operations respect the requesting user's MAAS permissions.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| **MCP Session** | An active HTTP/SSE connection from an AI client to the MCP server, scoped to a single user's MAAS API key |
| **MCP Tool** | A named, callable action exposed by the MCP server (e.g., `list_machines`, `get_machine_details`, `get_maas_info`) |
| **MCP Resource** | A named, readable data object exposed by the MCP server (e.g., machine inventory snapshot) |
| **MAAS API Key** | A user-owned credential provided at session initialisation; never stored persistently by the MCP server |
| **Machine** | A physical node managed by MAAS, discoverable and operable via API v3 |
| **Resource Pool** | A logical grouping of machines in MAAS for access control and allocation |
| **Availability Zone** | A physical or logical fault domain for machines in MAAS |
| **MAAS Instance UUID** | The globally unique identifier of a MAAS deployment — **not available via API v3**. `get_maas_info` (FR-12) does not return this field; no v3 endpoint exposes an instance UUID |
| **Region Controller** | A MAAS controller node responsible for the API layer, DNS, and DHCP management — **not available via API v3**. No v3 endpoint exposes a region controller list; `get_maas_info` does not include this field |
| **Rack Controller** | A MAAS controller node responsible for local PXE, DHCP relay, and power management; zero or more per deployment; exposed by `get_maas_info` via `GET /MAAS/a/v3/racks` |
| **Fabric** | A MAAS network fabric — a collection of VLANs that share the same physical or virtual layer-2 domain; manageable via FR-13 (`/fabrics` endpoints) |
| **VLAN** | A Virtual LAN within a fabric; identified by VID; manageable (create/update/delete) via API v3 write endpoints (`/fabrics/{fabric_id}/vlans`) (FR-13) |
| **Subnet** | An IP network (CIDR block) **nested under a VLAN** in API v3 (`/fabrics/{fabric_id}/vlans/{vlan_id}/subnets`); identified by CIDR; manageable (list, get, create, update, delete) via API v3 write endpoints (FR-13). A flat `/subnets/` collection endpoint does not exist in API v3 |
| **Boot Source** | A configured image source in MAAS (formerly called "boot resource" in v2) — defines the URL and key-ring for fetching kernel images, initrd files, and PXE boot artefacts; listable and manageable via `GET /MAAS/a/v3/boot_sources` (FR-14) |

---

## Assumptions

- MAAS API v3 is assumed to be available and reachable from the network location where the MCP server is deployed.
- Users have pre-existing MAAS accounts with API keys; the MCP server does not provide user account management.
- The MCP server does not need to support MAAS API v2 (legacy Django) endpoints. **Note**: API v3 supports read (GET) operations and select write operations. **Machine lifecycle write operations** (commission, release, abort, rescue, deploy, tag mutations, pool reassignment, power parameter updates) are **not available** in API v3 at this time and remain deferred (TC-2). Write operations for network management (fabrics, VLANs, subnets nested under VLANs at `/fabrics/{id}/vlans/{id}/subnets`) and boot-source management (via `/boot_sources/` hierarchy) **are available** in API v3 and are in scope; see FR-13 and FR-14.
- Session statefulness is limited to holding the user's API key for the duration of the connection; no conversation history, query caching, or cross-request state is maintained by the MCP server itself (AI client context windows handle conversational state).
- **Session lifetime is connection-scoped** (FR-11): a session persists for exactly as long as the underlying MCP client HTTP/SSE connection remains open. The server applies no server-side idle expiry or keep-alive timer. Disconnection immediately tears down the session.
- The MCP server is intended for single-operator or small-team use cases in its initial form; horizontal scaling is a future concern.
- MAAS API v3 responses are treated as authoritative; the MCP server does not apply additional business logic to filter or transform response data beyond adapting it to MCP protocol format.
- **No native TLS on the MCP listener (TC-4, Hard Constraint)**: The MCP server always listens in plain HTTP. TLS termination is exclusively the operator's responsibility via a reverse proxy (e.g., nginx, HAProxy). The server provides no native TLS configuration option on its own listener — there is no opt-in, no flag, and no "optional native TLS" mode.

---

## Out of Scope

- Integration with MAAS API v2 (legacy Django endpoints)
- Direct database access or MAAS internal RPC
- Built-in AI model hosting or LLM inference
- Managing MAAS user accounts, API key creation, or permission assignment
- MAAS UI changes or new UI components
- Real-time streaming of machine event logs via persistent push connections
- Multi-MAAS-region federated queries (single MAAS endpoint per MCP server instance)
- **Machine lifecycle write operations** — API v3 does not expose write endpoints for machine lifecycle management at this time. Commission, release, abort, rescue, deploy (OS installation), tag mutations (add/remove), resource pool reassignment, power parameter updates, and ownership changes are all unavailable in API v3 (TC-2). Because the MCP server communicates exclusively via API v3 (FR-3), none of these operations can be supported in the initial release. User Stories P4 and P5 and all FR-6 tools are fully deferred until API v3 exposes the corresponding write endpoints. **Note**: write operations for network management (fabrics, VLANs, subnets nested under VLANs — FR-13) and boot-source management (via `/boot_sources/` hierarchy — FR-14) are available in API v3 and are in scope.
- **Boot image source configuration and management** — Configuring or modifying the image sources that MAAS uses to fetch boot resources (source URLs, source types, credentials, or any equivalent MAAS-side source registry) is explicitly out of scope for the MCP server. `trigger_boot_source_sync` (FR-14) triggers a sync against MAAS's own pre-configured sources; the MCP server neither reads nor writes those source definitions. Operators must manage image sources directly in MAAS.

---

## Technical Constraints

### TC-1: MCP SDK — Ubuntu Archive System Dependency (Hard Constraint)

- The MCP server **must** use the official MCP Python SDK located at https://github.com/modelcontextprotocol/python-sdk as its sole MCP protocol implementation library.
- The SDK **must** be declared as a **system dependency sourced exclusively from the Ubuntu package archive** (package name: `python3-mcp` or the canonical archive name for the target Ubuntu series). This is a hard constraint with no exceptions.
- The SDK **must NOT** be vendored within the repository, bundled inside a snap, or installed via `pip` from PyPI. Any build or packaging step that fetches `mcp` or `modelcontextprotocol` from PyPI is prohibited.
- The build system, packaging manifest (`.deb` control file, `snapcraft.yaml` stage-packages, or equivalent), and any CI dependency declarations must all reference the Ubuntu archive package — not a PyPI index.
- Downstream consumers of the MCP server package (operators, CI pipelines) must be able to satisfy the MCP SDK dependency solely by enabling a standard Ubuntu package mirror with no additional package sources required.

### TC-2: API v3 Machine Lifecycle Write Operations Unavailability (Hard Constraint)

- The MAAS HTTP API v3 **does not** expose write endpoints for machine lifecycle management at this time. This is a **hard constraint** on the machine lifecycle portions of the MCP server's scope.
- Specifically, the following **machine lifecycle operations are not available** in API v3 and must not be implemented: commission, release, abort, rescue, deploy (OS installation), tag mutations (add/remove), resource pool reassignment, power parameter updates, and ownership changes.
- **Partial correction**: API v3 **does** expose write endpoints for the following domains, which are therefore **in scope** for this release:
  - **Network management**: fabrics (create, update, delete), VLANs (create, update, delete), and subnets (create, update, delete, nested under VLANs at `/fabrics/{fabric_id}/vlans/{vlan_id}/subnets`) — covered by FR-13.
  - **Boot-source management**: boot source sync and deletion (via `/boot_sources/` hierarchy) — covered by FR-14.
- Because FR-3 mandates exclusive communication via API v3, the MCP server **must not** attempt to implement any of the deferred machine lifecycle write operations by any other means (e.g., API v2, internal RPC, direct DB access).
- All tools in FR-6 (Machine Lifecycle Provisioning Tools) are **fully deferred** until API v3 exposes the corresponding write endpoints.
- User Stories P4 (Automated Node Provisioning) and P5 (Resource Lifecycle Management) are **fully deferred** for the same reason.
- The MCP server's machine lifecycle scope is **read-only**: fleet discovery (P2/FR-4), hardware inspection and troubleshooting (P3/FR-5), and session authentication (P1/FR-2). Network management (US7/FR-13), boot-source management (US8/FR-14), and MAAS instance identification (US6/FR-12) are in scope.
- **Machine lifecycle write tools are absent from the tool-listing response** while TC-2 is in force: a client querying available tools will not see any machine lifecycle write-operation tool entries. Network management and boot-source tools (FR-13/FR-14) are listed normally.
- **Runtime guard — MCP `not-implemented` error**: If a machine lifecycle write-operation tool call is received while TC-2 is in force (e.g., from a client operating with a stale or externally supplied tool list), the server **must** respond immediately with a structured MCP `not-implemented` error and a human-readable message (e.g., `"Machine lifecycle write operations are not available: API v3 does not currently expose write endpoints for machine lifecycle management (TC-2). Tool '<name>' is deferred."`). No partial execution, no MAAS API v3 call, and no silent failure is permitted.
- When API v3 gains machine lifecycle write endpoints, TC-2 should be revisited, this constraint partially or fully lifted, and the deferred items restored to scope incrementally.

### TC-3: HTTP/SSE Transport (Hard Constraint)

- The MCP server **must** use **HTTP/SSE (Server-Sent Events)** as its sole MCP transport mechanism.
- **stdio transport is not supported** and must not be implemented. No code path, configuration flag, or deployment mode may activate stdio as a transport.
- The server **always** runs as a persistent network service bound to a configured address and port; it does not read MCP protocol messages from standard input or write them to standard output.
- All MCP client connections are established over HTTP. The server delivers MCP event streams to connected clients via SSE on the HTTP response body.
- Any deployment documentation, packaging, or configuration template must describe only the HTTP/SSE deployment model. References to stdio-based invocation are prohibited.

### TC-4: No Native TLS on MCP Listener (Hard Constraint)

- The MCP server **never** provides native TLS on its own HTTP/SSE listener in v1. This is a **hard constraint with no exceptions**.
- The server always listens in **plain HTTP** on the configured address and port, regardless of how it is deployed.
- TLS termination is **exclusively the operator's responsibility**, achieved by placing a TLS-terminating reverse proxy (e.g., nginx, HAProxy) in front of the MCP server.
- **No native TLS configuration parameters exist**: `TLS_CERT`, `TLS_KEY`, `TLS_CA`, or any equivalent configuration keys must not be implemented in v1. Any deployment configuration referencing such parameters is invalid.
- Operators requiring encrypted MCP connections must use the reverse-proxy pattern; this requirement must be documented in all deployment and operations guides.
- There is no "optional native TLS" mode — the transport layer for the MCP listener is plain HTTP, full stop.

---

## Dependencies

- MAAS deployment with HTTP API v3 enabled and accessible
- An MCP-compatible AI client (e.g., Claude Desktop, a custom LLM host implementing the MCP client protocol)
- Network connectivity between the MCP server and the MAAS API v3 endpoint
- `python3-mcp` (or canonical Ubuntu archive equivalent): the MCP Python SDK, sourced from the Ubuntu package archive — **not** from PyPI (see TC-1)
