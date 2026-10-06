/**
 * Frontend Application Controller for Container Service Platform
 * Real-time polling, interactive traffic tester, container control, and metric updates
 */

let autoTrafficInterval = null;
let isStreamingTraffic = false;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  fetchPlatformStatus();
  fetchAuditLogs();

  // Poll platform state every 2 seconds for live real-time updates
  setInterval(fetchPlatformStatus, 2000);
  setInterval(fetchAuditLogs, 4000);
});

async function fetchPlatformStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error("Status API returned " + res.status);
    const data = await res.json();
    renderMetrics(data);
    renderContainers(data.instances, data.load_balancer);
    renderDistribution(data.load_balancer);
    renderAutoScaler(data.auto_scaler);
  } catch (err) {
    console.error("Failed to fetch platform status:", err);
    document.getElementById("gateway-status").innerText = "Gateway Offline";
    document.getElementById("gateway-status").parentElement.style.color = "#ef4444";
  }
}

function renderMetrics(data) {
  const lb = data.load_balancer || {};
  const instances = data.instances || [];
  const healthyCount = instances.filter(i => i.status === "RUNNING" && i.health_status === "HEALTHY").length;
  const runningCount = instances.filter(i => i.status === "RUNNING").length;

  document.getElementById("val-active-containers").innerHTML = `${runningCount} <span class="metric-sub">/ ${instances.length} total</span>`;
  document.getElementById("val-healthy-pill").innerHTML = `🩺 <strong>${healthyCount}</strong> healthy backend${healthyCount === 1 ? '' : 's'}`;

  // Algorithm dropdown
  const algoSelect = document.getElementById("algo-select");
  if (algoSelect && lb.algorithm && algoSelect.value !== lb.algorithm) {
    algoSelect.value = lb.algorithm;
  }

  // Algorithm description
  const algoDescriptions = {
    round_robin: "Sequential cyclic distribution across healthy containers",
    least_connections: "Routes traffic to container with lowest active load",
    random: "Uniform random selection across healthy cluster pool",
    ip_hash: "Client IP hash sticky routing for session persistence"
  };
  document.getElementById("val-algo-desc").innerText = algoDescriptions[lb.algorithm] || "Active load balancing policy";

  // Request stats
  document.getElementById("val-total-requests").innerText = (lb.total_requests || 0).toLocaleString();
  document.getElementById("val-success-requests").innerText = (lb.successful_requests || 0).toLocaleString();
  document.getElementById("val-failed-requests").innerText = (lb.failed_requests || 0).toLocaleString();

  // AutoScaler RPS
  const rps = (data.auto_scaler && data.auto_scaler.current_rps !== undefined) ? data.auto_scaler.current_rps : 0.0;
  document.getElementById("val-current-rps").innerText = rps.toFixed(1);

  // Compute avg latency
  let totalLatency = 0;
  let sampleCount = 0;
  if (lb.distribution) {
    for (const id in lb.distribution) {
      const item = lb.distribution[id];
      if (item.requests > 0 && item.avg_latency_ms > 0) {
        totalLatency += item.avg_latency_ms * item.requests;
        sampleCount += item.requests;
      }
    }
  }
  const avgLat = sampleCount > 0 ? (totalLatency / sampleCount).toFixed(1) : "0.0";
  document.getElementById("val-avg-latency").innerText = `${avgLat} ms`;
}

