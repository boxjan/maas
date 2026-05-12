# Feature Specification: MAAS MCP Server

**Feature Branch**: `6689-mcp-server`
**Created**: 2025-07-22
**Status**: Draft

## Overview

An optional, independently deployable Model Context Protocol (MCP) server that acts as a modular gateway between Large Language Models (LLMs) and MAAS bare-metal infrastructure. The server communicates exclusively with the MAAS HTTP API v3 and implements a transparent token-delegation authentication model, ensuring that every operation is governed by the requesting user's own MAAS permissions without introducing centralized service accounts.

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

### User Story 3 - Hardware Troubleshooting Assistance (Priority: P3)

An operator investigating an unexpected machine failure wants to gather diagnostic information quickly. Rather than navigating multiple MAAS UI screens or running several API calls manually, they ask their AI assistant: "What events have been recorded for machine X in the last 24 hours?" or "Show me the commissioning log for node Y." The MCP server fetches the relevant logs, events, and hardware test results via API v3 and presents them in a consolidated, readable format.

**Why this priority**: Troubleshooting is a high-value, time-sensitive workflow. Consolidating multi-call diagnostic data into a single natural language interaction meaningfully reduces incident response time.

**Independent Test**: Can be fully tested by requesting event logs and commissioning output for a specific machine through the MCP client and confirming the data matches the direct API v3 responses — no provisioning changes required.

**Acceptance Scenarios**:

1. **Given** an authenticated session, **When** the user requests the event history for a specific machine, **Then** the MCP server retrieves and returns the events from API v3 in chronological order.
2. **Given** an authenticated session, **When** the user requests commissioning or testing script output for a machine, **Then** the server retrieves and returns the script results from API v3.
3. **Given** an authenticated session, **When** the user asks for hardware details (CPU, memory, storage, network interfaces) of a specific machine, **Then** the server returns the full hardware inventory from API v3.
4. **Given** a user without log-view permissions for a particular machine, **When** they request diagnostic information, **Then** the server returns an authorisation error consistent with the API v3 permission model.

---

### User Story 4 - Automated Node Provisioning via Natural Language (Priority: P4)

A MAAS administrator needs to provision a batch of machines for a new workload. Instead of scripting API calls or navigating the UI for each machine, they instruct their AI assistant: "Commission the three ready machines in pool 'compute' and deploy Ubuntu 24.04 on them once commissioning completes." The MCP server decomposes the request into the required sequence of API v3 operations, executes them with the user's own credentials, and reports progress at each step.

**Why this priority**: Automated provisioning is the highest-impact write capability. It must be built on the solid foundation of discovery (P2) and authentication (P1), and carries the greatest security implications — hence it comes after read-only capabilities are proven.

**Independent Test**: Can be fully tested by issuing a provisioning instruction via the MCP client, then independently verifying in MAAS that the machines transitioned through the expected states — without any manual API calls.

**Acceptance Scenarios**:

1. **Given** an authenticated session with deploy permissions, **When** the user instructs the server to deploy an OS on a ready machine, **Then** the MCP server submits the correct API v3 deploy request and confirms the machine has entered the deploying state.
2. **Given** an authenticated session, **When** the user instructs a provisioning action that the user's MAAS role does not permit, **Then** the MCP server returns a clear permission-denied message without partially executing the operation.
3. **Given** an authenticated session with commission permissions, **When** the user instructs commissioning of one or more machines, **Then** the server submits the commissioning request via API v3 and reports the resulting machine state.
4. **Given** a provisioning instruction that references a non-existent machine or pool, **When** the API v3 returns a not-found response, **Then** the MCP server surfaces a descriptive error to the user rather than silently failing.
5. **Given** an in-progress provisioning operation, **When** the user requests a status update, **Then** the MCP server queries the current machine state via API v3 and reports it accurately.

---

### User Story 5 - Resource Lifecycle Management (Priority: P5)

An administrator managing the full lifecycle of machines in a large-scale environment wants to perform day-2 operations — tagging machines, updating power parameters, reassigning machines to pools, or releasing deployed nodes — through natural language. The MCP server maps these intents to the appropriate API v3 write operations and applies them under the user's credentials.

**Why this priority**: Day-2 lifecycle operations extend the utility of the MCP server beyond initial provisioning and are critical for ongoing fleet management, but they represent a wider attack surface and are lower urgency than core discovery and deployment.

**Independent Test**: Can be fully tested by issuing lifecycle commands (tag, release, reassign pool) via the MCP client and confirming the changes are reflected in the MAAS inventory via an independent API v3 query.

**Acceptance Scenarios**:

1. **Given** an authenticated session with appropriate permissions, **When** the user asks to add or remove a tag from one or more machines, **Then** the MCP server updates the tags via API v3 and confirms the change.
2. **Given** an authenticated session with appropriate permissions, **When** the user instructs releasing a deployed machine, **Then** the MCP server submits a release request via API v3 and confirms the machine transitions to the ready state.
3. **Given** an authenticated session with pool-management permissions, **When** the user reassigns a machine to a different resource pool, **Then** the MCP server submits the update via API v3 and reports the new pool assignment.

---

## Functional Requirements

### FR-1: MCP Protocol Compliance

- The server implements the Model Context Protocol specification, exposing MAAS capabilities as MCP **tools** (for actions) and MCP **resources** (for read-only data).
- The server responds correctly to MCP protocol handshake, tool-listing, resource-listing, and invocation messages.
- The server operates as an MCP server that AI clients (LLM hosts) connect to; it does not initiate connections to AI clients.

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
- The server exposes tools to list resource pools, availability zones, tags, and subnets.
- All list operations support pagination so that large fleets do not produce truncated results.

