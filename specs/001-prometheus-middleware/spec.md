# Feature Specification: Prometheus Observability Middleware

**Feature Branch**: `001-prometheus-middleware`
**Created**: 2026-02-26
**Status**: Draft
**Input**: User description: "Add Prometheus middleware for observability - expose workflow execution metrics (duration, token usage, node counts, error rates) via prometheus-client with a pluggable PrometheusMiddleware class that hooks into the existing Middleware system"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monitor Workflow Execution Metrics (Priority: P1)

A platform operator has deployed a generative-ai-workflow service and wants to monitor its health and performance using their existing Prometheus + Grafana stack. They attach the PrometheusMiddleware to their WorkflowEngine, start a Prometheus scrape endpoint, and immediately see workflow duration histograms, token usage counters, and node success/failure counts in Grafana dashboards.

**Why this priority**: This is the core deliverable — without exportable metrics the feature has no value.

**Independent Test**: Can be fully tested by running a workflow with PrometheusMiddleware attached, then scraping the metrics registry and verifying expected metric names and values appear.

**Acceptance Scenarios**:

1. **Given** a WorkflowEngine with PrometheusMiddleware attached, **When** a workflow completes successfully, **Then** a duration histogram metric is recorded and a completion counter increments with status label `completed`.
2. **Given** a WorkflowEngine with PrometheusMiddleware attached, **When** a workflow fails at a node, **Then** a failure counter increments with status label `failed` and a node-error counter increments labelled by the failing node name.
3. **Given** metrics have been recorded, **When** the Prometheus registry is serialised, **Then** all registered metrics appear in valid Prometheus text exposition format.

---

### User Story 2 - Track Token Usage Per Node (Priority: P2)

A cost-conscious developer wants to understand which nodes consume the most tokens so they can optimise prompts. After attaching the middleware, they query per-node token counters in Prometheus and identify the expensive node.

**Why this priority**: Token cost is a primary operational concern for LLM workloads; per-node granularity makes the data actionable.

**Independent Test**: Can be tested by running a workflow with multiple LLM nodes, then verifying that separate token counter time series exist per node name label.

**Acceptance Scenarios**:

1. **Given** a workflow with two LLM nodes, **When** the workflow completes, **Then** prompt-token and completion-token counters are available with a `node` label distinguishing each node's usage.
2. **Given** a node that performs no LLM call (e.g., an image generation node), **When** the workflow completes, **Then** no token metric is emitted for that node (zero-value pollution is avoided).

---

### User Story 3 - Zero-Config Registry Isolation (Priority: P3)

A library user embeds generative-ai-workflow inside a larger application that already uses Prometheus. They need the middleware's metrics to live in an isolated registry to avoid name collisions with other application metrics, while still being able to merge or expose them on a custom port.

**Why this priority**: Library-friendly design prevents integration friction in multi-component systems.

**Independent Test**: Can be tested by instantiating PrometheusMiddleware with a custom CollectorRegistry and verifying that the global default registry is unaffected.

**Acceptance Scenarios**:

1. **Given** a custom CollectorRegistry passed to PrometheusMiddleware, **When** the middleware records metrics, **Then** those metrics appear only in the custom registry, not in the global default registry.
2. **Given** no registry is provided, **When** PrometheusMiddleware is instantiated, **Then** it registers metrics against the global default Prometheus registry.

---

### Edge Cases

