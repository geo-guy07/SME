/**
 * SME Audit AI — Frontend Application Controller
 * Handles tabs, audits, AI copilot chat, Udyam workflow stepper, OCR, and PDF generation.
 */

// Application State
const AppState = {
  activeBusinessId: "B005",
  activeBusiness: null,
  businesses: [],
  findings: [],
  activeWorkflow: null,
  activeWorkflowId: "WF-UDYAM-B005",
  chatSessionId: "session-" + Math.random().toString(36).substring(2, 9),
  regulations: [],
  activeCategoryFilter: "all",
};

// DOM Ready
document.addEventListener("DOMContentLoaded", async () => {
  initTabs();
  initEventListeners();
  await loadBusinesses();
  await switchBusiness(AppState.activeBusinessId);
  await loadRegulations();
});

// Tab Navigation
function initTabs() {
  const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
  navItems.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      navItems.forEach(n => n.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("active");
      });
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      // Update header subtitle based on tab
      updateHeaderForTab(targetId);
    });
  });
}

function updateHeaderForTab(tabId) {
  const titles = {
    "tab-dashboard": { title: "Compliance Audit Dashboard", subtitle: "Real-time statutory threshold evaluations and regulatory grounding for Indian enterprises" },
    "tab-chat": { title: "AI Compliance Copilot", subtitle: "Conversational agent with native function calling and statutory citation grounding" },
    "tab-workflow": { title: "Udyam Registration Automation", subtitle: "Official portal automation state machine with mandatory OTP authentication pause" },
    "tab-ocr": { title: "Smart Document Ingestion", subtitle: "Multimodal Gemini Vision & heuristic parsing for invoices, bills, and tax certificates" },
    "tab-gstin": { title: "Official GSTIN Verification & Filing Health", subtitle: "Live taxpayer validation, jurisdiction mapping, and return filing track record" },
    "tab-ledger": { title: "Section 43B(h) Vendor Ledger Scanner", subtitle: "Accounts payable aging audit for MSME payment safeguards and penal interest calculations" },
    "tab-ca": { title: "CA Multi-Client Portfolio Hub", subtitle: "Comprehensive compliance monitoring and filing deadlines across all managed SME clients" },
    "tab-regulations": { title: "Statutory Knowledge Base", subtitle: "32 indexed Indian statutory provisions covering GST, MSME, Labor, PT, FSSAI & Income Tax" },
    "tab-report": { title: "Audit Reports & PDF Center", subtitle: "Generate official executive compliance audit dossiers with penalty risks and calendars" },
  };
  const info = titles[tabId] || titles["tab-dashboard"];
  document.getElementById("page-title").textContent = info.title;
  document.getElementById("page-subtitle").textContent = info.subtitle;
}

