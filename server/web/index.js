// STATE MANAGEMENT
let activeTab = 'console';
let documents = [];
let inventory = [];
let reports = [];
let traces = [];
let eventSource = null;

// INITIALIZE
document.addEventListener('DOMContentLoaded', () => {
    // Initialize icons
    lucide.createIcons();
    
    // Load initial data
    fetchDocuments();
    fetchInventory();
    fetchReports();
    fetchTraces();
    
    // Check MCP server status
    checkMcpStatus();
    setInterval(checkMcpStatus, 5000);
});

// SWITCH TABS
function switchTab(tabName) {
    activeTab = tabName;
    
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeBtn = document.getElementById(`btn-${tabName}`);
    if (activeBtn) activeBtn.classList.add('active');
    
    // Update panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    const activePanel = document.getElementById(`panel-${tabName}`);
    if (activePanel) activePanel.classList.add('active');

    // Fetch tab-specific data
    if (tabName === 'documents') fetchDocuments();
    if (tabName === 'inventory') fetchInventory();
    if (tabName === 'reports') fetchReports();
    if (tabName === 'traces') fetchTraces();
}

// CHECK CORE MCP SERVER PORT 8000 STATUS
async function checkMcpStatus() {
    try {
        const res = await fetch('/api/mcp-status');
        const data = await res.json();
        const indicator = document.getElementById('mcp-server-status');
        const warning = document.getElementById('mcp-offline-warning');
        
        if (data.online) {
            indicator.innerHTML = `<span class="status-dot online"></span><span class="status-label">Core MCP Server: Online</span>`;
            warning.style.display = 'none';
        } else {
            indicator.innerHTML = `<span class="status-dot offline"></span><span class="status-label">Core MCP Server: Offline</span>`;
            warning.style.display = 'flex';
        }
    } catch (err) {
        console.error('Failed to check MCP server status:', err);
    }
}

// USE PRESET QUERY
function usePreset(question) {
    document.getElementById('question-input').value = question;
}

// CLEAR LOGS
function clearConsole() {
    const consoleBody = document.getElementById('console-output');
    consoleBody.innerHTML = `
        <div class="console-placeholder">
            <i data-lucide="terminal"></i>
            <p>Logs cleared. Ready to start next execution.</p>
        </div>
    `;
    lucide.createIcons();
    resetPipelineVisuals();
}

// RESET WORKFLOW PIPELINE STATES
function resetPipelineVisuals() {
    document.querySelectorAll('.pipeline-step').forEach(step => {
        step.className = 'pipeline-step';
        step.querySelector('.step-status').textContent = 'Idle';
    });
}

// STREAM LOGGER AND RUN CREW
async function runCrew(event) {
    if (event) event.preventDefault();
    
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();
    if (!question) return;

    // Reset UI
    clearConsole();
    resetPipelineVisuals();
    
    const consoleBody = document.getElementById('console-output');
    consoleBody.innerHTML = ''; // Clear placeholder
    
    const runBtn = document.getElementById('btn-run-crew');
    runBtn.disabled = true;
    runBtn.querySelector('span').textContent = 'Running Pipeline...';

    // Start researcher state visually
    updatePipelineStep('step-research', 'active', 'Researching');

    try {
        // Trigger Run
        const res = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        
        const data = await res.json();
        if (res.status !== 200) {
            appendLogLine(`[Error Starting Session]: ${data.detail || 'Unknown error'}`, 'error');
            runBtn.disabled = false;
            runBtn.querySelector('span').textContent = 'Initialize Research Crew';
            updatePipelineStep('step-research', 'idle', 'Failed');
            return;
        }

        appendLogLine(`[System]: Session initialized. Connecting to active log stream...`, 'system');

        // Close existing stream if any
        if (eventSource) eventSource.close();
        
        // Open SSE Stream
        eventSource = new EventSource('/api/stream');
        
        eventSource.onmessage = (event) => {
            const line = event.data;
            
            // Handle Heartbeat ping
            if (line === '__PING__') return;
            
            // Handle Finished Sentinel
            if (line.startsWith('__FINISHED__')) {
                const parts = line.split(':');
                const status = parts[1];
                const result = parts.slice(2).join(':');
                
                eventSource.close();
                runBtn.disabled = false;
                runBtn.querySelector('span').textContent = 'Initialize Research Crew';
                
                if (status === 'completed') {
                    appendLogLine(`\n[System]: Crew finished successfully!`, 'success');
                    updatePipelineStep('step-verify', 'completed', 'Approved');
                    // Reload outputs
                    fetchReports();
                    fetchTraces();
                } else {
                    appendLogLine(`\n[System]: Crew failed or aborted.`, 'error');
                }
                return;
            }
            
            // Handle Human-in-the-Loop approval prompt
            if (line === '__WAITING_FOR_INPUT__') {
                updatePipelineStep('step-verify', 'active', 'Awaiting Human');
                document.getElementById('hitl-modal').classList.add('active');
                document.getElementById('hitl-input').focus();
                appendLogLine(`\n[System ALERT]: Fact Checker agent requires human validation. Displaying review card...`, 'warn');
                return;
            }
            
            // Classify and write log lines
            writeStyledLog(line);
        };
        
        eventSource.onerror = (err) => {
            console.error('SSE Stream Error:', err);
            appendLogLine(`[System Error]: Disconnected from log stream.`, 'error');
            eventSource.close();
            runBtn.disabled = false;
            runBtn.querySelector('span').textContent = 'Initialize Research Crew';
        };

    } catch (err) {
        appendLogLine(`[System Error]: Failed to contact web server: ${err.message}`, 'error');
        runBtn.disabled = false;
        runBtn.querySelector('span').textContent = 'Initialize Research Crew';
    }
}

