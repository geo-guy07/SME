/**
 * SME Audit AI — Interactive Web Application Engine
 * Handles Reactive State, PostgreSQL Sync, Gemini Vision OCR Ingestion,
 * Conversational Compliance Chat, and Udyam MSME Stepper.
 */

const STATE = {
  activeView: 'landing',
  activeTab: 'profile',
  currentUser: {
    user_id: 1,
    name: 'Rahul Sharma',
    email: 'rahul.sharma@example.com',
    role: 'owner',
  },
  currentBusinessId: 'B005',
  businessData: null,
  auditFindings: [],
  activeWorkflowId: 'WF-UDYAM-B005',
};

// ==========================================
// Initialization & Lifecycle
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
  console.log('[SME Audit AI] App loaded.');
  await loadBusinessProfile(STATE.currentBusinessId);
  await fetchLiveAuditScorecard();
});

// ==========================================
// Navigation & Views
// ==========================================
function navigateTo(view) {
  const landing = document.getElementById('app-landing-view');
  const dash = document.getElementById('app-dashboard-view');
  const agent = document.getElementById('app-agent-view');

  if (view === 'agent') {
    if (landing) landing.style.display = 'none';
    if (dash) dash.style.display = 'none';
    if (agent) agent.style.display = 'block';
    STATE.activeView = 'agent';
    window.scrollTo({ top: 0, behavior: 'smooth' });
    updateAgentViewWithBusiness(STATE.businessData);
  } else if (view === 'dashboard') {
    if (landing) landing.style.display = 'none';
    if (agent) agent.style.display = 'none';
    if (dash) dash.style.display = 'block';
    STATE.activeView = 'dashboard';
    window.scrollTo({ top: 0, behavior: 'smooth' });
    loadBusinessProfile(STATE.currentBusinessId);
  } else {
    if (dash) dash.style.display = 'none';
    if (agent) agent.style.display = 'none';
    if (landing) landing.style.display = 'block';
    STATE.activeView = 'landing';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function scrollToSection(id) {
  if (STATE.activeView === 'dashboard') {
    navigateTo('landing');
  }
  setTimeout(() => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }, 100);
}

function switchDashboardTab(tab) {
  STATE.activeTab = tab;
  document.querySelectorAll('.dash-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.dash-content-pane').forEach(p => p.classList.remove('active'));

  const btn = document.getElementById(`tab-btn-${tab}`);
  const pane = document.getElementById(`pane-${tab}`);
  if (btn) btn.classList.add('active');
  if (pane) pane.classList.add('active');

  if (tab === 'scorecard') {
    fetchLiveAuditScorecard();
  }
}

// ==========================================
// Business Profile Data (Retrieve & Update)
// ==========================================
async function loadBusinessProfile(businessId) {
  try {
    const res = await fetch(`/api/business/${businessId}`);
    if (!res.ok) throw new Error('Failed to load business profile');
    const data = await res.json();
    STATE.businessData = data;
    STATE.currentBusinessId = businessId;

    populateProfileForm(data);
    updatePaperCertificatePreview(data);
    updateDashboardHeader(data);
    updateAgentViewWithBusiness(data);
  } catch (err) {
    console.warn('Error loading business profile:', err);
  }
}

function populateProfileForm(biz) {
  if (!biz) return;
  setVal('field-biz-name', biz.name || biz.business_name || '');
  setVal('field-owner-name', biz.owner || '');
  setVal('field-biz-type', biz.business_type || 'goods');
  setVal('field-turnover', biz.turnover_lakh != null ? biz.turnover_lakh : 45.0);
  setVal('field-employees', biz.employee_count != null ? biz.employee_count : 4);
  setVal('field-state', biz.state || 'Madhya Pradesh');
  setVal('field-activity', biz.activity || 'Wholesale trading');
  setVal('field-address', biz.address || '');
  setVal('field-pan', biz.pan || '');
  setVal('field-gstin', biz.gstin || '');
  setVal('field-aadhaar', biz.aadhaar || 'XXXX-XXXX-1098');
  setVal('field-mobile', biz.mobile || '');
  setVal('field-email', biz.email || '');

  const chk = document.getElementById('field-special-state');
  if (chk) chk.checked = !!biz.special_category_state;
}

function updateDashboardHeader(biz) {
  setText('dash-biz-name', biz.name || 'ABC Traders');
  setText('dash-biz-owner', `Owner: ${biz.owner || 'Authorized Signatory'}`);
  setText('dash-biz-location', `${biz.address || biz.state || 'India'}`);
  setText('dash-biz-id-badge', `ID: ${biz.business_id}`);
  setText('chat-active-biz-label', biz.name || 'ABC Traders');
  setText('udyam-target-biz-name', biz.name || 'ABC Traders');
}

function updatePaperCertificatePreview(biz) {
  setText('cert-name', biz.name || 'ABC Traders');
  setText('cert-owner', biz.owner || 'Rahul Sharma');
  setText('cert-gstin', biz.gstin || '23ABCDE1234F1Z5');
  setText('cert-turnover', `${biz.turnover_lakh || 0.0}`);
  setText('cert-state', biz.state || 'Madhya Pradesh');
  setText('cert-activity', biz.activity || 'Commercial business');
}

async function saveAllBusinessProfileDetails() {
  const bizId = STATE.currentBusinessId || 'B005';
  const payload = {
    name: getVal('field-biz-name'),
    owner: getVal('field-owner-name'),
    business_type: getVal('field-biz-type'),
    turnover_lakh: parseFloat(getVal('field-turnover')) || 0.0,
    employee_count: parseInt(getVal('field-employees')) || 1,
    state: getVal('field-state'),
    special_category_state: document.getElementById('field-special-state')?.checked || false,
    activity: getVal('field-activity'),
    address: getVal('field-address'),
    pan: getVal('field-pan'),
    gstin: getVal('field-gstin'),
    aadhaar: getVal('field-aadhaar'),
    mobile: getVal('field-mobile'),
    email: getVal('field-email'),
  };

  try {
    const res = await fetch(`/api/business/${bizId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    if (res.ok) {
      STATE.businessData = result.business;
      updatePaperCertificatePreview(result.business);
      updateDashboardHeader(result.business);
      showToast('Profile details updated & synced to PostgreSQL!');
      fetchLiveAuditScorecard();
    } else {
      showToast('Failed to save profile: ' + (result.detail || 'Server error'));
    }
  } catch (err) {
    showToast('Network error saving details');
  }
}

function onStateDropdownChanged() {
  const state = getVal('field-state');
  const specialStates = ['Himachal Pradesh', 'Uttarakhand', 'Assam', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Tripura', 'Sikkim', 'Jammu & Kashmir'];
  const isSpecial = specialStates.some(s => state.includes(s));
  const chk = document.getElementById('field-special-state');
  if (chk) chk.checked = isSpecial;
  recalculateInstantAudit();
}

function recalculateInstantAudit() {
  const turnover = parseFloat(getVal('field-turnover')) || 0;
  const isSpecial = document.getElementById('field-special-state')?.checked || false;
  const bizType = getVal('field-biz-type');

  // Update certificate preview in real time
  setText('cert-turnover', `${turnover}`);
  setText('cert-name', getVal('field-biz-name') || 'ABC Traders');
  setText('cert-owner', getVal('field-owner-name') || 'Rahul Sharma');
  setText('cert-state', getVal('field-state') || 'Madhya Pradesh');

  // Instant threshold logic indicator
  const gstThreshold = (bizType === 'goods') ? (isSpecial ? 20 : 40) : (isSpecial ? 10 : 20);
  const gstApplies = turnover >= gstThreshold;

  const ringScore = gstApplies ? 92 : 98;
  setText('dash-health-score', `${ringScore}%`);
}

// ==========================================
// Statutory Audit Scorecard
// ==========================================
async function fetchLiveAuditScorecard() {
  const bizId = STATE.currentBusinessId || 'B005';
  try {
    const res = await fetch(`/api/audit/${bizId}`);
    if (!res.ok) throw new Error('Audit evaluation failed');
    const data = await res.json();
    STATE.auditFindings = data.findings || [];

    setText('dash-health-score', `${data.health_score}%`);
    renderScorecardGrid(data.findings);
  } catch (err) {
    console.warn('Audit error:', err);
  }
}

function renderScorecardGrid(findings) {
  const container = document.getElementById('scorecard-findings-grid');
  if (!container) return;
  container.innerHTML = '';

  findings.forEach(f => {
    const card = document.createElement('div');
    card.className = 'statutory-finding-card';

    const statusBadgeClass = f.applies ? 'status-applies' : 'status-exempt';
    const statusText = f.applies ? 'APPLIES / REQUIRED' : 'EXEMPT / OPTIONAL';

    card.innerHTML = `
      <div>
        <span class="finding-status-badge ${statusBadgeClass}">${statusText}</span>
        <h3 class="finding-req-title">${f.requirement}</h3>
        <p class="finding-reason-text">${f.reason}</p>
      </div>
      <div class="finding-footer">
        <span class="evidence-id-badge">Law: ${f.evidence_id}</span>
        <span style="font-size: 0.76rem; font-weight: 700; color: ${f.applies ? '#b45309' : '#059669'};">
          ${f.applies ? 'Action Required' : 'Compliant'}
        </span>
      </div>
    `;
    container.appendChild(card);
  });
}

// ==========================================
// Gemini Vision OCR Document Ingestion
// ==========================================
async function handleDocumentUpload(file) {
  if (!file) return;
  const statusBox = document.getElementById('ocr-status-box');
  const statusText = document.getElementById('ocr-status-text');
  if (statusBox) statusBox.style.display = 'block';
  if (statusText) statusText.innerHTML = `Uploading '${file.name}' & extracting details via Gemini Vision OCR...`;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('business_id', STATE.currentBusinessId || 'B005');
  if (STATE.currentUser) formData.append('user_id', STATE.currentUser.user_id);

  try {
    const res = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });
    const result = await res.json();

    if (res.ok && result.status === 'SUCCESS') {
      const ext = result.extracted_details || {};
      if (statusText) {
        statusText.innerHTML = `Extracted <strong>${result.document_type}</strong> (Confidence: ${(result.confidence_score * 100).toFixed(0)}%)! Synced to PostgreSQL.`;
      }
      showToast(`Document parsed: ${result.document_type}`);

      // Auto-populate form fields
      if (ext.business_name) setVal('field-biz-name', ext.business_name);
      if (ext.owner_name) setVal('field-owner-name', ext.owner_name);
      if (ext.pan) setVal('field-pan', ext.pan);
      if (ext.gstin) setVal('field-gstin', ext.gstin);
      if (ext.address) setVal('field-address', ext.address);
      if (ext.state) setVal('field-state', ext.state);
      if (ext.turnover_lakh) setVal('field-turnover', ext.turnover_lakh);
      if (ext.mobile) setVal('field-mobile', ext.mobile);
      if (ext.email) setVal('field-email', ext.email);

      // Refresh views
      recalculateInstantAudit();
      fetchLiveAuditScorecard();
    } else {
      if (statusText) statusText.innerHTML = `Error: ${result.detail || 'Extraction failed'}`;
      showToast('Document parsing issue');
    }
  } catch (err) {
    if (statusText) statusText.innerHTML = 'Network error during document upload.';
    showToast('Upload network error');
  }
}

function triggerQuickDocUpload() {
  navigateTo('dashboard');
  switchDashboardTab('profile');
  const input = document.getElementById('ocr-file-input');
  if (input) input.click();
}

// ==========================================
// Conversational Assistant (WhatsApp Style)
// ==========================================
async function sendDashboardChatMessage() {
  const input = document.getElementById('dash-chat-input');
  if (!input) return;
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  appendChatMessage(msg, 'sent', 'dash-chat-messages');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        business_id: STATE.currentBusinessId || 'B005',
      }),
    });
    const data = await res.json();
    appendAssistantReply(data, 'dash-chat-messages');
  } catch (err) {
    appendChatMessage('Error connecting to assistant server.', 'received', 'dash-chat-messages');
  }
}

function quickSendChat(text) {
  const input = document.getElementById('dash-chat-input');
  if (input) input.value = text;
  sendDashboardChatMessage();
}

function appendChatMessage(text, type, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${type}`;
  bubble.innerHTML = `
    ${text.replace(/\n/g, '<br>')}
    <div class="chat-meta">Just now ${type === 'sent' ? '<span class="chat-checks">✓✓</span>' : ''}</div>
  `;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function appendAssistantReply(data, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble received';

  let checklistHtml = '';
  if (data.checklist_steps && data.checklist_steps.length > 0) {
    checklistHtml = '<div class="chat-checklist">';
    data.checklist_steps.forEach(s => {
      checklistHtml += `<div class="chat-check-item"><span class="badge-check">✓</span> ${s.label}</div>`;
    });
    checklistHtml += '</div>';
  }

  bubble.innerHTML = `
    ${checklistHtml}
    <div>${data.reply.replace(/\n/g, '<br>')}</div>
    <div class="chat-meta">Just now</div>
  `;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// Phone hero mockup interaction
async function sendHeroPhoneMessage() {
  const input = document.getElementById('hero-phone-input');
  if (!input) return;
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  appendChatMessage(msg, 'sent', 'hero-phone-messages');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, business_id: 'B005' }),
    });
    const data = await res.json();
    appendAssistantReply(data, 'hero-phone-messages');
  } catch (err) {
    appendChatMessage('Grounded analysis ready.', 'received', 'hero-phone-messages');
  }
}

