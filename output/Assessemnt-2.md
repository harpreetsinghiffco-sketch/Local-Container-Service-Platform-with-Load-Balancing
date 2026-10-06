# Project Assessment 2: Architecture & Core Feature Specification

## 1. Finalized Project Title & Brief Description
**Project Title**: Local Container Service Platform with Load Balancing (CSP-LB)

**Brief Description**:  
The Local Container Service Platform is an orchestrator and application delivery platform that runs on a developer's local machine. It deploys and manages multiple isolated instances of a microservice (dummy service) across local containers (using both process-isolated namespaces and Docker runtimes), exposes an intelligent reverse proxy load balancer supporting multiple distribution policies (Round Robin, Least Connections, Random, IP Hash), performs automated background health checking with instant failover, and dynamically auto-scales instances according to real-time traffic load.

---

## 2. Major Components
The system is cleanly decoupled into three foundational tiers:

1. **User Interface (UI Tier)**:
   - **Interactive Web Dashboard (`web/index.html`, `static/styles.css`, `static/app.js`)**: A modern, high-contrast control console that visualizes active containers, health status, live request counters, cluster RPS, and per-container request distribution charts.
   - **Interactive Traffic Generator & Testbench**: Built-in interactive test controls to fire single requests, traffic bursts (10 to 25 requests), and continuous stream testing.
   - **Command-Line Interface (CLI - `cli.py`)**: Terminal tool for DevOps workflows (`deploy`, `stop`, `start`, `rm`, `algo`, `status`, `benchmark`).

2. **Logic (Application & Orchestration Tier)**:
   - **Container Manager (`core/container_manager.py`)**: Manages the complete lifecycle (creation, port assignment, health state, termination) of local microservice instances.
   - **Reverse Proxy Load Balancer (`core/load_balancer.py`)**: Intercepts inbound traffic at `/service/*`, evaluates healthy instances, and forwards requests using dynamic scheduling algorithms.
   - **Health Checker Daemon (`core/health_checker.py`)**: Background worker that continuously pings microservices at `/health`, detects unresponsive or failing containers, and auto-excludes them from the load balancer routing pool.
   - **Dynamic Auto-Scaler (`core/auto_scaler.py`)**: Monitors traffic load (RPS) against defined thresholds to spin up or tear down containers with cooldown protection.

3. **Persistence (Data Tier)**:
   - **SQLite Database (`data/platform.db`)**: Persists container configurations, historical telemetry, and state transitions.
   - **System Audit Logger (`core/storage.py`)**: Records event transitions (container starts, shutdowns, health check failures, recoveries, scale triggers).

---

## 3. System Architecture

```
                    +------------------------------------+
                    |   Client Browser / CLI Terminal    |
                    +-----------------+------------------+
                                      |
                     HTTP Requests    | Control Actions
                                      v
    +-----------------------------------------------------------------+
    |          Unified API Gateway & Control Plane (Port 8000)        |
    |                                                                 |
    |  [ Web UI & Static ]   [ REST API (/api/*) ]   [ Reverse Proxy ]|
    +--------------------------------------------------------+--------+
                                                             |
                                      +----------------------+
                                      | Dynamic Scheduling (RR, LC, IP-Hash)
                                      v
    +-----------------------------------------------------------------+
    |                    Load Balancer Core Engine                    |
    |     - Health-Filtered Target Pool                               |
    |     - Request Retry & Failover Handlers                         |
    |     - Latency & Telemetry Collectors                            |
    +---+-----------------------------+---------------------------+---+
        |                             |                           |
        v                             v                           v
+------------------+         +------------------+        +------------------+
| Container srv-1  |         | Container srv-2  |        | Container srv-3  |
| Port: 9001       |         | Port: 9002       |        | Port: 9003       |
| Status: HEALTHY  |         | Status: HEALTHY  |        | Status: HEALTHY  |
+------------------+         +------------------+        +------------------+
        ^                             ^                           ^
        |                             |                           |
        +-----------------------------+---------------------------+
                                      | Periodic Health Pings (/health)
    +---------------------------------+-------------------------------+
    |                   Background Worker Daemons                     |
    |  - Health Checker (interval: 3s, failure/recovery threshold)    |
    |  - Auto-Scaler (evaluates RPS vs capacity, cooldown protection) |
    +-----------------------------------------------------------------+
```

