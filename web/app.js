const API_BASE = "";

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

  event.target.classList.add('active');
  document.getElementById(tabId).classList.add('active');

  if (tabId === 'tab-ingest') loadCatalog();
  if (tabId === 'tab-audit') loadAuditLogs();
}

async function sendIntent() {
  const inputEl = document.getElementById('chat-input');
  const intent = inputEl.value.trim();
  if (!intent) return;

  inputEl.value = '';
  appendUserMessage(intent);
  appendAgentTyping();

  try {
    const formData = new FormData();
    formData.append('intent', intent);
    formData.append('merchant_id', 'rzp_merchant_001');

    const res = await fetch(`${API_BASE}/agent/buy`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    removeAgentTyping();
    renderAgentResponse(data);
  } catch (err) {
    removeAgentTyping();
    appendAgentMessage(`❌ Error processing intent: ${err.message}`);
  }
}

function runPreset(text) {
  document.getElementById('chat-input').value = text;
  sendIntent();
}

function appendUserMessage(text) {
  const win = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.className = 'chat-bubble chat-bubble-user';
  div.textContent = text;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

function appendAgentTyping() {
  const win = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.id = 'typing-indicator';
  div.className = 'chat-bubble chat-bubble-agent';
  div.innerHTML = '⏳ <em>Agent reasoning over catalog & checking guardrails...</em>';
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

function removeAgentTyping() {
  const indicator = document.getElementById('typing-indicator');
  if (indicator) indicator.remove();
}

function renderAgentResponse(data) {
  const win = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.className = 'chat-bubble chat-bubble-agent';

  let html = `<div>${data.message || ''}</div>`;

  if (data.steps && data.steps.length > 0) {
    html += `<div style="margin-top: 10px; font-size: 12px; opacity: 0.9;"><strong>Agent Execution Steps:</strong>`;
    data.steps.forEach(step => {
      html += `<div class="tool-badge">🔧 ${step.action} ${step.selected_product ? '→ ' + step.selected_product : ''}</div>`;
    });
    html += `</div>`;
  }

  if (data.payment_link) {
    html += `
      <div class="checkout-card">
        <div style="font-weight: 700; color: #34d399;">💳 Razorpay Test Checkout Ready</div>
        <div style="font-size: 12px; margin-top: 4px;">Order ID: <code>${data.order_id}</code></div>
        <a href="${data.payment_link}" target="_blank" class="payment-btn">Complete Test Payment →</a>
      </div>
    `;
  }

  if (data.status === 'blocked_by_guardrail') {
    html += `
      <div style="margin-top: 10px; padding: 10px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px;">
        <strong style="color: #f87171;">🛡️ Guardrail Blocked Transaction:</strong>
        <div style="font-size: 12px; margin-top: 4px;">${data.message}</div>
      </div>
    `;
  }

  div.innerHTML = html;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

function appendAgentMessage(text) {
  const win = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.className = 'chat-bubble chat-bubble-agent';
  div.textContent = text;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

async function loadCatalog() {
  try {
    const res = await fetch(`${API_BASE}/catalog/rzp_merchant_001`);
    const data = await res.json();

    document.getElementById('product-count').textContent = data.count || 0;
    const grid = document.getElementById('product-grid');
    grid.innerHTML = '';

    (data.products || []).forEach(p => {
      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <div class="product-title">${p.name}</div>
        <div class="product-price">₹${p.price.toLocaleString()}</div>
        <div style="font-size: 12px; color: var(--text-muted); margin: 6px 0;">${p.description}</div>
        <div style="font-size: 11px; display: flex; justify-content: space-between; margin-top: 8px; color: var(--text-muted);">
          <span>Stock: <strong>${p.stock}</strong></span>
          <span>COD: <strong>${p.cod_available ? 'Yes' : 'No'}</strong></span>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading catalog:', err);
  }
}

async function uploadCatalogFile() {
  const fileInput = document.getElementById('file-upload');
  if (!fileInput.files.length) {
    alert('Please select a file to upload.');
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('merchant_id', 'rzp_merchant_001');

  document.getElementById('ingest-status').textContent = '⏳ Ingesting and vector embedding file...';

  try {
    const res = await fetch(`${API_BASE}/ingest`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    document.getElementById('ingest-status').textContent = `✅ Successfully ingested ${data.product_count} products in ${data.elapsed_seconds}s!`;
    loadCatalog();
  } catch (err) {
    document.getElementById('ingest-status').textContent = `❌ Ingestion failed: ${err.message}`;
  }
}

async function uploadCatalogUrl() {
  const urlInput = document.getElementById('url-upload');
  const url = urlInput.value.trim();
  if (!url) return;

  const formData = new FormData();
  formData.append('source_url', url);
  formData.append('merchant_id', 'rzp_merchant_001');

  document.getElementById('ingest-status').textContent = '⏳ Scraping and embedding URL...';

  try {
    const res = await fetch(`${API_BASE}/ingest`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    document.getElementById('ingest-status').textContent = `✅ Ingested ${data.product_count} items from URL in ${data.elapsed_seconds}s!`;
    loadCatalog();
  } catch (err) {
    document.getElementById('ingest-status').textContent = `❌ Scraping failed: ${err.message}`;
  }
}

async function loadAuditLogs() {
  try {
    const res = await fetch(`${API_BASE}/audit/logs`);
    const data = await res.json();

    const tbody = document.getElementById('audit-table-body');
    tbody.innerHTML = '';

    (data.logs || []).reverse().forEach(log => {
      const tr = document.createElement('tr');
      const timeStr = new Date(log.timestamp).toLocaleTimeString();
      let statusClass = 'color: #34d399;';
      if (log.status === 'BLOCKED') statusClass = 'color: #f87171;';
      if (log.status === 'NO_MATCH') statusClass = 'color: #fbbf24;';

      tr.innerHTML = `
        <td style="font-family: monospace;">${timeStr}</td>
        <td><span class="badge" style="font-size: 11px;">${log.event_type}</span></td>
        <td><code style="color: #a5b4fc;">${log.tool_name}</code></td>
        <td style="${statusClass} font-weight: 700;">${log.status}</td>
        <td style="font-size: 12px; color: var(--text-muted);">${log.reasoning || JSON.stringify(log.outputs)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading audit logs:', err);
  }
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
  loadCatalog();
});
