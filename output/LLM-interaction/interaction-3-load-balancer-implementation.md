# LLM Interaction 3: Load Balancer Algorithms & Proxy Forwarding

**Date & Time**: 2026-10-01 16:45:00 UTC  
**Participant**: Student (Harpreet Singh) & AI Assistant (Antigravity)  
**Topic**: Implementing the Core Reverse Proxy and Scheduling Algorithms

---

### User Prompt:
> Can you show me how to implement the actual Load Balancer algorithms in Python? I need Round Robin, Least Connections, Random, and IP Hash. How do we ensure thread-safety when multiple requests arrive concurrently, and how does the reverse proxy forward requests to the chosen container?

---

### AI Response Summary:
We implemented the `LoadBalancer` class with atomic synchronization:
1. **Thread Safety**: Protected internal state (`rr_index`, `active_connections`, metrics) with Python `threading.Lock()`.
2. **Algorithm Implementations**:
   - `round_robin`: Uses `self.rr_index % len(healthy_instances)`, followed by `self.rr_index += 1`.
   - `least_connections`: Uses Python's `min(healthy_instances, key=lambda inst: inst.active_connections)`.
   - `random`: Employs `random.choice(healthy_instances)`.
   - `ip_hash`: Hashes the client IP with MD5, converts to integer, and computes modulo over healthy instance count for sticky sessions.
3. **HTTP Reverse Proxying**:
   - Strips hop-by-hop headers (`host`, `connection`, `transfer-encoding`).
   - Injects tracing headers (`X-Forwarded-For`, `X-Load-Balancer-Algo`).
   - Uses `urllib.request.urlopen` with a 3.0s timeout.
   - Measures start-to-finish request latency and updates per-container stats.

---

### Key Decisions Made:
- Incorporated automatic retries with alternative healthy containers if the primary target throws an HTTP 503 or network socket error.
- Maintained a rolling 50-item request log for real-time visualization on the web UI.