// Event Listeners
function initEventListeners() {
  // Business Switcher
  const bizSelect = document.getElementById("business-select");
  if (bizSelect) {
    bizSelect.addEventListener("change", (e) => {
      switchBusiness(e.target.value);
    });
  }

  // Quick PDF Download
  document.getElementById("btn-quick-download-pdf").addEventListener("click", () => {
    downloadReport(AppState.activeBusinessId);
  });
  document.getElementById("btn-generate-pdf-now").addEventListener("click", () => {
    downloadReport(AppState.activeBusinessId);
  });

  // Re-audit button
  document.getElementById("btn-re-audit").addEventListener("click", () => {
    runAudit(AppState.activeBusinessId);
  });

  // Chat send
  document.getElementById("btn-chat-send").addEventListener("click", handleChatSend);
  document.getElementById("chat-input-text").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleChatSend();
    }
  });

  // Suggested Prompts
  document.querySelectorAll(".prompt-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const promptText = chip.getAttribute("data-prompt");
      document.getElementById("chat-input-text").value = promptText;
      handleChatSend();
    });
  });

  // Clear Chat
  document.getElementById("btn-clear-chat").addEventListener("click", () => {
    const stream = document.getElementById("chat-messages-stream");
    stream.innerHTML = `
      <div class="message-bubble message-assistant">
        <div class="bubble-sender">SME Compliance Copilot</div>
        <div class="bubble-content">Chat history cleared. How can I assist you with Indian statutory compliance?</div>
      </div>
    `;
  });

  // Workflow Initiate
  document.getElementById("btn-start-workflow").addEventListener("click", handleStartWorkflow);

  // Workflow OTP submit
  document.getElementById("btn-submit-otp").addEventListener("click", handleSubmitOtp);

  // Document OCR Upload
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = document.getElementById("file-input");
  document.getElementById("btn-browse-files").addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--accent-indigo)";
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.style.borderColor = "rgba(99, 102, 241, 0.35)";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "rgba(99, 102, 241, 0.35)";
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  // Apply OCR to Custom Profile
  document.getElementById("btn-apply-extracted-profile").addEventListener("click", () => {
    if (window._lastExtractedData) {
      applyExtractedDataToAudit(window._lastExtractedData);
    }
  });

  // Regulations Search
  document.getElementById("reg-search-input").addEventListener("input", (e) => {
    filterRegulations(e.target.value, AppState.activeCategoryFilter);
  });

  // Category Filter Chips
  document.querySelectorAll(".category-filters .filter-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".category-filters .filter-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      AppState.activeCategoryFilter = chip.getAttribute("data-category");
      const searchTerm = document.getElementById("reg-search-input").value;
      filterRegulations(searchTerm, AppState.activeCategoryFilter);
    });
  });

  // Custom Business Modal
  const modal = document.getElementById("custom-biz-modal");
  document.getElementById("btn-custom-business-modal").addEventListener("click", () => {
    modal.classList.remove("hidden");
  });
  document.getElementById("btn-close-modal").addEventListener("click", () => {
    modal.classList.add("hidden");
  });
  document.getElementById("btn-cancel-modal").addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  document.getElementById("custom-biz-form").addEventListener("submit", (e) => {
    e.preventDefault();
    modal.classList.add("hidden");
    runCustomAudit();
  });

  // GSTIN Verifier Events
  document.getElementById("btn-verify-gstin").addEventListener("click", () => {
    const gstin = document.getElementById("gstin-search-input").value.trim();
    handleVerifyGstin(gstin);
  });

  document.getElementById("btn-import-gstin").addEventListener("click", () => {
    const gstin = document.getElementById("gstin-search-input").value.trim();
    handleImportGstin(gstin);
  });

  document.querySelectorAll(".gstin-quick-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      const g = pill.getAttribute("data-gstin");
      document.getElementById("gstin-search-input").value = g;
      handleVerifyGstin(g);
    });
  });

  // 43B(h) Ledger Events
  document.getElementById("btn-download-sample-ledger").addEventListener("click", () => {
    window.open("/api/ledger/sample", "_blank");
  });

  const ledgerDropzone = document.getElementById("ledger-dropzone");
  const ledgerFileInput = document.getElementById("ledger-file-input");
  document.getElementById("btn-browse-ledger").addEventListener("click", () => ledgerFileInput.click());

  ledgerFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleLedgerUpload(e.target.files[0]);
    }
  });

  ledgerDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    ledgerDropzone.style.borderColor = "var(--accent-amber)";
  });

  ledgerDropzone.addEventListener("dragleave", () => {
    ledgerDropzone.style.borderColor = "rgba(99, 102, 241, 0.35)";
  });

  ledgerDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    ledgerDropzone.style.borderColor = "rgba(99, 102, 241, 0.35)";
    if (e.dataTransfer.files.length > 0) {
      handleLedgerUpload(e.dataTransfer.files[0]);
    }
  });

  // CA Portfolio Events
  document.getElementById("btn-refresh-ca-portfolio").addEventListener("click", loadCaPortfolio);
  document.getElementById("nav-ca").addEventListener("click", loadCaPortfolio);
}

// Load Business Profiles
async function loadBusinesses() {
  try {
    const res = await fetch("/api/businesses");
    if (res.ok) {
      AppState.businesses = await res.json();
      populateBusinessDropdown(AppState.businesses);
    }
  } catch (e) {
    console.error("Failed to load businesses:", e);
  }
}

function populateBusinessDropdown(businesses) {
  const select = document.getElementById("business-select");
  if (!select) return;
  select.innerHTML = "";
  businesses.forEach(b => {
    const opt = document.createElement("option");
    opt.value = b.business_id;
    opt.textContent = `${b.name} (₹${b.turnover_lakh}L • ${b.employee_count} Staff • ${b.state})`;
    if (b.business_id === AppState.activeBusinessId) {
      opt.selected = true;
    }
    select.appendChild(opt);
  });
}

// Switch Active Business
async function switchBusiness(bizId) {
  AppState.activeBusinessId = bizId;
  AppState.activeWorkflowId = `WF-UDYAM-${bizId}`;

  try {
    const res = await fetch(`/api/business/${bizId}`);
    if (res.ok) {
      AppState.activeBusiness = await res.json();
      updateBusinessProfileUI(AppState.activeBusiness);
      await runAudit(bizId);
    }
  } catch (e) {
    console.error(`Error loading business ${bizId}:`, e);
  }
}