// ==========================================
// Udyam MSME Workflow Stepper
// ==========================================
async function triggerUdyamWorkflowStart() {
  const bizId = STATE.currentBusinessId || 'B005';
  showToast('Initiating official Udyam portal automation...');

  try {
    const res = await fetch('/api/workflow/udyam/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ business_id: bizId, dry_run: true }),
    });
    const summary = await res.json();

    setText('udyam-wf-status-badge', summary.status);

    if (summary.status === 'AWAITING_USER') {
      document.getElementById('udyam-ready-state').style.display = 'none';
      document.getElementById('udyam-otp-state').style.display = 'block';

      const prompt = summary.pending_user_action?.prompt || 'Enter Aadhaar OTP to authorize verification.';
      setText('udyam-prompt-text', prompt);

      document.getElementById('wf-step-3').classList.add('completed');
      document.getElementById('wf-step-4').classList.add('active');
    }
  } catch (err) {
    showToast('Workflow startup error');
  }
}

async function submitUdyamOTP() {
  const otp = getVal('udyam-otp-input') || '654321';
  showToast('Verifying OTP with e-KYC service...');

  try {
    const res = await fetch('/api/workflow/udyam/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow_id: STATE.activeWorkflowId,
        otp: otp,
      }),
    });
    const result = await res.json();

    if (result.status === 'RUNNING' || result.result) {
      document.getElementById('udyam-otp-state').style.display = 'none';
      document.getElementById('udyam-completed-state').style.display = 'block';

      const msg = result.result?.status_message || 'Aadhaar verified. Proceeding to enterprise unit details.';
      setText('udyam-result-msg', msg);
      setText('udyam-wf-status-badge', 'STAGE 1 VERIFIED');

      document.getElementById('wf-step-4').classList.add('completed');
      document.getElementById('wf-step-5').classList.add('active');
      showToast('Aadhaar OTP authorization verified!');
    }
  } catch (err) {
    showToast('Error submitting OTP');
  }
}

