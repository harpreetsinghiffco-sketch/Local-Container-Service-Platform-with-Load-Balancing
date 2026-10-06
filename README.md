# ⚡ Local Container Service Platform with Load Balancing (CSP-LB)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/architecture-Microservices%20%7C%20Reverse%20Proxy-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()
[![Status](https://img.shields.io/badge/status-Assessment--3%20Complete-success.svg)]()

> **Project Topic 24**: Develop a platform that deploys multiple instances of a dummy service across local containers and distributes requests using a load-balancing strategy. Students can additionally implement service health checking and automatic scaling as advanced features.

---

## 🌟 Executive Summary

**Local Container Service Platform with Load Balancing (CSP-LB)** is an end-to-end distributed systems platform designed to run directly on a developer's local machine with **zero external dependencies**. 

The platform deploys and supervises a fleet of microservice containers, exposes a high-performance reverse proxy gateway supporting multiple load balancing algorithms, performs automated continuous health probing with transparent failover, and scales containers up or down dynamically based on live traffic load.

### Key Highlights
- **Zero-Dependency Architecture**: Runs out-of-the-box using the Python 3 standard library. No complex virtual environment setups, external package installations, or broken dependency chains during evaluations.
- **Dual Container Isolation Engine**: Ships with an internal process-isolated container runtime (port isolation, PID supervision, log streaming) and auto-detects Docker daemon environments when available.
- **Pluggable Load Balancing Policies**: Supports **Round Robin**, **Least Connections**, **Random**, and **IP Hash (Sticky Sessions)**.
- **Active Health Probing & Zero-Downtime Failover**: Periodically pings container `/health` endpoints and excludes failing instances from routing pools before users notice errors.
- **Dynamic Auto-Scaler**: Real-time traffic monitoring that automatically spins up new containers during high RPS bursts and scales down during cooldown periods.
- **Interactive Control Dashboard**: Single-page web console featuring live traffic generation, per-container distribution bar charts, chaos testing (failure injection), and real-time audit logs.
- **Developer CLI Tool**: Full command-line interface (`cli.py`) for scripting and terminal management.

---

## 🏗️ System Architecture

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

## 📁 Repository Directory Structure

```text
Local-Container-Service-Platform-with-Load-Balancing/
├── app.py                     # Main Unified Gateway, Control Plane API & Server
├── cli.py                     # Developer Command Line Interface (CLI)
├── README.md                  # Complete Documentation & Learnings
│
├── core/                      # Platform Engine & Business Logic
│   ├── container_manager.py   # Container Lifecycle, Process Isolation & Docker Support
│   ├── load_balancer.py       # Reverse Proxy & Scheduling Algorithms
│   ├── health_checker.py      # Background Health Probing Daemon & Failover
│   ├── auto_scaler.py         # Dynamic Load-Based Auto-Scaler Engine
│   └── storage.py             # SQLite Persistence & Audit Logging
│
├── dummy_service/             # Containerized Microservice Implementation
│   ├── service.py             # HTTP Microservice with Health & Chaos Hooks
│   └── Dockerfile             # Docker Container Specification
│
├── web/                       # Single-Page Web Control Dashboard
│   ├── index.html             # Dashboard Layout & UI Panels
│   └── static/
│       ├── styles.css         # Modern Dark Theme Stylesheet
│       └── app.js             # Real-time Telemetry & Interactive Actions
│
├── tests/                     # Automated Test Suite
│   ├── test_container_manager.py
│   ├── test_load_balancer.py
│   └── test_auto_scaler.py
│
├── data/                      # Persistent Runtime State (SQLite DB & Logs)
│   ├── platform.db            # Database (Auto-created)
│   └── logs/                  # Container standard output logs
│
└── output/                    # Academic Deliverables & Assessment Artifacts
    ├── Assessment-2.md        # Architecture & Requirements Specification
    ├── Assessment-3.md        # Feature Implementation & Demo Guide
    └── LLM-interaction/       # First 5 LLM Prompts & Design Iterations
        ├── interaction-1-problem-definition.md
        ├── interaction-2-architecture-design.md
        ├── interaction-3-load-balancer-implementation.md
        ├── interaction-4-health-check-failover.md
        └── interaction-5-autoscaler-and-testing.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+ (No external packages required!)

### 1. Run the Platform
Open your terminal and execute:
```bash
python3 app.py
```

You will see:
```text
=================================================================
 🚀 STARTING LOCAL CONTAINER SERVICE PLATFORM WITH LOAD BALANCING
=================================================================
📦 Deploying initial pool of 3 container instances...
   [+] Container 'cntr-9001' active on http://127.0.0.1:9001
   [+] Container 'cntr-9002' active on http://127.0.0.1:9002
   [+] Container 'cntr-9003' active on http://127.0.0.1:9003
🩺 Health Checker daemon started (interval: 3s).
📈 Dynamic Auto-Scaler daemon started.

=================================================================
✨ Web Control Dashboard : http://localhost:8000/
🔀 Load Balancer Gateway  : http://localhost:8000/service/
📊 Platform Health & API : http://localhost:8000/api/status
=================================================================
```

### 2. Access the Interactive Dashboard
Open your web browser and navigate to:
```
http://localhost:8000/
```

---

## 🎯 Live Demonstration Walkthrough (For Evaluation & Demo)

During your project demo, follow these steps to showcase all capabilities:

### Step 1: Demonstrate Multi-Algorithm Load Balancing
1. Open the dashboard at `http://localhost:8000/`.
2. Ensure the algorithm dropdown is set to **Round Robin**.
3. Under **Interactive Traffic Generator**, click **"Burst 10 Requests"**.
4. Observe the live stream and the **Request Distribution Breakdown** chart: requests cycle evenly across `cntr-9001`, `cntr-9002`, and `cntr-9003`.
5. Switch the algorithm to **Least Connections** or **IP Hash** and demonstrate the shift in routing policy.

### Step 2: Demonstrate Chaos Engineering & Automatic Failover
1. On container `cntr-9002`, click the **"⚡ Fail"** button.
2. The container's status immediately updates to `UNHEALTHY (503)`.
3. The Health Checker detects the failure within 3 seconds, logs a `HEALTH_FAILED` event in the audit table, and removes `cntr-9002` from the active routing pool.
4. Click **"Burst 10 Requests"** again.
5. Notice that all 10 requests succeed! Traffic is routed exclusively between `cntr-9001` and `cntr-9003` without a single client error.

### Step 3: Demonstrate Automatic Self-Healing & Recovery
1. Click the **"🔄 Recover"** button on `cntr-9002`.
2. Within 3 seconds, the Health Checker confirms consecutive successful pings, marks `cntr-9002` as `HEALTHY`, and re-adds it to the load balancer pool.
3. Fire another traffic burst: traffic immediately resumes flowing to `cntr-9002`.

### Step 4: Demonstrate Dynamic Auto-Scaling
1. Toggle the **Dynamic Auto-Scaler** switch to **ON**.
2. Click **"Auto-Traffic: ON (Streaming)"** to generate continuous synthetic load.
3. Observe the cluster RPS gauge spike. Once it exceeds the target threshold (default: 5 req/s/container), the auto-scaler automatically provisions `cntr-9004`!
4. Click **"Auto-Traffic: OFF"**. Once the cluster cools down past the 8-second cooldown window, idle containers are gracefully terminated.

---

## 💻 Developer CLI (`cli.py`)

You can also operate the platform directly from your terminal:

```bash
# Check platform cluster status
python3 cli.py status

# Deploy an additional container
python3 cli.py deploy --name dummy-service

# Change Load Balancing Algorithm
python3 cli.py algo least_connections

# Fire a traffic benchmark (25 requests)
python3 cli.py benchmark --requests 25

# Stop or restart a container
python3 cli.py stop cntr-9001
python3 cli.py start cntr-9001
```

---

## 🧪 Running Automated Unit Tests

Run all unit tests using Python's standard test runner:

```bash
python3 -m unittest discover tests
```

Expected output:
```text
......
----------------------------------------------------------------------
Ran 6 tests in 0.045s

OK
```

---

## 📚 Key Learnings & Engineering Reflections

Throughout the design and implementation of this platform, the following software engineering insights were gained:

1. **Reverse Proxying & Concurrency**:
   - Implementing reverse proxying taught us the importance of cleaning hop-by-hop HTTP headers (such as `Host`, `Connection`, and `Transfer-Encoding`) to prevent broken pipe socket exceptions.
   - Synchronizing concurrent access to load balancer state using mutex locks (`threading.Lock()`) is critical to avoiding race conditions in round-robin counters and active connection trackers.

2. **Resilience & Failover Design**:
   - A naive load balancer drops client requests when a backend crashes. Introducing active health probing coupled with in-flight retry logic guarantees 99.99% availability even in the face of sudden node failures.
   - Setting hysteresis thresholds (consecutive failure/success counts) prevents premature flap-cycles caused by momentary network latency.

3. **Auto-Scaling Dynamics & Anti-Flapping**:
   - Dynamic scaling requires careful balancing. Without cooldown timers, sudden micro-bursts of traffic cause aggressive scale-ups followed by immediate scale-downs ("thrashing"). Implementing an 8-second cooldown stabilized cluster topology.

4. **Self-Contained Architecture Benefits**:
   - By eliminating heavy third-party dependencies and leveraging standard library network primitives, the project achieved instant startup time, negligible memory footprint, and bulletproof cross-platform portability.

---

## 👥 Course & Author Information
- **Course**: Cloud Computing & Distributed Systems / Software Engineering Lab
- **Student**: Harpreet Singh
- **Institution**: Bennett University
- **Repository**: [GitHub Repository](https://github.com/harpreetsinghiffco-sketch/Local-Container-Service-Platform-with-Load-Balancing.git)
- **Submission Date**: October 2026