function updateBusinessProfileUI(biz) {
  if (!biz) return;
  document.getElementById("header-biz-name").textContent = `${biz.name} (${biz.business_id})`;
  document.getElementById("banner-biz-type").textContent = `${biz.business_type.toUpperCase()} ENTERPRISE`;
  document.getElementById("prof-owner").textContent = biz.owner || "Not Specified";
  document.getElementById("prof-turnover").textContent = `₹ ${biz.turnover_lakh} Lakhs`;
  document.getElementById("prof-employees").textContent = `${biz.employee_count} Personnel`;
  document.getElementById("prof-state").textContent = biz.state + (biz.special_category_state ? " (Special Category)" : "");
  document.getElementById("prof-pan").textContent = biz.pan || "NOT LINKED";
  document.getElementById("prof-address").textContent = biz.address || `${biz.state}, India`;

  // Workflow credentials card
  document.getElementById("wf-cred-name").textContent = biz.name;
  document.getElementById("wf-cred-owner").textContent = biz.owner || "Applicant";
  document.getElementById("wf-cred-pan").textContent = biz.pan ? `${biz.pan.slice(0, 2)}******${biz.pan.slice(-2)}` : "******";
  document.getElementById("wf-cred-mobile").textContent = biz.mobile ? `******${biz.mobile.slice(-4)}` : "******";
  document.getElementById("wf-cred-aadhaar").textContent = biz.aadhaar ? `XXXX-XXXX-${biz.aadhaar.slice(-4)}` : "XXXX-XXXX-XXXX";
}

// Run Statutory Audit
async function runAudit(bizId) {
  try {
    const res = await fetch(`/api/audit/${bizId}`);
    if (res.ok) {
      const data = await res.json();
      AppState.findings = data.findings;
      renderAuditFindings(data);
    }
  } catch (e) {
    console.error("Audit failed:", e);
  }
}

function renderAuditFindings(auditData) {
  const findings = auditData.findings || [];
  const applicableCount = findings.filter(f => f.applies).length;
  const exemptCount = findings.length - applicableCount;
  const highSevCount = findings.filter(f => f.applies && f.severity === "HIGH").length;

  document.getElementById("stat-applicable-count").textContent = applicableCount;
  document.getElementById("stat-exempt-count").textContent = exemptCount;
  document.getElementById("stat-high-sev-count").textContent = highSevCount;

  // Calculate Health Score
  const score = Math.max(20, Math.round(100 - (highSevCount * 18 + applicableCount * 6)));
  const scoreElem = document.getElementById("stat-health-score");
  scoreElem.textContent = `${score}%`;
  scoreElem.style.color = score > 75 ? "var(--accent-emerald)" : (score > 50 ? "var(--accent-amber)" : "var(--accent-rose)");

  // Populate Table
  const tbody = document.getElementById("findings-table-body");
  tbody.innerHTML = "";

  findings.forEach(f => {
    const tr = document.createElement("tr");

    const statusBadge = f.applies
      ? `<span class="badge badge-rose">MANDATORY</span>`
      : `<span class="badge badge-emerald">EXEMPT</span>`;

    let sevBadge = `<span class="badge badge-slate">${f.severity || "LOW"}</span>`;
    if (f.severity === "HIGH") sevBadge = `<span class="badge badge-rose">HIGH</span>`;
    else if (f.severity === "MEDIUM") sevBadge = `<span class="badge badge-amber">MEDIUM</span>`;
    else if (f.severity === "ADVISORY") sevBadge = `<span class="badge badge-indigo">ADVISORY</span>`;

    let actionButton = "";
    if (f.workflow_available === "udyam_registration") {
      actionButton = `<button class="btn btn-xs btn-primary btn-quick-wf">Start Udyam</button>`;
    } else {
      actionButton = `<button class="btn btn-xs btn-outline btn-ask-copilot">Explain</button>`;
    }

    tr.innerHTML = `
      <td style="font-weight: 600; color: #fff;">${f.requirement}</td>
      <td>${statusBadge}</td>
      <td>${sevBadge}</td>
      <td style="color: var(--text-secondary); max-width: 320px;">${f.reason}</td>
      <td><span class="citation-pill" data-cite="${f.evidence_id}">${f.evidence_id}</span></td>
      <td>${actionButton}</td>
    `;

    // Hook action buttons
    const wfBtn = tr.querySelector(".btn-quick-wf");
    if (wfBtn) {
      wfBtn.addEventListener("click", () => {
        document.getElementById("nav-workflow").click();
        handleStartWorkflow();
      });
    }

    const askBtn = tr.querySelector(".btn-ask-copilot");
    if (askBtn) {
      askBtn.addEventListener("click", () => {
        document.getElementById("nav-chat").click();
        document.getElementById("chat-input-text").value = `Explain why ${f.requirement} applies or is exempt for my business (${f.evidence_id})`;
        handleChatSend();
      });
    }

    const citePill = tr.querySelector(".citation-pill");
    if (citePill) {
      citePill.addEventListener("click", () => {
        document.getElementById("nav-regulations").click();
        document.getElementById("reg-search-input").value = f.evidence_id;
        filterRegulations(f.evidence_id, "all");
      });
    }

    tbody.appendChild(tr);
  });
}