// ==========================================
// Authentication Modal & Persona Switching
// ==========================================
function openAuthModal(tab = 'signin') {
  const modal = document.getElementById('auth-modal');
  if (modal) modal.classList.add('active');
  switchAuthTab(tab);
}

function closeAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) modal.classList.remove('active');
}

function switchAuthTab(tab) {
  const btnIn = document.getElementById('btn-tab-signin');
  const btnReg = document.getElementById('btn-tab-register');
  const formIn = document.getElementById('form-signin');
  const formReg = document.getElementById('form-register');

  if (tab === 'signin') {
    btnIn?.classList.add('active');
    btnReg?.classList.remove('active');
    if (formIn) formIn.style.display = 'block';
    if (formReg) formReg.style.display = 'none';
  } else {
    btnReg?.classList.add('active');
    btnIn?.classList.remove('active');
    if (formReg) formReg.style.display = 'block';
    if (formIn) formIn.style.display = 'none';
  }
}

async function handleUserLogin() {
  const email = getVal('auth-signin-email');
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (res.ok && data.status === 'SUCCESS') {
      STATE.currentUser = data.user;
      if (data.business) {
        STATE.currentBusinessId = data.business.business_id;
      }
      closeAuthModal();
      showToast(`Welcome back, ${data.user.name}!`);
      navigateTo('dashboard');
      loadBusinessProfile(STATE.currentBusinessId);
    }
  } catch (err) {
    showToast('Login error');
  }
}

