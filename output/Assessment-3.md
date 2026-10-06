# Project Assessment 3: End-to-End Feature Implementation & Demonstration

## 1. Crucial Features Identified for In-Depth Implementation
In accordance with Assessment 3 guidelines emphasizing deep, complete implementations over superficial breadth, this submission focuses on two core mission-critical features:

1. **End-to-End Dynamic Load Balancing & Traffic Routing**:
   - Implementing multiple scheduling algorithms (Round Robin, Least Connections, Random, IP Hash).
   - Real-time HTTP reverse proxying from UI/gateway to containerized microservice backends.
   - Comprehensive telemetry measuring per-container request distribution and response latency.

2. **Automated Health Probing & Fault-Tolerant Failover**:
   - Continuous background health checking against all running containers.
   - Fault injection mechanism (`/simulate/fail`) to mimic real-world container crashes.
   - Immediate exclusion of unhealthy containers from the load balancer pool with zero dropped requests (automated retry/reroute).
   - Auto-recovery detection that seamlessly reinstates containers once healthy.

---

## 2. End-to-End Implementation: UI to Business Logic

### A. User Interface (UI Layer)
- **Interactive Traffic Generator**:
  - The UI provides immediate buttons to fire 1 request, 10 requests, 25 requests, or continuous background streaming.
  - As requests are dispatched, the response stream displays:
    - HTTP Status Code (`200 OK`, `503 Service Unavailable`, `502 Bad Gateway`).
    - The exact container instance that handled the request (`cntr-9001`, `cntr-9002`, etc.).
    - Round-trip latency in milliseconds.
- **Visual Distribution Chart**:
  - Real-time proportional progress bars showing the exact count and percentage of requests processed by each container.
- **Failure Injection & Recovery Controls**:
  - Each container card includes a **"⚡ Fail"** button to simulate instance breakdown and a **"🔄 Recover"** button to simulate repair.

### B. Gateway & API Layer (`app.py`)
- Maps inbound traffic from `/service/*` to the `LoadBalancer.forward_request()` handler.
- Adds tracing headers (`X-Served-By-Container`, `X-LB-Algorithm`).
- Exposes REST control endpoints for container lifecycle, load balancer algorithm switches, and health checks.

### C. Core Business Logic (`core/load_balancer.py`, `core/health_checker.py`, `core/auto_scaler.py`)
- **Algorithm Execution**:
  - `Round Robin`: Statefully cycles through healthy instances using an atomic counter modulo the pool size.
  - `Least Connections`: Dynamically inspects `active_connections` across all containers and selects the container with minimum concurrent load.
  - `IP Hash`: Derives a hash of the client's IP address to ensure sticky sessions.
- **Failover Logic**:
  - When an upstream container responds with `503` or encounters a network timeout, the load balancer automatically reroutes the request to another healthy container within the same client request cycle.
- **Health Checker Daemon**:
  - Polls `/health` on each container every 3 seconds.
  - Maintains consecutive success/failure counters with configurable thresholds (default 2) to eliminate false positives.

### D. Microservice Layer (`dummy_service/service.py`)
- Lightweight HTTP microservice that tracks internal request counts, responds to `/health` queries, and supports test hooks for failure injection and artificial latency simulation.

---

## 3. Testing and Sound Functioning Verification

The platform has been verified with comprehensive unit and integration tests:
1. `tests/test_load_balancer.py`:
   - Validates Round Robin cyclic ordering across instances.
   - Validates Least Connections selection with uneven loads.
   - Validates IP Hash stickiness consistency.
   - Confirms unhealthy containers are strictly excluded from the routing pool.
2. `tests/test_container_manager.py`:
   - Validates automated non-conflicting port allocation.
   - Verifies container lifecycle transitions (start, stop, remove).
3. `tests/test_auto_scaler.py`:
   - Validates minimum instance constraint enforcement.
   - Tests traffic threshold evaluation for scale-up events.

---

## 4. Live Demo Walkthrough (For October 07, 2026 Evaluation)

### Step 1: Launch the Platform
```bash
python3 app.py
```
- Open browser at `http://localhost:8000/`.
- Verify 3 default containers (`cntr-9001`, `cntr-9002`, `cntr-9003`) are in `HEALTHY` state.

### Step 2: Demonstrate Round Robin Load Balancing
- Set Algorithm dropdown to **"Round Robin"**.
- Click **"Burst 10 Requests"**.
- Point out the traffic stream and distribution bars: requests are distributed evenly (e.g. 4, 3, 3) across `cntr-9001`, `cntr-9002`, and `cntr-9003`.

### Step 3: Demonstrate Fault Injection & Automatic Failover
- On `cntr-9002`, click the **"⚡ Fail"** button.
- Status updates to `UNHEALTHY (503)`.
- The Health Checker immediately logs the failure in the Platform Audit Event Log.
- Click **"Burst 10 Requests"** again.
- Notice that **zero requests** are sent to `cntr-9002`! The load balancer transparently routes all requests between `cntr-9001` and `cntr-9003` with 100% success rate.

### Step 4: Demonstrate Auto-Recovery
- Click **"🔄 Recover"** on `cntr-9002`.
- Within 3 seconds, the Health Checker detects the healthy response, marks it `HEALTHY`, and re-adds it to the load balancer pool.
- Send another burst: traffic seamlessly resumes routing to `cntr-9002`.

### Step 5: Demonstrate Auto-Scaling
- Toggle **Dynamic Auto-Scaler** to `ON`.
- Click **"Auto-Traffic: ON (Streaming)"** to generate continuous load.
- Observe cluster RPS rise: once it exceeds the target threshold, a new container (e.g. `cntr-9004`) is automatically spawned!