### FR-5: Diagnostic Tools

- The server exposes tools to retrieve machine event logs, filtered by time range.
- The server exposes tools to retrieve commissioning script output and hardware test results.
- The server exposes tools to retrieve the current power state of a machine.

### FR-6: Provisioning and Lifecycle Tools

- The server exposes tools to commission, deploy, release, abort, and rescue machines.
- The server exposes tools to set and update deployment parameters (OS image, kernel options, user data).
- The server exposes tools to manage machine tags, resource pool assignment, and ownership.
- The server exposes tools to update power parameters for machines with appropriate permissions.

### FR-7: Permission Transparency

- Before executing any write operation, the server informs the AI client of the action that will be taken and the affected resource(s).
- The server surfaces MAAS API v3 permission errors directly to the AI client without masking or retrying with elevated credentials.
- The server does not cache stale permission decisions; every API v3 call reflects the current state of the user's MAAS permissions.

### FR-8: Operational Independence

- The MCP server runs as a standalone process separate from all MAAS controller services.
- Starting, stopping, or restarting the MCP server has no effect on MAAS controller operation.
- The MCP server requires only network access to the MAAS API v3 endpoint; no shared filesystem, database connection, or MAAS internal socket is needed.

### FR-9: Configuration

- The server is configurable with the target MAAS API v3 base URL.
- TLS certificate verification for the MAAS API v3 endpoint is enabled by default, with an opt-out for self-signed certificates in development environments.
- The server listens on a configurable network address and port.
- All configuration is provided via environment variables or a configuration file; no configuration requires editing source code.

---

## Success Criteria

1. **Fleet queries complete quickly**: Users receive fleet discovery results within 3 seconds for fleets up to 1,000 machines under normal network conditions.
2. **Authentication is enforced end-to-end**: 100% of tool calls that result in MAAS API v3 responses use the requesting user's API key with no credential substitution, verified through MAAS audit logs.
3. **Permission model is faithfully reflected**: A user with restricted MAAS permissions receives identical access boundaries when using the MCP server as when calling the MAAS API v3 directly — no privilege escalation and no unjustified denial.
4. **Core MAAS system is unaffected**: The MCP server can be started, restarted, or stopped without causing any change to MAAS controller health, machine state, or ongoing provisioning operations.
5. **Provisioning operations are reliable**: Provisioning instructions issued via the MCP server result in the correct MAAS API v3 operations with a success rate matching direct API calls under the same network conditions.
6. **Multi-user isolation**: Multiple concurrent users each operate within their own authenticated session with no cross-session data leakage, verified by confirming that one user's credentials are never used in another user's API calls.
7. **Operational visibility**: All tool invocations and their outcomes are observable through standard logging, enabling operators to audit MCP server activity without access to the AI client conversation.
8. **Adoption is low-friction**: An administrator with an existing MAAS deployment can install and connect the MCP server to their AI client in under 15 minutes using documented steps.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| **MCP Session** | An active connection from an AI client to the MCP server, scoped to a single user's MAAS API key |
| **MCP Tool** | A named, callable action exposed by the MCP server (e.g., `list_machines`, `deploy_machine`) |
| **MCP Resource** | A named, readable data object exposed by the MCP server (e.g., machine inventory snapshot) |
| **MAAS API Key** | A user-owned credential provided at session initialisation; never stored persistently by the MCP server |
| **Machine** | A physical node managed by MAAS, discoverable and operable via API v3 |
| **Resource Pool** | A logical grouping of machines in MAAS for access control and allocation |
| **Availability Zone** | A physical or logical fault domain for machines in MAAS |

---

## Assumptions

- MAAS API v3 is assumed to be available and reachable from the network location where the MCP server is deployed.
- Users have pre-existing MAAS accounts with API keys; the MCP server does not provide user account management.
- The MCP server does not need to support MAAS API v2 (legacy Django) endpoints; all operations are available via v3.
- Session statefulness is limited to holding the user's API key for the duration of the connection; no conversation history, query caching, or cross-request state is maintained by the MCP server itself (AI client context windows handle conversational state).
- The MCP server is intended for single-operator or small-team use cases in its initial form; horizontal scaling is a future concern.
- MAAS API v3 responses are treated as authoritative; the MCP server does not apply additional business logic to filter or transform response data beyond adapting it to MCP protocol format.
- TLS termination for the MCP server's own listener is the operator's responsibility (e.g., via a reverse proxy); the MCP server may optionally support TLS natively.

---

## Out of Scope

- Integration with MAAS API v2 (legacy Django endpoints)
- Direct database access or MAAS internal RPC
- Built-in AI model hosting or LLM inference
- Managing MAAS user accounts, API key creation, or permission assignment
- MAAS UI changes or new UI components
- Real-time streaming of machine event logs via persistent push connections
- Multi-MAAS-region federated queries (single MAAS endpoint per MCP server instance)

---

## Dependencies

- MAAS deployment with HTTP API v3 enabled and accessible
- An MCP-compatible AI client (e.g., Claude Desktop, a custom LLM host implementing the MCP client protocol)
- Network connectivity between the MCP server and the MAAS API v3 endpoint

---

**Next Step**: Run `/speckit.plan` to generate a detailed implementation design.