// DETECT WORKFLOW STEP HIGHLIGHTS & LOG STYLE
function writeStyledLog(line) {
    let type = 'default';
    
    // Highlight working agents
    if (line.includes('Operations Researcher') || line.includes('Agent: Operations Researcher')) {
        updatePipelineStep('step-research', 'active', 'Researching');
    }
    if (line.includes('Report Writer') || line.includes('Agent: Report Writer')) {
        updatePipelineStep('step-research', 'completed', 'Done');
        updatePipelineStep('step-write', 'active', 'Synthesizing');
    }
    if (line.includes('Fact Checker') || line.includes('Agent: Fact Checker')) {
        updatePipelineStep('step-write', 'completed', 'Done');
        updatePipelineStep('step-verify', 'active', 'Fact-checking');
    }
    if (line.includes('save_report') || line.includes('Tool: save_report')) {
        updatePipelineStep('step-verify', 'completed', 'Verified');
    }

    // Color logging lines
    if (line.startsWith('Error') || line.includes('RuntimeError') || line.includes('SECURITY ALERT') || line.includes('Aborting')) {
        type = 'error';
    } else if (line.includes('Working Agent:') || line.includes('Running Task:')) {
        type = 'system';
    } else if (line.includes('Using Tool:') || line.includes('Tool Call:') || line.includes('Tool Output:')) {
        type = 'info';
    } else if (line.includes('WARNING') || line.includes('Alert') || line.includes('human input')) {
        type = 'warn';
    } else if (line.includes('saved to:') || line.includes('Success')) {
        type = 'success';
    }
    
    appendLogLine(line, type);
}

function updatePipelineStep(stepId, state, statusText) {
    const el = document.getElementById(stepId);
    if (!el) return;
    
    el.className = 'pipeline-step';
    if (state === 'active') el.classList.add('active');
    if (state === 'completed') el.classList.add('completed');
    
    el.querySelector('.step-status').textContent = statusText;
}

function appendLogLine(text, type) {
    const consoleBody = document.getElementById('console-output');
    const lineEl = document.createElement('div');
    lineEl.className = 'console-line';
    if (type !== 'default') lineEl.classList.add(`console-${type}`);
    lineEl.textContent = text;
    consoleBody.appendChild(lineEl);
    
    const autoScroll = document.getElementById('auto-scroll-check').checked;
    if (autoScroll) {
        consoleBody.scrollTop = consoleBody.scrollHeight;
    }
}

// SUBMIT HUMAN IN THE LOOP INPUT
async function submitHITL(inputValue) {
    const input = inputValue || document.getElementById('hitl-input').value.trim();
    if (!input) return;
    
    // Close modal
    document.getElementById('hitl-modal').classList.remove('active');
    document.getElementById('hitl-input').value = '';
    
    appendLogLine(`[System]: Sending input to Fact Checker: "${input}"`, 'system');
    
    try {
        const res = await fetch('/api/human-input', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input })
        });
        const data = await res.json();
        if (res.status !== 200) {
            appendLogLine(`[System Error]: Failed to transmit input: ${data.detail}`, 'error');
        } else {
            updatePipelineStep('step-verify', 'completed', 'Approved');
        }
    } catch (err) {
        appendLogLine(`[System Error]: Failed to transmit input: ${err.message}`, 'error');
    }
}

