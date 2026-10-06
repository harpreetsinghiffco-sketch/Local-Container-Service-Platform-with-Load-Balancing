# LLM Interaction 5: Dynamic Auto-Scaling, CLI, and Automated Unit Testing

**Date & Time**: 2026-10-06 09:10:00 UTC  
**Participant**: Student (Harpreet Singh) & AI Assistant (Antigravity)  
**Topic**: Finalizing Auto-Scaling Policies, Developer CLI, and Unit Test Suite

---

### User Prompt:
> For the final submission (Assessment-3) and live demo on October-07, how do we implement the auto-scaling feature, build automated unit tests, and create a CLI tool so I can demonstrate the project from both the browser and terminal?

---

### AI Response Summary:
We finalized the system with three key components:
1. **Dynamic Auto-Scaler (`core/auto_scaler.py`)**:
   - Calculates cluster-wide requests per second (RPS) over a sliding sampling window.
   - Scale-Up Trigger: If `RPS > healthy_instances * target_rps`, spawns new container instances up to `max_instances`.
   - Scale-Down Trigger: If `RPS < (healthy_instances - 1) * target_rps * 0.5` after a cooldown window, gracefully terminates the container with the lowest historical load.
   - Cooldown Timer: 8-second delay prevents flapping (rapid oscillating scale-ups and scale-downs).
2. **Command Line Tool (`cli.py`)**:
   - Implemented subcommands: `status`, `deploy`, `stop`, `start`, `rm`, `algo`, `benchmark`.
3. **Automated Unit Testing (`tests/`)**:
   - Built unit tests for load balancer algorithms, pool exclusions, container port allocations, and autoscaler scale triggers.

---

### Key Decisions Made:
- Made Auto-Scaling toggleable from both the UI and CLI so it can be demonstrated on-demand during the evaluation.
- Added a traffic burst tool in the web UI and CLI benchmark tool (`cli.py benchmark --requests 20`) to easily trigger scale events during presentations.