async function handleUserRegister() {
  const payload = {
    name: getVal('auth-reg-name'),
    business_name: getVal('auth-reg-biz'),
    email: getVal('auth-reg-email'),
    phone: getVal('auth-reg-phone'),
  };

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok && data.status === 'SUCCESS') {
      STATE.currentUser = data.user;
      if (data.business) {
        STATE.currentBusinessId = data.business.business_id;
      }
      closeAuthModal();
      showToast(`Account created for ${data.user.name}!`);
      navigateTo('dashboard');
      loadBusinessProfile(STATE.currentBusinessId);
    }
  } catch (err) {
    showToast('Registration error');
  }
}

function selectDemoAccount(email, bizId) {
  setVal('auth-signin-email', email);
  STATE.currentBusinessId = bizId;
  handleUserLogin();
}

// ==========================================
// Toast Utility
// ==========================================
function showToast(message) {
  const toast = document.getElementById('global-toast');
  const msgEl = document.getElementById('toast-message');
  if (!toast || !msgEl) return;
  msgEl.innerText = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// Helpers
function getVal(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.innerText = text;
}

// ==========================================
// Agent Studio & Execution Engine
// ==========================================

function updateAgentViewWithBusiness(biz) {
  if (!biz) return;
  setText('agent-active-biz-name', biz.name || 'ABC Traders');
  setText('agent-active-owner', `Owner: ${biz.owner || 'Rahul Sharma'}`);
  setText('agent-active-biz-id', `ID: ${biz.business_id || 'B005'}`);

  // Telemetry drawer
  setText('tele-biz-name', biz.name || 'ABC Traders');
  setText('tele-biz-owner', biz.owner || 'Rahul Sharma');
  setText('tele-biz-state', biz.state || 'Madhya Pradesh');
  setText('tele-biz-type', (biz.business_type || 'goods').toUpperCase());
  setText('tele-biz-gstin', biz.gstin || '23ABCDE1234F1Z5');
  setText('tele-biz-employees', `${biz.employee_count || 4} Staff`);

  const turnover = parseFloat(biz.turnover_lakh) || 0;
  const isSpecial = !!biz.special_category_state;
  const gstThresh = (biz.business_type === 'services') ? (isSpecial ? 10 : 20) : (isSpecial ? 20 : 40);
  setText('tele-meter-val', `₹${turnover}L / ₹${gstThresh}L GST Limit`);

  const pct = Math.min(100, Math.max(10, Math.round((turnover / (gstThresh * 1.5)) * 100)));
  const bar = document.getElementById('tele-meter-bar');
  if (bar) bar.style.width = `${pct}%`;

  // Matrix pills
  const gstReq = turnover >= gstThresh;
  setMatrixPill('matrix-gst-pill', gstReq ? 'REQUIRED' : 'EXEMPT', gstReq ? 'pill-required' : 'pill-exempt');

  const compLimit = isSpecial ? 75 : 150;
  const compEligible = turnover <= compLimit;
  setMatrixPill('matrix-comp-pill', compEligible ? 'ELIGIBLE' : 'NOT ELIGIBLE', compEligible ? 'pill-eligible' : 'pill-required');

  const udyamReq = turnover <= 500;
  setMatrixPill('matrix-udyam-pill', udyamReq ? 'REQUIRED (Micro)' : 'REQUIRED (Small)', 'pill-required');

  const employees = parseInt(biz.employee_count) || 1;
  setMatrixPill('matrix-epf-pill', employees >= 20 ? 'REQUIRED' : 'EXEMPT (<20)', employees >= 20 ? 'pill-required' : 'pill-exempt');
  setMatrixPill('matrix-esi-pill', employees >= 10 ? 'REQUIRED' : 'EXEMPT (<10)', employees >= 10 ? 'pill-required' : 'pill-exempt');

  // Memo modal info
  setText('memo-modal-biz-name', biz.name || 'ABC Traders');
  setText('memo-modal-biz-sub', `${biz.owner} • ${biz.state} • ₹${turnover}L Turnover • ID: ${biz.business_id}`);
  const now = new Date();
  setText('memo-modal-timestamp', now.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }));
}