// Custom Business Evaluation
async function runCustomAudit() {
  const payload = {
    name: document.getElementById("cust-name").value,
    business_type: document.getElementById("cust-type").value,
    turnover_lakh: parseFloat(document.getElementById("cust-turnover").value),
    employee_count: parseInt(document.getElementById("cust-employees").value),
    state: document.getElementById("cust-state").value,
    activity: document.getElementById("cust-activity").value,
  };

  try {
    const res = await fetch("/api/audit/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const data = await res.json();
      updateBusinessProfileUI({
        business_id: "CUSTOM",
        name: payload.name,
        business_type: payload.business_type,
        turnover_lakh: payload.turnover_lakh,
        employee_count: payload.employee_count,
        state: payload.state,
        activity: payload.activity,
        owner: "Custom Proprietor",
        pan: "ABCDE1234F",
      });
      renderAuditFindings(data);
    }
  } catch (e) {
    console.error("Custom audit failed:", e);
  }
}

// Chat Handling
async function handleChatSend() {
  const input = document.getElementById("chat-input-text");
  const query = input.value.trim();
  if (!query) return;

  input.value = "";
  appendChatMessage("user", query);

  // Show thinking indicator
  const stream = document.getElementById("chat-messages-stream");
  const loadingId = "loading-" + Date.now();
  const loadingElem = document.createElement("div");
  loadingElem.id = loadingId;
  loadingElem.className = "message-bubble message-assistant";
  loadingElem.innerHTML = `<div class="bubble-sender">AI Copilot</div><div class="bubble-content"><em>Evaluating statutory provisions and tool calling...</em></div>`;
  stream.appendChild(loadingElem);
  stream.scrollTop = stream.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: query,
        business_id: AppState.activeBusinessId,
        session_id: AppState.chatSessionId,
      }),
    });

    const loadingNode = document.getElementById(loadingId);
    if (loadingNode) loadingNode.remove();

    if (res.ok) {
      const data = await res.json();
      appendAssistantChatResponse(data);
    } else {
      appendChatMessage("assistant", "Sorry, I encountered an error connecting to the agent backend.");
    }
  } catch (e) {
    const loadingNode = document.getElementById(loadingId);
    if (loadingNode) loadingNode.remove();
    appendChatMessage("assistant", `Error: ${e.message}`);
  }
}

function appendChatMessage(sender, text) {
  const stream = document.getElementById("chat-messages-stream");
  const bubble = document.createElement("div");
  bubble.className = `message-bubble message-${sender}`;
  bubble.innerHTML = `
    <div class="bubble-sender">${sender === "user" ? "You" : "SME Copilot"}</div>
    <div class="bubble-content">${formatMarkdownText(text)}</div>
  `;
  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
}

function appendAssistantChatResponse(data) {
  const stream = document.getElementById("chat-messages-stream");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble message-assistant";

  let toolsHtml = "";
  if (data.tools_invoked && data.tools_invoked.length > 0) {
    toolsHtml = data.tools_invoked.map(t => `<div class="tool-invocation-chip">&#9881; Tool Executed: ${t.tool}</div>`).join(" ");
  }

  let citationsHtml = "";
  if (data.citations && data.citations.length > 0) {
    const pills = data.citations.map(c => `<span class="citation-pill" title="${c.source}">${c.id}</span>`).join(" ");
    citationsHtml = `<div style="margin-top: 10px; font-size: 0.75rem; color: var(--text-muted);">Grounded Evidence: ${pills}</div>`;
  }

  bubble.innerHTML = `
    <div class="bubble-sender">SME Compliance Copilot</div>
    ${toolsHtml}
    <div class="bubble-content">${formatMarkdownText(data.response)}</div>
    ${citationsHtml}
  `;
  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
}

function formatMarkdownText(text) {
  if (!text) return "";
  let formatted = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
  return formatted;
}

