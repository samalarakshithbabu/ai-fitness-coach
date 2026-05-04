/**
 * app.js  –  AI Fitness Coach Frontend
 * Communicates with the FastAPI backend at /api (proxied) or direct localhost.
 */

const API = "http://localhost:8000";

// ── Tab switching ─────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach(t => {
      t.classList.remove("active");
      t.classList.add("hidden");
    });
    btn.classList.add("active");
    const target = document.getElementById(`tab-${btn.dataset.tab}`);
    target.classList.remove("hidden");
    target.classList.add("active");
  });
});

// ── File upload & preview ─────────────────────────────────────────────────────
const dropZone   = document.getElementById("dropZone");
const fileInput  = document.getElementById("fileInput");
const imgPreview = document.getElementById("imgPreview");
const vidPreview = document.getElementById("vidPreview");
const previewBox = document.getElementById("previewBox");
const analyzeBtn = document.getElementById("analyzeBtn");

let selectedFile = null;

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

function handleFile(file) {
  selectedFile = file;
  const url = URL.createObjectURL(file);

  if (file.type.startsWith("image/")) {
    imgPreview.src = url;
    imgPreview.classList.remove("hidden");
    vidPreview.classList.add("hidden");
  } else {
    vidPreview.src = url;
    vidPreview.classList.remove("hidden");
    imgPreview.classList.add("hidden");
  }

  previewBox.classList.remove("hidden");
  analyzeBtn.classList.remove("hidden");
  document.getElementById("results").classList.add("hidden");
}

// ── Analyze ───────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  showLoader(true);
  document.getElementById("results").classList.add("hidden");

  const formData = new FormData();
  formData.append("file", selectedFile);

  const endpoint = selectedFile.type.startsWith("image/")
    ? `${API}/upload-image`
    : `${API}/upload-video`;

  try {
    const res  = await fetch(endpoint, { method: "POST", body: formData });
    const data = await res.json();
    showLoader(false);
    renderResults(data);
  } catch (err) {
    showLoader(false);
    alert("Error connecting to backend. Make sure the server is running on port 8000.");
    console.error(err);
  }
});

function showLoader(show) {
  document.getElementById("loader").classList.toggle("hidden", !show);
  analyzeBtn.disabled = show;
}

function renderResults(data) {
  const results = document.getElementById("results");
  results.classList.remove("hidden");

  // Exercise name & confidence
  const exercise = data.exercise || data.top_exercise || "unknown";
  document.getElementById("exerciseName").textContent =
    exercise.replace(/_/g, " ");
  document.getElementById("confidenceBadge").textContent =
    data.confidence ? `${(data.confidence * 100).toFixed(1)}% confidence` : "";

  // Score ring — must set dasharray before animating dashoffset
  const score = data.posture?.score ?? data.average_score ?? 0;
  document.getElementById("scoreText").textContent = score;
  const circumference = 2 * Math.PI * 50; // r=50 → ~314.16
  const offset = circumference - (score / 100) * circumference;
  const ring = document.getElementById("ringFill");
  ring.style.strokeDasharray = circumference;
  ring.style.strokeDashoffset = circumference; // start at 0
  // Trigger animation on next frame
  setTimeout(() => { ring.style.strokeDashoffset = offset; }, 50);
  ring.style.stroke = score >= 80 ? "var(--accent2)" : score >= 50 ? "#f6c90e" : "var(--danger)";

  // Feedback message
  const msg = data.feedback || (data.posture?.is_correct ? "Great form!" : "Check your posture.");
  document.getElementById("feedbackMsg").textContent = msg;

  // Issues
  const issues = data.posture?.issues || data.issues || [];
  const issuesDiv = document.getElementById("issuesList");
  const issuesUl  = document.getElementById("issuesUl");
  issuesUl.innerHTML = "";
  if (issues.length) {
    issues.forEach(i => {
      const li = document.createElement("li");
      li.textContent = i;
      issuesUl.appendChild(li);
    });
    issuesDiv.classList.remove("hidden");
  } else {
    issuesDiv.classList.add("hidden");
  }

  // Suggestions
  const suggestions = data.posture?.suggestions || [];
  const sugDiv = document.getElementById("suggestionsList");
  const sugUl  = document.getElementById("suggestionsUl");
  sugUl.innerHTML = "";
  if (suggestions.length) {
    suggestions.forEach(s => {
      const li = document.createElement("li");
      li.textContent = s;
      sugUl.appendChild(li);
    });
    sugDiv.classList.remove("hidden");
  } else {
    sugDiv.classList.add("hidden");
  }
}

// ── Recommendation form ───────────────────────────────────────────────────────
document.getElementById("profileForm").addEventListener("submit", async e => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("age",          document.getElementById("age").value);
  formData.append("weight_kg",    document.getElementById("weight").value);
  formData.append("height_cm",    document.getElementById("height").value);
  formData.append("fitness_goal", document.getElementById("goal").value);

  try {
    const res  = await fetch(`${API}/get-recommendation`, { method: "POST", body: formData });
    const data = await res.json();
    renderPlan(data);
  } catch (err) {
    alert("Error connecting to backend.");
    console.error(err);
  }
});

function renderPlan(data) {
  document.getElementById("planResults").classList.remove("hidden");

  document.getElementById("planLevel").textContent = data.level;
  document.getElementById("planBmi").textContent   = `BMI: ${data.bmi_category}`;
  document.getElementById("planSchedule").textContent = `📅 ${data.weekly_schedule}`;
  document.getElementById("planHighlight").textContent = data.highlight || "";

  // Exercise table
  const tbody = document.getElementById("exerciseTbody");
  tbody.innerHTML = "";
  data.exercises.forEach(ex => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${ex.name}</td><td>${ex.sets}</td><td>${ex.reps}</td><td>${ex.rest}</td>`;
    tbody.appendChild(tr);
  });

  // Tips
  const tipsList = document.getElementById("tipsList");
  tipsList.innerHTML = "";
  data.tips.forEach(tip => {
    const li = document.createElement("li");
    li.textContent = tip;
    tipsList.appendChild(li);
  });
}

// ── History ───────────────────────────────────────────────────────────────────
document.getElementById("loadHistoryBtn").addEventListener("click", async () => {
  try {
    const res  = await fetch(`${API}/history`);
    const data = await res.json();
    renderHistory(data.history);
  } catch (err) {
    alert("Error loading history.");
    console.error(err);
  }
});

function renderHistory(history) {
  const container = document.getElementById("historyList");
  container.innerHTML = "";

  if (!history.length) {
    container.innerHTML = "<p style='color:var(--muted)'>No sessions recorded yet.</p>";
    return;
  }

  history.forEach(item => {
    const date = new Date(item.timestamp * 1000).toLocaleString();
    const dot  = item.posture_ok
      ? '<span class="ok-dot">✔</span>'
      : '<span class="fail-dot">✘</span>';

    const div = document.createElement("div");
    div.className = "history-item";
    div.innerHTML = `
      <div>
        <span class="ex-name">${dot} ${item.exercise.replace(/_/g, " ")}</span>
        <div class="h-date">${date}</div>
      </div>
      <div class="h-score">${item.score}/100</div>
    `;
    container.appendChild(div);
  });
}