function setMatrixPill(elementId, text, className) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerText = text;
  el.className = `matrix-pill ${className}`;
}

async function runAgentPlaybook(missionKey) {
  const titles = {
    full_audit: 'Execute Full Statutory Health Audit across 6 regulatory domains',
    udyam_automate: 'Initiate Autonomous Udyam MSME Portal Registration Pipeline',
    composition_check: 'Evaluate Section 10 Composition Scheme Eligibility & Tax Slabs',
    labor_check: 'Audit EPFO & ESIC Employee Headcount Statutory Risk Barriers',
  };

  const userPrompt = titles[missionKey] || `Execute mission: ${missionKey}`;
  appendAgentUserPrompt(userPrompt);

  const payload = {
    mission: missionKey,
    business_id: STATE.currentBusinessId || 'B005',
    workflow_id: STATE.activeWorkflowId || `WF-UDYAM-${STATE.currentBusinessId || 'B005'}`,
  };

  await executeAgentPipeline(payload);
}

function quickAgentPrompt(text) {
  const input = document.getElementById('agent-custom-input');
  if (input) input.value = text;
  sendAgentCustomPrompt();
}

async function sendAgentCustomPrompt() {
  const input = document.getElementById('agent-custom-input');
  if (!input) return;
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = '';

  appendAgentUserPrompt(prompt);

  const payload = {
    prompt: prompt,
    business_id: STATE.currentBusinessId || 'B005',
    workflow_id: STATE.activeWorkflowId || `WF-UDYAM-${STATE.currentBusinessId || 'B005'}`,
  };

  await executeAgentPipeline(payload);
}