function submitHITLCustom() {
    const text = document.getElementById('hitl-input').value.trim();
    if (text) {
        submitHITL(text);
    }
}

// FETCH SOP DOCUMENTS
async function fetchDocuments() {
    try {
        const res = await fetch('/api/documents');
        documents = await res.json();
        
        // Update badges
        document.getElementById('doc-count').textContent = documents.length;
        
        if (activeTab === 'documents') {
            renderDocumentsList();
        }
    } catch (err) {
        console.error('Error fetching documents:', err);
    }
}

function renderDocumentsList(filteredDocs = documents) {
    const listEl = document.getElementById('documents-list');
    listEl.innerHTML = '';
    
    if (filteredDocs.length === 0) {
        listEl.innerHTML = '<div class="viewer-placeholder"><p>No matching documents found</p></div>';
        return;
    }
    
    filteredDocs.forEach((doc, idx) => {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerHTML = `
            <div class="list-item-title">${doc.name}</div>
            <div class="list-item-meta">Size: ${(doc.size / 1024).toFixed(2)} KB | ${doc.updated_at}</div>
        `;
        item.onclick = () => selectDocument(doc, item);
        listEl.appendChild(item);
    });
}

function selectDocument(doc, itemEl) {
    document.querySelectorAll('#documents-list .list-item').forEach(el => el.classList.remove('selected'));
    itemEl.classList.add('selected');
    
    const header = document.getElementById('doc-viewer-header');
    header.innerHTML = `
        <h2>${doc.name}</h2>
        <p>Last Modified: ${doc.updated_at} | Size: ${(doc.size / 1024).toFixed(2)} KB</p>
    `;
    
    const body = document.getElementById('doc-viewer-body');
    body.innerHTML = `<pre><code>${escapeHtml(doc.content)}</code></pre>`;
}

function filterDocuments() {
    const query = document.getElementById('doc-search').value.toLowerCase();
    const filtered = documents.filter(doc => 
        doc.name.toLowerCase().includes(query) || 
        (doc.content && doc.content.toLowerCase().includes(query))
    );
    renderDocumentsList(filtered);
}

// FETCH INVENTORY RECORDS
async function fetchInventory() {
    try {
        const res = await fetch('/api/inventory');
        inventory = await res.json();
        
        document.getElementById('inv-count').textContent = inventory.length;
        
        if (activeTab === 'inventory') {
            renderInventoryTable();
        }
    } catch (err) {
        console.error('Error fetching inventory:', err);
    }
}

function renderInventoryTable(filteredInventory = inventory) {
    const tableBody = document.getElementById('inventory-table-body');
    tableBody.innerHTML = '';
    
    if (filteredInventory.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No inventory records match your query</td></tr>';
        return;
    }
    
    filteredInventory.forEach(row => {
        const tr = document.createElement('tr');
        
        // Format status badge
        const statusClass = `badge-${row.status}`;
        
        tr.innerHTML = `
            <td><strong>${row.id}</strong></td>
            <td>${row.product_name}</td>
            <td><code>${row.sku}</code></td>
            <td>${row.quantity}</td>
            <td>$${row.unit_price}</td>
            <td><span class="badge-status ${statusClass}">${row.status.replace('_', ' ')}</span></td>
            <td>${row.last_updated}</td>
        `;
        tableBody.appendChild(tr);
    });
}

function filterInventory() {
    const query = document.getElementById('inv-search').value.toLowerCase();
    const filtered = inventory.filter(row => 
        row.product_name.toLowerCase().includes(query) || 
        row.sku.toLowerCase().includes(query) ||
        row.status.toLowerCase().includes(query)
    );
    renderInventoryTable(filtered);
}

// FETCH GENERATED REPORTS
async function fetchReports() {
    try {
        const res = await fetch('/api/reports');
        reports = await res.json();
        
        document.getElementById('report-count').textContent = reports.length;
        
        if (activeTab === 'reports') {
            renderReportsList();
        }
    } catch (err) {
        console.error('Error fetching reports:', err);
    }
}