- What happens when a workflow is cancelled mid-execution? The middleware should record a partial duration and increment a cancelled-count metric labelled `cancelled`.
- What happens when PrometheusMiddleware is attached to multiple WorkflowEngine instances sharing the same registry? Metrics must aggregate across all engines without double-registration errors.
- What happens if `prometheus-client` is not installed? Importing the middleware module must raise a clear `ImportError` with an install hint rather than an obscure attribute error.
- What happens when a node name contains characters invalid for Prometheus labels? The middleware must sanitise label values to comply with Prometheus label character rules.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a `PrometheusMiddleware` class that implements the existing `Middleware` base class interface without modifying any existing middleware or engine code.
- **FR-002**: The middleware MUST record workflow total duration as a Prometheus Histogram with configurable bucket boundaries.
- **FR-003**: The middleware MUST increment a workflow completion counter labelled by final workflow status (`completed`, `failed`, `cancelled`, `timeout`).
- **FR-004**: The middleware MUST record per-node execution duration as a Prometheus Histogram labelled by node name.
- **FR-005**: The middleware MUST expose prompt-token and completion-token counters labelled by node name and model name.
- **FR-006**: The middleware MUST increment a per-node error counter labelled by node name when a node fails.
- **FR-007**: The middleware MUST accept an optional `CollectorRegistry` parameter; when omitted it defaults to the global Prometheus default registry.
- **FR-008**: The middleware MUST accept an optional metric name prefix (default: `workflow`) to namespace all metric names and prevent collisions.
- **FR-009**: Importing `PrometheusMiddleware` when `prometheus-client` is not installed MUST raise `ImportError` with a human-readable install instruction.
- **FR-010**: Label values derived from node names or model names MUST be sanitised to valid Prometheus label characters (alphanumeric and underscore only).
- **FR-011**: All metrics MUST include an optional `workflow_name` label; when the caller does not supply a workflow name, the label value defaults to an empty string.
- **FR-012**: Any error occurring during metric recording MUST be caught by the middleware, logged as a warning via the existing structured logging facility, and MUST NOT propagate to or interrupt the workflow execution.
- **FR-013**: The middleware MUST NOT add its own concurrency locks; correctness under concurrent async/multi-engine use relies on the thread-safety guarantees provided by the metrics client library itself.
- **FR-014**: The middleware MUST accept an optional `label_sanitiser` callable at construction time; when provided it replaces the default character sanitiser for all label value transformations, enabling callers to mask or hash sensitive node/model names.

### Key Entities

- **PrometheusMiddleware**: The middleware class; holds references to all Prometheus metric objects and the registry. Constructed with optional prefix and registry.
- **Metric Registry**: A `CollectorRegistry` instance (default or custom) that owns the metric descriptors for this middleware.
- **Metric Labels**: Dimensions attached to each time series — `status` (workflow level), `node` (node level), `model` (token metrics) — enabling filtering in Prometheus queries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After attaching PrometheusMiddleware and running one workflow, at least 4 distinct metric families appear in the registry output (workflow duration histogram, workflow completion counter, token counter, node error counter).
- **SC-002**: Per-node token metrics carry a `node` label that exactly matches the node's name as configured in the workflow definition.
- **SC-003**: Using an isolated custom registry leaves the global default Prometheus registry unchanged — zero new metric families are registered globally.
- **SC-004**: Attaching PrometheusMiddleware adds no more than 1 ms of overhead per workflow execution on average, measured against the existing performance baseline.
- **SC-005**: 100% of existing framework unit and integration tests continue to pass after the feature is introduced (zero regressions).

## Clarifications

### Session 2026-02-26

- Q: Should metrics include a `workflow_name` label to distinguish different workflow types? → A: Yes — optional `workflow_name` label, defaults to empty string when not provided by the caller.
- Q: What should happen if metric recording fails inside the middleware? → A: Swallow the error silently — emit a warning via structlog, never raise, so observability code never interrupts workflow execution.
- Q: Must the middleware add its own locking for async/thread safety? → A: No — rely on prometheus-client's built-in thread-safety guarantees; no extra synchronisation is required.
- Q: Should users be able to customise how label values are sanitised to prevent sensitive data exposure? → A: Yes — default to built-in character sanitiser, but accept an optional `label_sanitiser` callable at construction time for security-conscious users.
- Q: What is the minimum required version of the metrics client library? → A: `prometheus-client >= 0.16.0`.

## Assumptions

- The `prometheus-client` Python package (minimum version `0.16.0`) will be listed as an optional dependency (extras group `observability`), not a mandatory dependency, to avoid forcing it on users who do not need metrics export.
- Histogram bucket boundaries for duration metrics use the `prometheus-client` default buckets unless the user overrides them at middleware construction time via a constructor parameter.
- The middleware does not spin up an HTTP server; exposing the `/metrics` scrape endpoint is the responsibility of the consuming application, consistent with the library's design philosophy.
- Node names are assumed to be stable identifiers set at workflow definition time, not dynamic runtime values, making them safe for use as Prometheus label values.