async function executeAgentPipeline(payload) {
  setAgentBadge('RUNNING...');
  const loadingCard = appendAgentLoadingIndicator();

  try {
    const res = await fetch('/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    loadingCard.remove();
    setAgentBadge('READY');

    if (res.ok && data.status === 'SUCCESS') {
      renderAgentExecutionResult(data);
      if (data.business) {
        STATE.businessData = data.business;
        updateAgentViewWithBusiness(data.business);
      }
      if (data.findings && data.findings.length > 0) {
        STATE.auditFindings = data.findings;
      }
      if (data.workflow_status) {
        updateTelemetryWorkflowStatus(data.workflow_status, data.workflow_id);
      }
    } else {
      appendAgentResponseCard(`⚠️ **Agent Error:** ${data.detail || 'Execution encountered an unexpected issue.'}`);
    }
  } catch (err) {
    loadingCard.remove();
    setAgentBadge('ERROR');
    appendAgentResponseCard('⚠️ **Network Error:** Could not connect to the agent execution engine.');
  }
}

function appendAgentUserPrompt(text) {
  const viewport = document.getElementById('agent-feed-viewport');
  if (!viewport) return;

  const card = document.createElement('div');
  card.className = 'agent-user-prompt-card';
  card.innerHTML = `
    <div>${escapeHtml(text)}</div>
    <div class="agent-user-meta">Just now • User Command</div>
  `;
  viewport.appendChild(card);
  viewport.scrollTop = viewport.scrollHeight;
}

function appendAgentLoadingIndicator() {
  const viewport = document.getElementById('agent-feed-viewport');
  const card = document.createElement('div');
  card.className = 'execution-trace-card';
  card.id = 'agent-loading-card';
  card.innerHTML = `
    <div style="display: flex; align-items: center; gap: 10px; color: var(--emerald-800); font-weight: 600; font-size: 0.85rem;">
      <span class="step-icon-status step-status-run">⟳</span>
      <span>Agent reasoning & orchestrating tools (database lookup, rules evaluation, regulatory RAG)...</span>
    </div>
  `;
  if (viewport) {
    viewport.appendChild(card);
    viewport.scrollTop = viewport.scrollHeight;
  }
  return card;
}

function appendAgentResponseCard(markdownText) {
  const viewport = document.getElementById('agent-feed-viewport');
  if (!viewport) return;
  const memoCard = document.createElement('div');
  memoCard.className = 'agent-response-memo';
  memoCard.innerHTML = parseMarkdownToHtml(markdownText);
  viewport.appendChild(memoCard);
  viewport.scrollTop = viewport.scrollHeight;
}

function renderAgentExecutionResult(data) {
  const viewport = document.getElementById('agent-feed-viewport');
  if (!viewport) return;

  // 1. Render Execution Steps Trace Card if steps exist
  if (data.steps && data.steps.length > 0) {
    const traceCard = document.createElement('div');
    traceCard.className = 'execution-trace-card';

    let stepsHtml = '';
    data.steps.forEach(s => {
      const isComplete = s.status === 'COMPLETED';
      const rawInputOutput = JSON.stringify({ input: s.input, output: s.output }, null, 2);
      const toggleId = `step-raw-${Math.random().toString(36).substr(2, 9)}`;

      stepsHtml += `
        <div class="trace-step-item">
          <div class="step-icon-status ${isComplete ? 'step-status-done' : 'step-status-wait'}">
            ${isComplete ? '✓' : '!'}
          </div>
          <div class="step-content">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span class="step-tool-name">tool::${s.tool_called}</span>
              <span style="font-size: 0.7rem; color: var(--slate-400);">Step ${s.step_num}</span>
            </div>
            <div class="step-title-text">${s.title}</div>
            <span class="step-payload-toggle" onclick="toggleRawStepBox('${toggleId}')">Inspect Tool Payload</span>
            <div class="step-raw-box" id="${toggleId}">${escapeHtml(rawInputOutput)}</div>
          </div>
        </div>
      `;
    });

    traceCard.innerHTML = `
      <div class="trace-card-header">
        <div class="trace-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
          Autonomous Tool Execution Trace (${data.steps.length} Tools)
        </div>
        <span class="trace-time-pill">${data.execution_time_ms || 45}ms</span>
      </div>
      <div class="trace-steps-list">
        ${stepsHtml}
      </div>
    `;
    viewport.appendChild(traceCard);
  }

  // 2. Render Main Formatted Response Memo
  if (data.summary) {
    const memoCard = document.createElement('div');
    memoCard.className = 'agent-response-memo';
    memoCard.innerHTML = parseMarkdownToHtml(data.summary);
    viewport.appendChild(memoCard);
  }

  // 3. Render Regulatory Citations if present
  if (data.citations && data.citations.length > 0) {
    const citeWrap = document.createElement('div');
    citeWrap.className = 'citations-wrapper';
    
    let cardsHtml = '';
    data.citations.forEach(c => {
      cardsHtml += `
        <div class="citation-card">
          <div class="citation-card-top">
            <span class="citation-id">${c.id || 'REG'}</span>
            <span class="citation-source">${c.source || 'Official Gazette'}</span>
          </div>
          <div style="font-weight: 700; font-size: 0.82rem; color: var(--slate-900); margin-bottom: 2px;">
            ${c.title}
          </div>
          <div class="citation-text">${c.text}</div>
        </div>
      `;
    });

    citeWrap.innerHTML = `
      <div class="citation-header-label">Grounding Statutory Evidence Citations</div>
      <div class="citation-strip">
        ${cardsHtml}
      </div>
    `;
    viewport.appendChild(citeWrap);
  }

  // 4. Render Human-In-The-Loop Checkpoint Card if required
  if (data.hitl_action) {
    const hitl = data.hitl_action;
    const hitlCard = document.createElement('div');
    hitlCard.className = 'hitl-action-card';
    hitlCard.id = 'agent-active-hitl-card';

    hitlCard.innerHTML = `
      <div class="hitl-header">
        <span style="font-size: 1.3rem;">⚠️</span>
        <div class="hitl-title">Human-In-The-Loop Authorization Required</div>
      </div>
      <div class="hitl-prompt-text">
        ${escapeHtml(hitl.prompt || 'Please enter the 6-digit Aadhaar OTP to authorize this registration step.')}
      </div>
      <div class="hitl-input-row">
        <input type="text" id="hitl-otp-input" class="hitl-otp-field" placeholder="123456" maxlength="6" value="654321">
        <button type="button" class="hitl-demo-btn" onclick="document.getElementById('hitl-otp-input').value='654321'">
          Quick Demo OTP (654321)
        </button>
        <button class="btn btn-primary btn-sm" onclick="submitAgentHITL('${hitl.workflow_id || 'WF-UDYAM-B005'}')">
          Authorize & Resume Workflow
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
        </button>
      </div>
      <div style="font-size: 0.74rem; color: #92400e; margin-top: 8px;">
        ${hitl.disclaimer || 'Statutory UIDAI privacy mandates require explicit human OTP approval.'}
      </div>
    `;
    viewport.appendChild(hitlCard);
  }

  viewport.scrollTop = viewport.scrollHeight;
}

async function submitAgentHITL(workflowId) {
  const input = document.getElementById('hitl-otp-input');
  const otp = input ? input.value.trim() : '654321';
  if (!otp) {
    showToast('Please enter the 6-digit OTP.');
    return;
  }

  const activeCard = document.getElementById('agent-active-hitl-card');
  if (activeCard) activeCard.style.opacity = '0.5';

  appendAgentUserPrompt(`Submitted 6-Digit Aadhaar OTP: ******`);
  showToast('Submitting OTP to e-KYC service...');

  const payload = {
    mission: 'resume_workflow',
    workflow_id: workflowId,
    business_id: STATE.currentBusinessId || 'B005',
    user_action: { otp: otp },
  };

  await executeAgentPipeline(payload);
  if (activeCard) activeCard.remove();
}

function toggleRawStepBox(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.display = el.style.display === 'block' ? 'none' : 'block';
  }
}