// Workflow Engine Handling
async function handleStartWorkflow() {
  const dryRun = document.getElementById("wf-dryrun-toggle").checked;
  appendWorkflowLog(`[Initiating] Starting Udyam MSME workflow for ${AppState.activeBusinessId} (Dry-Run: ${dryRun})`, "info");

  updateStepperState(2); // Data Check

  try {
    const res = await fetch("/api/workflow/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        business_id: AppState.activeBusinessId,
        dry_run: dryRun,
      }),
    });

    if (res.ok) {
      const summary = await res.json();
      AppState.activeWorkflow = summary;
      handleWorkflowStateUpdate(summary);
    } else {
      appendWorkflowLog("[Error] Failed to initiate registration workflow", "error");
    }
  } catch (e) {
    appendWorkflowLog(`[Error] Network error: ${e.message}`, "error");
  }
}

function handleWorkflowStateUpdate(summary) {
  const status = summary.status;
  appendWorkflowLog(`[State Transition] Current Status: ${status}`, "info");

  if (summary.last_step) {
    appendWorkflowLog(`  -> ${summary.last_step.message}`, "success");
  }

  const hitlBanner = document.getElementById("hitl-action-card");

  if (status === "AWAITING_USER") {
    updateStepperState(5); // Human OTP
    hitlBanner.classList.remove("hidden");
    const action = summary.pending_user_action || {};
    document.getElementById("hitl-prompt-title").textContent = action.action_type || "Aadhaar e-KYC Verification Checkpoint";
    document.getElementById("hitl-prompt-desc").textContent = action.prompt || "Please enter Aadhaar OTP received on registered mobile.";
    appendWorkflowLog("[AWAITING_USER] Paused at official portal boundary for Aadhaar OTP authentication.", "warn");
  } else if (status === "RUNNING") {
    updateStepperState(4);
    hitlBanner.classList.add("hidden");
  } else if (status === "COMPLETED" || (summary.result && summary.result.stage)) {
    updateStepperState(6);
    hitlBanner.classList.add("hidden");
    appendWorkflowLog("[Stage 1 Verified] Aadhaar authentication validated truthfully. Ready for PAN verification stage.", "success");
  }
}

async function handleSubmitOtp() {
  const otp = document.getElementById("input-otp").value.trim();
  if (!otp || otp.length < 6) {
    alert("Please enter a valid 6-digit OTP.");
    return;
  }

  appendWorkflowLog(`[User Action] Submitted OTP '******' for verification...`, "info");

  try {
    const res = await fetch("/api/workflow/resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workflow_id: AppState.activeWorkflowId,
        otp: otp,
      }),
    });

    if (res.ok) {
      const summary = await res.json();
      handleWorkflowStateUpdate(summary);
    } else {
      const err = await res.json();
      appendWorkflowLog(`[Error] ${err.detail || "Failed to resume workflow"}`, "error");
    }
  } catch (e) {
    appendWorkflowLog(`[Error] Resume failed: ${e.message}`, "error");
  }
}

function updateStepperState(activeStepNumber) {
  const steps = [
    { num: 1, id: "step-node-ready", conn: "conn-1" },
    { num: 2, id: "step-node-collecting", conn: "conn-2" },
    { num: 3, id: "step-node-validating", conn: "conn-3" },
    { num: 4, id: "step-node-running", conn: "conn-4" },
    { num: 5, id: "step-node-awaiting", conn: "conn-5" },
    { num: 6, id: "step-node-completed", conn: null },
  ];

  steps.forEach(s => {
    const node = document.getElementById(s.id);
    const conn = s.conn ? document.getElementById(s.conn) : null;

    if (s.num < activeStepNumber) {
      node.className = "step-item completed";
      if (conn) conn.className = "step-connector active";
    } else if (s.num === activeStepNumber) {
      node.className = "step-item active";
      if (conn) conn.className = "step-connector";
    } else {
      node.className = "step-item";
      if (conn) conn.className = "step-connector";
    }
  });
}

function appendWorkflowLog(message, type = "info") {
  const terminal = document.getElementById("workflow-terminal-logs");
  const entry = document.createElement("div");
  entry.className = `log-entry ${type}`;
  const timeStr = new Date().toLocaleTimeString();
  entry.textContent = `[${timeStr}] ${message}`;
  terminal.appendChild(entry);
  terminal.scrollTop = terminal.scrollHeight;
}

