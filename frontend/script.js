const API_BASE = (() => {
  // Check if running on localhost
  if (window.location.hostname === 'localhost' || 
      window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000/api/v1';
  }
  
  // Production: try to detect from environment or use default
  // Can be overridden by setting window.PULSEOPS_API_URL before script loads
  if (window.PULSEOPS_API_URL) {
    return window.PULSEOPS_API_URL;
  }
  
  // Fallback: use same origin with /api/v1 path
  return `${window.location.origin}/api/v1`;
})();

let activeEventSource = null;
let taskCount = 0;

const taskInput = document.getElementById("taskInput");
const submitBtn = document.getElementById("submitBtn");
const charCount = document.getElementById("charCount");
const progressLog = document.getElementById("progressLog");
const progressBarFill = document.getElementById("progressBarFill");
const progressBarGlow = document.getElementById("progressBarGlow");
const outputBlock = document.getElementById("outputBlock");
const statusDot = document.getElementById("connectionStatus");
const statusLabel = document.getElementById("statusLabel");
const taskIdDisplay = document.getElementById("taskIdDisplay");
const copyBtn = document.getElementById("copyBtn");
const clearBtn = document.getElementById("clearBtn");
const footerTaskCount = document.getElementById("footerTaskCount");

taskInput.addEventListener("input", () => {
  charCount.textContent = taskInput.value.length;
});

function setStatus(type, label) {
  statusDot.className = "status-dot " + type;
  statusLabel.textContent = label;
}

function showToast(message) {
  const old = document.querySelector(".toast");
  if (old) old.remove();

  const div = document.createElement("div");
  div.className = "toast";
  div.textContent = message;

  document.body.appendChild(div);

  setTimeout(() => div.remove(), 2500);
}

function addLog(message, cls = "") {
  const placeholder = progressLog.querySelector(".log-placeholder");
  if (placeholder) placeholder.remove();

  const row = document.createElement("div");
  row.className = `log-entry ${cls}`;

  const time = new Date().toLocaleTimeString();

  row.innerHTML = `
    <span class="log-time">${time}</span>
    <span>${message}</span>
  `;

  progressLog.appendChild(row);
  progressLog.scrollTop = progressLog.scrollHeight;
}

function setProgress(value) {
  progressBarFill.style.width = value + "%";
  progressBarGlow.style.opacity =
    value > 0 && value < 100 ? "1" : "0";
}

function resetOutput() {
  outputBlock.innerHTML =
    '<span class="output-placeholder">Final result will appear here once task completes.</span>';

  copyBtn.style.display = "none";
  clearBtn.style.display = "none";
}

function clearAll() {
  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }

  progressLog.innerHTML =
    '<div class="log-placeholder"><p>No active task.</p></div>';

  resetOutput();
  setProgress(0);
  setStatus("", "IDLE");

  submitBtn.disabled = false;
  submitBtn.classList.remove("loading");
}

function copyOutput() {
  navigator.clipboard.writeText(outputBlock.innerText);
  showToast("Copied to clipboard");
}

async function submitTask() {
  const text = taskInput.value.trim();

  if (!text) {
    showToast("Enter task first");
    return;
  }

  clearAll();

  submitBtn.disabled = true;
  submitBtn.classList.add("loading");

  setStatus("waiting", "DISPATCHING");

  try {
    const res = await fetch(`${API_BASE}/task`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        request: text
      })
    });

    if (!res.ok) {
      throw new Error("Failed to submit task");
    }

    const data = await res.json();

    taskCount++;
    footerTaskCount.textContent =
      `${taskCount} task${taskCount > 1 ? "s" : ""} dispatched`;

    taskIdDisplay.textContent = data.task_id;
    addLog("Task accepted", "info");

    setStatus("active", "RUNNING");
    setProgress(10);

    openStream(data.task_id);

  } catch (err) {
    addLog(err.message, "error");
    setStatus("error", "FAILED");

    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
  }
}

function openStream(taskId) {
  let completed = false;
  const es = new EventSource(`${API_BASE}/stream/${taskId}`);
  activeEventSource = es;

  es.onopen = () => {
    addLog("Live connection established", "success");
    setStatus("active", "STREAMING");
  };

  es.addEventListener("task_started", (event) => {
    const payload = JSON.parse(event.data);
    addLog(payload.message || "Task started");
  });

  es.addEventListener("plan_ready", (event) => {
    const payload = JSON.parse(event.data);
    addLog(payload.message || "Plan ready");
  });

  es.addEventListener("step_started", (event) => {
    const payload = JSON.parse(event.data);
    addLog(payload.message || "Step started");
  });

  es.addEventListener("step_progress", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.data && payload.data.token) {
      addLog(payload.data.token);
    }
  });

  es.addEventListener("step_completed", (event) => {
    const payload = JSON.parse(event.data);
    addLog(payload.message || "Step completed");
  });

  es.addEventListener("step_failed", (event) => {
    const payload = JSON.parse(event.data);
    addLog(payload.message || "Step failed", "error");
  });

  es.addEventListener("task_completed", (event) => {
    const payload = JSON.parse(event.data);
    completed = true;
    
    const result = payload.data?.result || payload.data?.final_output || "Completed";
    completeTask(result);
    
    es.close();
  });

  es.addEventListener("task_failed", (event) => {
    const payload = JSON.parse(event.data);
    completed = true;
    
    addLog(payload.message || "Task failed", "error");
    setStatus("error", "FAILED");
    
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
    
    es.close();
  });

  es.onerror = () => {
    if (!completed) {
      addLog("Connection closed", "error");
      setStatus("error", "DISCONNECTED");
      submitBtn.disabled = false;
      submitBtn.classList.remove("loading");
    }
    es.close();
  };
}

function handlePayload(raw) {
  try {
    const payload = JSON.parse(raw);

    if (payload.message) addLog(payload.message);

    if (payload.progress) setProgress(payload.progress);

    if (payload.result) completeTask(payload.result);

  } catch {
    addLog(raw);
  }
}

function completeTask(result) {
  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }

  setProgress(100);
  setStatus("active", "COMPLETE");

  addLog("Task completed", "success");

  outputBlock.textContent = result;

  copyBtn.style.display = "flex";
  clearBtn.style.display = "flex";

  submitBtn.disabled = false;
  submitBtn.classList.remove("loading");

  showToast("Task complete");
}

taskInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    submitTask();
  }
});

setStatus("", "IDLE");