function toggleAgentDocUpload() {
  const zone = document.getElementById('agent-embedded-ocr-zone');
  if (zone) {
    zone.style.display = zone.style.display === 'block' ? 'none' : 'block';
  }
}

async function handleAgentDocumentUpload(file) {
  if (!file) return;
  toggleAgentDocUpload();
  appendAgentUserPrompt(`Uploaded document photo: '${file.name}'`);
  showToast(`Analyzing '${file.name}' with Gemini Vision OCR...`);

  const formData = new FormData();
  formData.append('file', file);
  formData.append('business_id', STATE.currentBusinessId || 'B005');
  if (STATE.currentUser) formData.append('user_id', STATE.currentUser.user_id);

  try {
    const res = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });
    const result = await res.json();

    if (res.ok && result.status === 'SUCCESS') {
      showToast(`Document parsed: ${result.document_type}`);
      // Now command agent to cross check
      await executeAgentPipeline({
        prompt: `I just uploaded a photo of my ${result.document_type}. Please verify my statutory profile and check if any compliance details need updating.`,
        business_id: STATE.currentBusinessId || 'B005',
      });
      loadBusinessProfile(STATE.currentBusinessId);
    } else {
      showToast('Document parsing issue');
    }
  } catch (err) {
    showToast('Upload network error');
  }
}