function renderContainers(instances, lbStats) {
  const fleetEl = document.getElementById("container-fleet-list");
  if (!instances || instances.length === 0) {
    fleetEl.innerHTML = `<div class="empty-state">No containers active. Click "+ Deploy Container" to start one!</div>`;
    return;
  }

  let html = "";
  instances.forEach(inst => {
    let pillClass = "pill-healthy";
    let pillText = "HEALTHY";

    if (inst.status !== "RUNNING") {
      pillClass = "pill-stopped";
      pillText = inst.status;
    } else if (inst.health_status === "UNHEALTHY") {
      pillClass = "pill-unhealthy";
      pillText = "UNHEALTHY (503)";
    }

    const requests = inst.requests_count || 0;
    const latency = inst.last_response_time_ms ? `${inst.last_response_time_ms}ms` : "-";

    html += `
      <div class="container-card">
        <div class="cntr-info">
          <div class="cntr-badge">${inst.id}</div>
          <div>
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.2rem;">
              <strong>Port :${inst.port}</strong>
              <span class="status-pill ${pillClass}">${pillText}</span>
              <span style="font-size:0.75rem; color:var(--text-dim);">[${inst.driver}]</span>
            </div>
            <div class="cntr-meta">
              Handled: <strong>${requests}</strong> requests • Latency: <strong>${latency}</strong> • Act Conns: <strong>${inst.active_connections || 0}</strong>
            </div>
          </div>
        </div>
        <div class="cntr-actions">
          ${inst.status === 'RUNNING' && inst.health_status === 'HEALTHY'
            ? `<button class="btn btn-warning btn-sm" onclick="simulateContainerFailure('${inst.id}')">⚡ Fail</button>`
            : (inst.status === 'RUNNING' ? `<button class="btn btn-success btn-sm" onclick="simulateContainerRecovery('${inst.id}')">🔄 Recover</button>` : '')
          }
          ${inst.status === 'RUNNING'
            ? `<button class="btn btn-secondary btn-sm" onclick="stopContainer('${inst.id}')">⏹ Stop</button>`
            : `<button class="btn btn-primary btn-sm" onclick="startContainer('${inst.id}')">▶ Start</button>`
          }
          <button class="btn btn-danger btn-sm" onclick="deleteContainer('${inst.id}')">🗑</button>
        </div>
      </div>
    `;
  });

  fleetEl.innerHTML = html;
}