function renderReportsList() {
    const listEl = document.getElementById('reports-list');
    listEl.innerHTML = '';
    
    if (reports.length === 0) {
        listEl.innerHTML = '<div class="viewer-placeholder"><p>No reports generated yet</p></div>';
        return;
    }
    
    reports.forEach((report, idx) => {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerHTML = `
            <div class="list-item-title">${report.name}</div>
            <div class="list-item-meta">Created: ${report.created_at}</div>
        `;
        item.onclick = () => selectReport(report, item);
        listEl.appendChild(item);
    });
}

function selectReport(report, itemEl) {
    document.querySelectorAll('#reports-list .list-item').forEach(el => el.classList.remove('selected'));
    itemEl.classList.add('selected');
    
    const header = document.getElementById('report-viewer-header');
    header.innerHTML = `
        <h2>${report.name}</h2>
        <p>Generated: ${report.created_at}</p>
    `;
    
    const body = document.getElementById('report-viewer-body');
    body.innerHTML = renderMarkdown(report.content);
}

// FETCH METADATA TRACES
async function fetchTraces() {
    try {
        const res = await fetch('/api/traces');
        traces = await res.json();
        
        if (activeTab === 'traces') {
            renderTracesList();
        }
    } catch (err) {
        console.error('Error fetching traces:', err);
    }
}

function renderTracesList() {
    const listEl = document.getElementById('traces-list');
    listEl.innerHTML = '';
    
    if (traces.length === 0) {
        listEl.innerHTML = '<div class="viewer-placeholder"><p>No telemetry traces available</p></div>';
        return;
    }
    
    traces.forEach((trace, idx) => {
        const isRunReport = trace.name.startsWith('run_report');
        const badgeText = isRunReport ? 'Run Summary' : 'Telemetry Log';
        const badgeClass = isRunReport ? 'badge-in_stock' : 'badge-low_stock';
        
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerHTML = `
            <div class="list-item-title">${trace.name}</div>
            <div class="list-item-meta" style="display:flex; justify-content:space-between; align-items:center;">
                <span>Saved: ${trace.created_at}</span>
                <span class="badge-status ${badgeClass}" style="font-size:9px; padding:1px 5px;">${badgeText}</span>
            </div>
        `;
        item.onclick = () => selectTrace(trace, item);
        listEl.appendChild(item);
    });
}

function selectTrace(trace, itemEl) {
    document.querySelectorAll('#traces-list .list-item').forEach(el => el.classList.remove('selected'));
    itemEl.classList.add('selected');
    
    const header = document.getElementById('trace-viewer-header');
    header.innerHTML = `
        <h2>${trace.name}</h2>
        <p>Logged: ${trace.created_at}</p>
    `;
    
    const body = document.getElementById('trace-viewer-body');
    if (trace.name.endsWith('.md')) {
        body.innerHTML = renderMarkdown(trace.content);
    } else {
        body.innerHTML = `<pre><code>${escapeHtml(trace.content)}</code></pre>`;
    }
}

// ESCAPE HTML HELPER
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// CLIENT SIDE BASIC MARKDOWN CONVERTER (HTML ENVELOPE)
function renderMarkdown(text) {
    if (!text) return "";
    let html = text;
    
    // Escape standard tags first for viewer protection
    html = escapeHtml(html);
    
    // Headers
    html = html.replace(/^# (.*?)$/gm, "<h1>$1</h1>");
    html = html.replace(/^## (.*?)$/gm, "<h2>$1</h2>");
    html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");
    
    // Bold / Italic
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
    
    // Blockquotes
    html = html.replace(/^&gt; (.*?)$/gm, "<blockquote>$1</blockquote>");
    
    // Preformatted Code blocks (restore escaped tags inside code block only for formatting)
    html = html.replace(/```([\s\S]*?)```/g, function(match, p1) {
        return `<pre><code>${p1}</code></pre>`;
    });
    
    // Inline code
    html = html.replace(/`(.*?)`/g, "<code>$1</code>");
    
    // Bullet lists
    html = html.replace(/^\- (.*?)$/gm, "<li>$1</li>");
    
    // Format double spacing into paragraphs
    const paragraphs = html.split('\n\n').map(p => {
        const trimmed = p.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('<h') || trimmed.startsWith('<blockquote') || trimmed.startsWith('<pre') || trimmed.startsWith('<li>')) {
            return trimmed;
        }
        return `<p>${trimmed.replace(/\n/g, '<br>')}</p>`;
    });
    
    return paragraphs.join('\n');
}