---

## 4. Minimal Set of Features (Initial Deliverable)
1. **Container Lifecycle Orchestration**: Automated local container spawning, unique port binding, process execution, and termination.
2. **Reverse Proxy Load Balancing**: Multi-algorithm request distribution (Round Robin, Least Connections, Random, IP Hash) with zero configuration.
3. **Microservice Simulation**: Deploying dummy microservices capable of processing simulated business requests, returning container metadata, and supporting failure injection (`/simulate/fail`).
4. **Automated Health Probing**: Periodic health monitoring with automatic exclusion of degraded instances from active traffic.
5. **Interactive Single-Page Dashboard**: Live visual feedback for container state, live request distributions, and immediate test traffic triggering.

---

## 5. Target Users & Stakeholders
- **Software & Systems Engineering Students**: Learning practical distributed systems concepts, microservice design, reverse proxy mechanisms, and container management.
- **Backend & Cloud Developers**: Needing a zero-overhead local sandbox to prototype load balancing strategies without incurring cloud vendor fees.
- **DevOps & Site Reliability Engineers (SREs)**: Simulating chaos engineering (failure injection, recovery detection, auto-scaling) on a single local development machine.

---

## 6. Components of the First Deliverable
1. `app.py`: Central Gateway and HTTP routing engine.
2. `dummy_service/service.py`: Microservice container application.
3. `core/container_manager.py`: Local container creation and lifecycle manager.
4. `core/load_balancer.py`: Forwarding proxy and load balancing algorithms.
5. `core/health_checker.py`: Health verification engine.
6. `core/auto_scaler.py`: Load-based autoscaler.
7. `core/storage.py`: SQLite persistence layer.
8. `web/`: Full frontend interface (HTML, CSS, JS).

---

## 7. Component Interfaces (API & CLI)

### Load Balancer Gateway Routes:
- `GET /service/*` or `POST /service/*`: Forwarded transparently to an active healthy backend container.

### Control Plane REST Endpoints:
- `GET /api/status`: Complete cluster state, load balancer stats, and health checker results.
- `POST /api/containers/deploy`: Spin up a new container instance.
- `POST /api/containers/<id>/stop`: Stop an existing container.
- `POST /api/containers/<id>/start`: Start a stopped container.
- `DELETE /api/containers/<id>`: Terminate and destroy container.
- `POST /api/containers/<id>/simulate/fail`: Inject failure into container.
- `POST /api/containers/<id>/simulate/recover`: Restore container health.
- `POST /api/loadbalancer/algorithm`: Switch load balancing algorithm.
- `POST /api/traffic/burst`: Fire $N$ test requests for demonstration.
- `POST /api/autoscaler/config`: Update auto-scaler parameters.
- `GET /api/logs`: Query audit events.

### Developer CLI (`cli.py`):
```bash
python3 cli.py status
python3 cli.py deploy [--name <str>] [--port <int>]
python3 cli.py stop <container_id>
python3 cli.py start <container_id>
python3 cli.py algo <round_robin|least_connections|random|ip_hash>
python3 cli.py benchmark --requests 25
```

---

## 8. Technology Stack
- **Programming Language**: Python 3 (built-in standard library for high portability and zero external dependency friction).
- **Web Frontend**: HTML5, Vanilla JavaScript (ES6+ async/await), Custom CSS with modern dark mode theme.
- **Database / Persistence**: SQLite3 (`data/platform.db`) for transaction safety and ACID guarantees.
- **Container Isolation**: Multi-threaded isolated processes with port isolation & optional Docker engine integration (`Dockerfile`).
- **Testing Framework**: Python `unittest` standard library.