// Document OCR Ingestion
async function handleFileUpload(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("business_id", AppState.activeBusinessId);

  const dropzone = document.getElementById("upload-dropzone");
  dropzone.innerHTML = `<h4>Extracting fields via Multimodal Vision / Heuristic Parser...</h4><p class="upload-hint">Analyzing ${file.name}</p>`;

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      renderOcrResults(data);
    } else {
      alert("Failed to extract document.");
    }
  } catch (e) {
    console.error("Upload error:", e);
    alert(`Upload error: ${e.message}`);
  } finally {
    dropzone.innerHTML = `
      <svg class="upload-cloud-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
        <path d="M12 12v9"/><path d="m16 16-4-4-4 4"/>
      </svg>
      <h4>Drag & Drop your invoice or document here</h4>
      <p class="upload-hint">Supports PDF, PNG, JPG (e.g. Tax Invoices, Utility Bills, PAN cards)</p>
      <input type="file" id="file-input" class="hidden-file-input" accept=".pdf,.png,.jpg,.jpeg">
      <button id="btn-browse-files-reset" class="btn btn-secondary">Browse Local File</button>
    `;
    document.getElementById("btn-browse-files-reset").addEventListener("click", () => {
      document.getElementById("file-input").click();
    });
  }
}

function renderOcrResults(uploadRes) {
  const card = document.getElementById("extraction-results-card");
  card.classList.remove("hidden");

  const ext = uploadRes.extracted_data || {};
  window._lastExtractedData = ext;

  document.getElementById("doc-type-badge").textContent = ext.document_type || "Commercial Document";
  document.getElementById("doc-filename").textContent = uploadRes.filename;
  document.getElementById("doc-confidence").textContent = `${Math.round((ext.confidence || 0.85) * 100)}%`;

  const grid = document.getElementById("extracted-fields-grid");
  grid.innerHTML = `
    <div class="extracted-field-box">
      <span class="ef-label">Detected Business Name</span>
      <span class="ef-val">${ext.business_name || "Extracted Enterprise"}</span>
    </div>
    <div class="extracted-field-box">
      <span class="ef-label">PAN Number</span>
      <span class="ef-val mono">${ext.pan || "NOT DETECTED"}</span>
    </div>
    <div class="extracted-field-box">
      <span class="ef-label">Estimated Turnover</span>
      <span class="ef-val">${ext.turnover_lakh ? `₹ ${ext.turnover_lakh} Lakhs` : "₹ 45.0 Lakhs (Est)"}</span>
    </div>
    <div class="extracted-field-box">
      <span class="ef-label">State / Region</span>
      <span class="ef-val">${ext.state || "Maharashtra"}</span>
    </div>
    <div class="extracted-field-box">
      <span class="ef-label">Contact / Mobile</span>
      <span class="ef-val mono">${ext.mobile || "9876543210"}</span>
    </div>
    <div class="extracted-field-box">
      <span class="ef-label">Registered Address</span>
      <span class="ef-val">${ext.address || "Commercial Zone, India"}</span>
    </div>
  `;
}

function applyExtractedDataToAudit(ext) {
  const customProfile = {
    name: ext.business_name || "Extracted Entity",
    business_type: "goods",
    turnover_lakh: ext.turnover_lakh || 50.0,
    employee_count: 5,
    state: ext.state || "Maharashtra",
    pan: ext.pan || "ABCDE1234F",
    owner: ext.owner || "Detected Proprietor",
  };

  updateBusinessProfileUI({
    business_id: "OCR-EXTRACTED",
    ...customProfile,
  });

  document.getElementById("nav-dashboard").click();
  runCustomAuditFromProfile(customProfile);
}

async function runCustomAuditFromProfile(profile) {
  try {
    const res = await fetch("/api/audit/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    });
    if (res.ok) {
      const data = await res.json();
      renderAuditFindings(data);
    }
  } catch (e) {
    console.error("Audit from OCR failed:", e);
  }
}

// Regulations Explorer
async function loadRegulations() {
  try {
    const res = await fetch("/api/regulations");
    if (res.ok) {
      AppState.regulations = await res.json();
      renderRegulations(AppState.regulations);
    }
  } catch (e) {
    console.error("Failed to load regulations:", e);
  }
}

function renderRegulations(regs) {
  const grid = document.getElementById("regulations-card-grid");
  grid.innerHTML = "";

  regs.forEach(r => {
    const card = document.createElement("div");
    card.className = "regulation-card";
    card.innerHTML = `
      <div class="reg-card-header">
        <span class="reg-id">${r.id}</span>
        <span class="badge badge-indigo">${r.category}</span>
      </div>
      <h4 class="reg-title">${r.title}</h4>
      <div class="reg-source">${r.source}</div>
      <p class="reg-text">${r.text}</p>
    `;
    grid.appendChild(card);
  });
}

function filterRegulations(searchTerm, category) {
  const term = (searchTerm || "").toLowerCase().trim();
  const filtered = AppState.regulations.filter(r => {
    const matchCat = category === "all" || r.category.toLowerCase() === category.toLowerCase();
    const matchText = !term ||
      r.id.toLowerCase().includes(term) ||
      r.title.toLowerCase().includes(term) ||
      r.text.toLowerCase().includes(term) ||
      r.source.toLowerCase().includes(term);
    return matchCat && matchText;
  });
  renderRegulations(filtered);
}

// PDF Download
function downloadReport(bizId) {
  window.open(`/api/report/download/${bizId}`, "_blank");
}

// ---- GSTIN Verifier Controller ----
async function handleVerifyGstin(gstin) {
  if (!gstin || gstin.length < 15) {
    alert("Please enter a valid 15-character GSTIN.");
    return;
  }

  try {
    const res = await fetch("/api/gstin/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gstin: gstin }),
    });

    if (res.ok) {
      const data = await res.json();
      renderGstinResult(data);
    } else {
      const err = await res.json();
      alert(`GSTIN Verification Error: ${err.detail || "Lookup failed"}`);
    }
  } catch (e) {
    alert(`Error verifying GSTIN: ${e.message}`);
  }
}

