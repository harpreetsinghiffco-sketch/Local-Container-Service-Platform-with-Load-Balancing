# LLM Interaction 1: Problem Definition & Requirement Scoping

**Date & Time**: 2026-09-24 10:15:00 UTC  
**Participant**: Student (Harpreet Singh) & AI Assistant (Antigravity)  
**Topic**: Scoping Topic 24 - Local Container Service Platform with Load Balancing

---

### User Prompt:
> I have been assigned Project Topic 24: "Local Container Service Platform with Load Balancing". The requirement states: "Develop a platform that deploys multiple instances of a dummy service across local containers and distributes requests using a load-balancing strategy. Students can additionally implement service health checking and automatic scaling as advanced features."
> Can you help me break down what this means, what the core deliverables should be for Assessment-2 and Assessment-3, and recommend a tech stack that will run cleanly on my local machine without breaking dependencies?

---

### AI Response Summary:
To build a standout, robust submission, the project should be divided into distinct modular layers:
1. **Container Abstraction**: A management engine that deploys isolated dummy microservices locally. We should support process-isolated local containers with dedicated port namespaces and lifecycle states (RUNNING, STOPPED, FAILED), while also providing Dockerfile support if Docker is installed.
2. **Reverse Proxy Load Balancer**: A gateway that intercepts incoming client requests and applies load balancing algorithms (Round Robin, Least Connections, Random, and IP Hash).
3. **Advanced Features**:
   - Automated Health Checking (probing `/health`, detecting failure, and dropping unhealthy instances from the proxy pool).
   - Dynamic Auto-Scaling (monitoring cluster requests-per-second and spinning up/down containers).
   - Interactive Web Dashboard (allowing evaluators to visually test routing and observe health changes in real time).
4. **Recommended Tech Stack**:
   - **Language**: Python 3 standard library (`http.server`, `urllib`, `threading`, `sqlite3`, `json`). This ensures the evaluator can run the project on any computer with 0 dependency errors.
   - **Frontend**: Clean modern HTML/CSS/JavaScript with real-time polling.
   - **Persistence**: SQLite for tracking container state and audit events.

---

### Key Decisions Made:
- Chose standard library Python with zero external pip dependencies to ensure 100% demo reliability.
- Decided to implement a multi-algorithm load balancer rather than just a single basic round robin.
- Planned a dedicated failure injection mechanism (`/simulate/fail`) so the health checker's auto-failover can be demonstrated live in front of the professor.