function renderDistribution(lbStats) {
  const container = document.getElementById("distribution-chart-container");
  if (!lbStats || !lbStats.distribution || Object.keys(lbStats.distribution).length === 0) {
    container.innerHTML = `<div class="empty-state">No requests routed yet.</div>`;
    return;
  }

  const dist = lbStats.distribution;
  let maxRequests = 1;
  for (const id in dist) {
    if (dist[id].requests > maxRequests) maxRequests = dist[id].requests;
  }

  let html = "";
  for (const id in dist) {
    const item = dist[id];
    const pct = Math.round((item.requests / maxRequests) * 100);
    const isHealthy = item.health_status === "HEALTHY";

    html += `
      <div class="dist-bar-wrapper">
        <div class="dist-label-row">
          <span>${id} (: ${item.port}) ${!isHealthy ? '⚠️ [Out of Pool]' : ''}</span>
          <span><strong>${item.requests}</strong> reqs (${item.avg_latency_ms}ms avg)</span>
        </div>
        <div class="dist-bar-bg">
          <div class="dist-bar-fill" style="width: ${pct}%; ${!isHealthy ? 'background: #ef4444;' : ''}"></div>
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
}

function renderAutoScaler(as) {
  if (!as) return;
  const toggle = document.getElementById("autoscaler-toggle");
  if (toggle) toggle.checked = as.enabled;

  const minInput = document.getElementById("as-min");
  const maxInput = document.getElementById("as-max");
  const rpsInput = document.getElementById("as-target-rps");
  
  if (document.activeElement !== minInput) minInput.value = as.min_instances;
  if (document.activeElement !== maxInput) maxInput.value = as.max_instances;
  if (document.activeElement !== rpsInput) rpsInput.value = as.target_rps_per_instance;

  const statusBox = document.getElementById("scaler-status-text");
  statusBox.innerHTML = `
    Status: <strong style="color:${as.enabled ? '#10b981' : '#94a3b8'}">${as.enabled ? 'ACTIVE' : 'DISABLED'}</strong> • 
    Current RPS: <strong>${(as.current_rps || 0).toFixed(1)}</strong> • Target: <strong>${as.target_rps_per_instance} req/s/container</strong>
  `;
}

async function fetchAuditLogs() {
  try {
    const res = await fetch("/api/logs");
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById("events-log-tbody");
    if (!data.logs || data.logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center">No audit logs recorded yet.</td></tr>`;
      return;
    }

    let html = "";
    data.logs.slice(0, 15).forEach(l => {
      const timeStr = l.timestamp.split("T")[1]?.slice(0, 8) || l.timestamp;
      html += `
        <tr>
          <td style="font-family:var(--font-mono); color:var(--text-dim);">${timeStr}</td>
          <td><code>${l.event_type}</code></td>
          <td>${l.message}</td>
          <td style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">${l.details || '-'}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (e) {
    console.error(e);
  }
}

// Interactive Traffic Actions
async function fireTrafficBurst(count) {
  const streamEl = document.getElementById("traffic-results-stream");
  if (streamEl.querySelector(".empty-state")) streamEl.innerHTML = "";

  try {
    const res = await fetch("/api/traffic/burst", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count: count })
    });
    const data = await res.json();
    
    if (data.results) {
      data.results.forEach(r => {
        const item = document.createElement("div");
        item.className = `traffic-log-item ${r.status_code === 200 ? 'success' : 'fail'}`;
        item.innerHTML = `
          <span>[Req #${r.req_num}] HTTP ${r.status_code}</span>
          <span>Target: <strong>${r.served_by || 'NONE'}</strong> (:${r.port || '-'})</span>
          <span>Latency: ${r.latency_ms}ms</span>
        `;
        streamEl.prepend(item);
      });
    }

    // Keep stream tidy
    while (streamEl.children.length > 30) {
      streamEl.removeChild(streamEl.lastChild);
    }

    fetchPlatformStatus();
  } catch (err) {
    console.error(err);
  }
}

function toggleContinuousStream() {
  const btn = document.getElementById("btn-stream-toggle");
  if (isStreamingTraffic) {
    clearInterval(autoTrafficInterval);
    isStreamingTraffic = false;
    btn.innerText = "Auto-Traffic: OFF";
    btn.className = "btn btn-secondary";
  } else {
    isStreamingTraffic = true;
    btn.innerText = "Auto-Traffic: ON (Streaming)";
    btn.className = "btn btn-warning";
    autoTrafficInterval = setInterval(() => {
      fireTrafficBurst(3);
    }, 800);
  }
}

// Container Management Controls
async function deployNewContainer() {
  try {
    const res = await fetch("/api/containers/deploy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (!res.ok) alert(data.error || "Failed to deploy container");
    fetchPlatformStatus();
    fetchAuditLogs();
  } catch (err) {
    alert("Deploy error: " + err);
  }
}

async function stopContainer(id) {
  await fetch(`/api/containers/${id}/stop`, { method: "POST" });
  fetchPlatformStatus();
}

async function startContainer(id) {
  await fetch(`/api/containers/${id}/start`, { method: "POST" });
  fetchPlatformStatus();
}

async function deleteContainer(id) {
  if (confirm(`Terminate container ${id}?`)) {
    await fetch(`/api/containers/${id}`, { method: "DELETE" });
    fetchPlatformStatus();
  }
}

async function simulateContainerFailure(id) {
  await fetch(`/api/containers/${id}/simulate/fail`, { method: "POST" });
  fetchPlatformStatus();
  fetchAuditLogs();
}

async function simulateContainerRecovery(id) {
  await fetch(`/api/containers/${id}/simulate/recover`, { method: "POST" });
  fetchPlatformStatus();
  fetchAuditLogs();
}

// Algorithm Switch
async function changeAlgorithm(algo) {
  await fetch("/api/loadbalancer/algorithm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ algorithm: algo })
  });
  fetchPlatformStatus();
  fetchAuditLogs();
}

// AutoScaler Config
async function toggleAutoScaler(enabled) {
  await fetch("/api/autoscaler/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: enabled })
  });
  fetchPlatformStatus();
  fetchAuditLogs();
}

async function saveAutoScalerConfig() {
  const min = parseInt(document.getElementById("as-min").value);
  const max = parseInt(document.getElementById("as-max").value);
  const rps = parseFloat(document.getElementById("as-target-rps").value);
  await fetch("/api/autoscaler/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ min_instances: min, max_instances: max, target_rps: rps })
  });
  fetchPlatformStatus();
}

async function triggerHealthCheckNow() {
  await fetch("/api/health/check-now");
  fetchPlatformStatus();
  fetchAuditLogs();
}