function renderGstinResult(data) {
  const card = document.getElementById("gstin-result-card");
  card.classList.remove("hidden");

  document.getElementById("gstin-res-legal-name").textContent = data.legal_name || "Taxpayer Legal Name";
  document.getElementById("gstin-res-trade-name").textContent = `Trade Name: ${data.trade_name || "N/A"}`;
  document.getElementById("gstin-res-number").textContent = data.gstin;
  document.getElementById("gstin-res-type").textContent = `${data.taxpayer_type || "Regular"} Taxpayer`;
  document.getElementById("gstin-res-state").textContent = `${data.state_name} (${data.state_code})`;
  document.getElementById("gstin-res-center").textContent = data.center_jurisdiction || "Central Division";
  document.getElementById("gstin-res-regdate").textContent = data.registration_date || "2018-07-01";
  document.getElementById("gstin-res-pan").textContent = data.pan;
  document.getElementById("gstin-res-entity").textContent = data.entity_type || "Commercial Entity";
  document.getElementById("gstin-res-source").textContent = data.source || "Government Portal Direct";

  // Filing Table
  const tbody = document.getElementById("gstin-filing-tbody");
  tbody.innerHTML = "";
  const records = data.filing_track_record || [];
  records.forEach(r => {
    const tr = document.createElement("tr");
    const statusClass = r.status.includes("Late") ? "badge-amber" : "badge-emerald";
    tr.innerHTML = `
      <td style="font-weight: 600; color: #fff;">${r.return_type}</td>
      <td>${r.tax_period}</td>
      <td class="mono">${r.date_of_filing}</td>
      <td><span class="badge ${statusClass}">${r.status}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

async function handleImportGstin(gstin) {
  if (!gstin || gstin.length < 15) {
    alert("Please enter a valid 15-character GSTIN.");
    return;
  }
  try {
    const res = await fetch("/api/gstin/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gstin: gstin }),
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Taxpayer '${data.data.trade_name}' imported successfully into business registry as '${data.business_id}'!`);
      await loadBusinesses();
      await switchBusiness(data.business_id);
      document.getElementById("nav-dashboard").click();
    }
  } catch (e) {
    alert(`Import failed: ${e.message}`);
  }
}