function resetAgentSession() {
  const viewport = document.getElementById('agent-feed-viewport');
  if (!viewport) return;
  viewport.innerHTML = `
    <div class="agent-briefing-banner" id="agent-welcome-briefing">
      <div class="agent-briefing-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
        New Session Initialized
      </div>
      <div>
        Agent memory reset. Connected to <strong>PostgreSQL Business Vault</strong>. 
        Select a mission playbook above or command the agent below.
      </div>
    </div>
  `;
  setAgentBadge('READY');
  showToast('Agent session refreshed');
}

function setAgentBadge(text) {
  const el = document.getElementById('agent-active-badge');
  if (el) el.innerText = text;
}

function updateTelemetryWorkflowStatus(status, wfId) {
  setText('tele-wf-status', status);
  const badge = document.getElementById('tele-wf-status');
  if (badge) {
    if (status === 'AWAITING_USER') badge.className = 'wf-state-badge wf-awaiting';
    else if (status.includes('VERIFIED') || status === 'COMPLETED') badge.className = 'wf-state-badge wf-verified';
    else badge.className = 'wf-state-badge wf-ready';
  }
  if (wfId) setText('tele-wf-id', wfId);

  const descEl = document.getElementById('tele-wf-desc');
  if (descEl) {
    if (status === 'AWAITING_USER') descEl.innerText = 'Paused at Aadhaar OTP authorization boundary.';
    else if (status.includes('VERIFIED')) descEl.innerText = 'Stage 1 Aadhaar authenticated & verified in PostgreSQL.';
    else descEl.innerText = `Pipeline status: ${status}`;
  }
}

function openOfficialMemoModal() {
  const modal = document.getElementById('memo-modal');
  if (!modal) return;
  updateOfficialMemoContent();
  modal.classList.add('active');
}

function closeOfficialMemoModal() {
  const modal = document.getElementById('memo-modal');
  if (modal) modal.classList.remove('active');
}

function updateOfficialMemoContent() {
  const body = document.getElementById('memo-modal-body-content');
  const biz = STATE.businessData || {};
  if (!body) return;

  const findings = STATE.auditFindings || [];
  let findingsHtml = '';
  findings.forEach(f => {
    findingsHtml += `
      <div style="padding: 10px; border-bottom: 1px solid rgba(15, 23, 42, 0.08); display: flex; justify-content: space-between;">
        <div>
          <strong style="color: ${f.applies ? '#b91c1c' : '#15803d'};">${f.requirement}</strong>
          <div style="font-size: 0.8rem; color: var(--slate-600); margin-top: 2px;">${f.reason}</div>
        </div>
        <div style="text-align: right;">
          <span class="evidence-id-badge">${f.evidence_id}</span>
          <div style="font-size: 0.72rem; font-weight: 700; color: ${f.applies ? '#b91c1c' : '#15803d'}; margin-top: 4px;">
            ${f.applies ? 'LIABILITY' : 'COMPLIANT'}
          </div>
        </div>
      </div>
    `;
  });

  body.innerHTML = `
    <div style="background: var(--slate-50); padding: 14px; border-radius: var(--radius-sm); margin-bottom: 16px;">
      <h4 style="font-size: 0.9rem; font-weight: 700; color: var(--slate-900); margin-bottom: 6px;">Enterprise Operational Metrics</h4>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.82rem;">
        <div><strong>Turnover:</strong> ₹${biz.turnover_lakh || 55.0} Lakhs</div>
        <div><strong>Headcount:</strong> ${biz.employee_count || 4} Staff</div>
        <div><strong>GSTIN:</strong> ${biz.gstin || '23ABCDE1234F1Z5'}</div>
        <div><strong>PAN:</strong> ${biz.pan || 'ABCDE1234F'}</div>
      </div>
    </div>
    <h4 style="font-size: 0.9rem; font-weight: 700; color: var(--slate-900); margin-bottom: 8px;">Statutory Threshold Audit Findings</h4>
    <div style="border: 1px solid rgba(15, 23, 42, 0.1); border-radius: var(--radius-sm);">
      ${findingsHtml || '<p style="padding: 12px; color: var(--slate-500);">Run an audit to populate live statutory findings.</p>'}
    </div>
  `;
}

function parseMarkdownToHtml(md) {
  if (!md) return '';
  return md
    .replace(/### (.*?)\n/g, '<h3>$1</h3>')
    .replace(/#### (.*?)\n/g, '<h4>$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/---\n/g, '<hr>')
    .replace(/> \[!IMPORTANT\]\n> (.*?)\n/g, '<div style="padding: 10px 14px; background: #fffbeb; border-left: 3px solid #f59e0b; border-radius: 4px; margin: 10px 0; color: #92400e;"><strong>IMPORTANT:</strong> $1</div>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
