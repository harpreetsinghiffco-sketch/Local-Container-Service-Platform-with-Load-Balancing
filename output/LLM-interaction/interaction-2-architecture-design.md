# LLM Interaction 2: Architectural Design & Component Interfaces

**Date & Time**: 2026-09-27 14:30:00 UTC  
**Participant**: Student (Harpreet Singh) & AI Assistant (Antigravity)  
**Topic**: High-level Architecture for Assessment-2 Submission

---

### User Prompt:
> For Assessment-2, I need to define the major components (UI, Logic, Persistence), the architecture diagram, and describe the interfaces (APIs, CLI). How should the components interact so that requests flow seamlessly from the browser to the dummy services?

---

### AI Response Summary:
We designed a 3-tier architecture:
1. **Control & Ingress Plane (`app.py`)**:
   - Runs on port 8000.
   - Dual-purpose server:
     - Serves the Single-Page Web UI and static assets (`/`, `/static/*`).
     - Exposes REST API for container control (`/api/containers/*`, `/api/status`, `/api/traffic/burst`).
     - Serves as the Load Balanced Ingress Gateway (`/service/*`), proxying requests to backends.
2. **Container Engine & Scheduling Layer (`core/`)**:
   - `container_manager.py`: Allocates ports from pool (9001-9099), tracks PIDs, and manages lifecycle.
   - `load_balancer.py`: Dispatches requests using pluggable algorithms and manages client sessions.
   - `health_checker.py`: Background daemon maintaining a health map of all containers.
   - `auto_scaler.py`: Background daemon checking RPS against capacity limits.
3. **Persistence Layer (`core/storage.py`)**:
   - SQLite database storing container registries, metrics, and audit event logs.

---

### Key Decisions Made:
- Separated control plane routes (`/api/*`) from data plane proxy routes (`/service/*`) to prevent routing collision.
- Used HTTP headers (`X-Served-By-Container`, `X-LB-Algorithm`) in responses so clients and the UI can instantly verify which backend processed each request.
- Designed an audit log system to preserve history of all failures and scaling events.