// ---- Section 43B(h) Ledger Scanner Controller ----
async function handleLedgerUpload(file) {
  const formData = new FormData();
  formData.append("file", file);

  const dropzone = document.getElementById("ledger-dropzone");
  dropzone.innerHTML = `<h4>Analyzing accounts payable against Section 43B(h) limits...</h4><p class="upload-hint">Evaluating ${file.name}</p>`;

  try {
    const res = await fetch("/api/ledger/upload", {
      method: "POST",
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      renderLedgerAnalysis(data);
    } else {
      alert("Failed to analyze vendor ledger.");
    }
  } catch (e) {
    alert(`Ledger upload error: ${e.message}`);
  } finally {
    dropzone.innerHTML = `
      <svg class="upload-cloud-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><polyline points="10 9 9 9 8 9"/>
      </svg>
      <h4>Drag & Drop your Purchase Ledger (CSV)</h4>
      <p class="upload-hint">Audits invoice dates against 45-day MSMED limits & flags taxable disallowances</p>
      <input type="file" id="ledger-file-input" class="hidden-file-input" accept=".csv">
      <button id="btn-browse-ledger-reset" class="btn btn-secondary">Browse CSV File</button>
    `;
    document.getElementById("btn-browse-ledger-reset").addEventListener("click", () => {
      document.getElementById("ledger-file-input").click();
    });
  }
}

function renderLedgerAnalysis(data) {
  const container = document.getElementById("ledger-results-container");
  container.classList.remove("hidden");

  const s = data.summary || {};
  document.getElementById("ledger-stat-total-purchases").textContent = `₹ ${s.total_purchases ? (s.total_purchases / 100000).toFixed(2) : 0} Lakhs`;
  document.getElementById("ledger-stat-total-invoices").textContent = `${s.total_invoices || 0} Invoices Analyzed`;
  document.getElementById("ledger-stat-disallowed").textContent = `₹ ${s.total_disallowed_amount ? (s.total_disallowed_amount / 100000).toFixed(2) : 0} Lakhs`;
  document.getElementById("ledger-stat-tax-risk").textContent = `₹ ${s.corporate_tax_exposure ? (s.corporate_tax_exposure / 100000).toFixed(2) : 0} Lakhs`;
  document.getElementById("ledger-stat-interest").textContent = `₹ ${s.statutory_compound_interest ? s.statutory_compound_interest.toLocaleString() : 0}`;

  // Invoices Table
  const tbody = document.getElementById("ledger-invoices-tbody");
  tbody.innerHTML = "";

  const invoices = data.invoices || [];
  invoices.forEach(inv => {
    const tr = document.createElement("tr");

    let statusBadge = `<span class="badge badge-emerald">COMPLIANT</span>`;
    if (inv.status === "DISALLOWED_OVERDUE") {
      statusBadge = `<span class="badge badge-rose">DISALLOWED (43B-h)</span>`;
    } else if (inv.status === "CRITICAL_APPROACHING") {
      statusBadge = `<span class="badge badge-amber">CRITICAL (DUE SOON)</span>`;
    } else if (inv.status === "EXEMPT_NON_MSME") {
      statusBadge = `<span class="badge badge-slate">NON-MSME</span>`;
    }

    const interestHtml = inv.penal_interest > 0
      ? `<span style="color: var(--accent-rose); font-weight: 600;">₹${inv.penal_interest.toLocaleString()}</span>`
      : `<span style="color: var(--text-muted);">₹0</span>`;

    tr.innerHTML = `
      <td class="mono" style="font-weight: 600; color: #fff;">${inv.invoice_number}</td>
      <td>${inv.vendor_name}</td>
      <td><span class="badge badge-indigo">${inv.msme_status}</span></td>
      <td style="font-weight: 600;">₹ ${inv.amount.toLocaleString()}</td>
      <td class="mono">${inv.invoice_date || "--"}</td>
      <td>${inv.days_elapsed}d / ${inv.statutory_limit_days}d</td>
      <td>${statusBadge}</td>
      <td>${interestHtml}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ---- CA Portfolio Hub Controller ----
async function loadCaPortfolio() {
  try {
    const res = await fetch("/api/ca/portfolio-summary");
    if (res.ok) {
      const data = await res.json();
      renderCaPortfolio(data);
    }
  } catch (e) {
    console.error("CA portfolio load error:", e);
  }
}

function renderCaPortfolio(data) {
  const m = data.portfolio_metrics || {};
  document.getElementById("ca-stat-clients").textContent = m.total_clients || 0;
  document.getElementById("ca-stat-high-risk").textContent = m.high_risk_clients || 0;
  document.getElementById("ca-stat-avg-score").textContent = `${m.portfolio_health_average || 75}%`;
  document.getElementById("ca-stat-total-turnover").textContent = `₹${m.total_turnover_monitored_lakh || 0}L`;

  const tbody = document.getElementById("ca-client-table").querySelector("tbody");
  tbody.innerHTML = "";

  const clients = data.clients || [];
  clients.forEach(c => {
    const tr = document.createElement("tr");

    let riskBadge = `<span class="badge badge-emerald">LOW RISK</span>`;
    if (c.risk_level === "HIGH") riskBadge = `<span class="badge badge-rose">HIGH RISK</span>`;
    else if (c.risk_level === "MEDIUM") riskBadge = `<span class="badge badge-amber">MEDIUM RISK</span>`;

    tr.innerHTML = `
      <td style="font-weight: 600; color: #fff;">${c.name} (${c.business_id})</td>
      <td>${c.business_type} • ${c.state}</td>
      <td style="font-weight: 600;">₹${c.turnover_lakh}L</td>
      <td>${c.employee_count} Staff</td>
      <td>${c.applicable_count} Registrations</td>
      <td style="font-weight: 700; color: ${c.health_score > 70 ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">${c.health_score}%</td>
      <td>${riskBadge}</td>
      <td><button class="btn btn-xs btn-primary btn-ca-audit">View Audit</button></td>
    `;

    tr.querySelector(".btn-ca-audit").addEventListener("click", () => {
      switchBusiness(c.business_id);
      document.getElementById("nav-dashboard").click();
    });

    tbody.appendChild(tr);
  });
}
