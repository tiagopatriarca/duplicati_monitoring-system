/* ==========================================================================
   SISTEMA DE MONITORAMENTO DE JOBS DUPLICATI - LÓGICA DE FRONTEND JS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Inicializações com base na página atual
    const path = window.location.pathname;

    if (path === '/' || path === '/index.html') {
        loadDashboardData();
    } else if (path === '/clients') {
        loadClientsPageData();
    } else if (path === '/history') {
        loadHistoryData();
    } else if (path === '/reports') {
        initReportsPage();
    }
});

// --- DASHBOARD FUNCTIONS ---
async function loadDashboardData(selectedDate = null) {
    try {
        let url = '/api/dashboard-stats';
        if (selectedDate) url += `?date=${selectedDate}`;

        const res = await fetch(url);
        const data = await res.json();

        // Atualizar Cards Métricos
        document.getElementById('stat-clients').textContent = data.total_clients;
        document.getElementById('stat-jobs').textContent = data.total_jobs;
        document.getElementById('stat-success').textContent = data.success_today;
        document.getElementById('stat-warning').textContent = data.warning_today;
        document.getElementById('stat-error').textContent = data.error_today;
        document.getElementById('stat-bytes').textContent = data.total_bytes_today_formatted;

        // Renderizar Banner & Cards de Jobs Pendentes / Não Executados
        const alertSection = document.getElementById('missed-jobs-section');
        const alertGrid = document.getElementById('missed-jobs-grid');

        if (data.missed_count > 0) {
            alertSection.style.display = 'block';
            document.getElementById('missed-alert-count').textContent = data.missed_count;

            alertGrid.innerHTML = data.missed_jobs.map(job => `
                <div class="missed-job-card">
                    <div class="missed-job-info">
                        <div class="missed-job-client">${escapeHtml(job.client_name)}</div>
                        <h4>${escapeHtml(job.job_name)}</h4>
                    </div>
                    <div class="missed-details">
                        <span class="detail-pill">🗓 ${job.day_of_week}</span>
                        <span class="detail-pill">⏱ Freq: ${job.frequency_per_day}x/dia</span>
                        <span class="detail-pill">⚠️ Encontradas: ${job.executions_found}</span>
                    </div>
                    <div class="badge-investigate">🚨 INVESTIGAR - ${job.status_alert}</div>
                </div>
            `).join('');
        } else {
            alertSection.style.display = 'none';
            alertGrid.innerHTML = '';
        }

        // Tabela Rápida dos Últimos Resultados
        const tbody = document.getElementById('recent-results-tbody');
        if (tbody) {
            if (data.recent_results.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Nenhum resultado registrado até o momento.</td></tr>`;
            } else {
                tbody.innerHTML = data.recent_results.map(r => `
                    <tr>
                        <td><strong>${escapeHtml(r.client_name)}</strong></td>
                        <td>${escapeHtml(r.job_name)}</td>
                        <td>${r.execution_date}</td>
                        <td><span class="status-badge ${r.status}">${r.status}</span></td>
                        <td>${r.bytes_formatted}</td>
                        <td>${r.duration_formatted}</td>
                    </tr>
                `).join('');
            }
        }

    } catch (err) {
        console.error('Erro ao carregar dados do dashboard:', err);
    }
}

// --- CLIENTS & JOBS MANAGEMENT ---
async function loadClientsPageData() {
    try {
        const [resClients, resJobs] = await Promise.all([
            fetch('/api/clients'),
            fetch('/api/jobs')
        ]);
        const clients = await resClients.json();
        const jobs = await resJobs.json();

        // Preencher Tabela de Clientes
        const clientsTbody = document.getElementById('clients-tbody');
        if (clientsTbody) {
            if (clients.length === 0) {
                clientsTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted);">Nenhum cliente cadastrado.</td></tr>`;
            } else {
                clientsTbody.innerHTML = clients.map(c => `
                    <tr>
                        <td><strong>${escapeHtml(c.name)}</strong></td>
                        <td>${escapeHtml(c.email || '-')}</td>
                        <td>${escapeHtml(c.contact_phone || '-')}</td>
                        <td><span class="status-badge Success">${c.job_count} job(s)</span></td>
                        <td>
                            <button class="btn btn-danger" style="padding: 4px 10px; font-size: 0.8rem;" onclick="deleteClient(${c.id})">Excluir</button>
                        </td>
                    </tr>
                `).join('');
            }
        }

        // Preencher Select de Clientes no Modal de Job
        const clientSelect = document.getElementById('job-client-id');
        if (clientSelect) {
            clientSelect.innerHTML = clients.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
        }

        // Preencher Tabela de Jobs
        const jobsTbody = document.getElementById('jobs-tbody');
        if (jobsTbody) {
            if (jobs.length === 0) {
                jobsTbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Nenhum job agendado.</td></tr>`;
            } else {
                jobsTbody.innerHTML = jobs.map(j => `
                    <tr>
                        <td><strong>${escapeHtml(j.client_name)}</strong></td>
                        <td>${escapeHtml(j.job_name)}</td>
                        <td>${j.frequency_per_day}x ao dia</td>
                        <td>${j.days_of_week}</td>
                        <td>${j.expected_time || '-'}</td>
                        <td>
                            <button class="btn btn-danger" style="padding: 4px 10px; font-size: 0.8rem;" onclick="deleteJob(${j.id})">Excluir</button>
                        </td>
                    </tr>
                `).join('');
            }
        }

    } catch (err) {
        console.error('Erro ao carregar clientes/jobs:', err);
    }
}

async function createClient(event) {
    event.preventDefault();
    const name = document.getElementById('client-name').value;
    const email = document.getElementById('client-email').value;
    const contact_phone = document.getElementById('client-phone').value;
    const notes = document.getElementById('client-notes').value;

    const res = await fetch('/api/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, contact_phone, notes })
    });

    if (res.ok) {
        closeModal('modal-client');
        document.getElementById('form-client').reset();
        loadClientsPageData();
    } else {
        alert('Erro ao cadastrar cliente');
    }
}

async function createJob(event) {
    event.preventDefault();
    const client_id = document.getElementById('job-client-id').value;
    const job_name = document.getElementById('job-name').value;
    const frequency_per_day = document.getElementById('job-freq').value;
    const expected_time = document.getElementById('job-time').value;

    // Obter dias selecionados
    const checkboxes = document.querySelectorAll('input[name="days"]:checked');
    const days_of_week = Array.from(checkboxes).map(cb => cb.value);

    const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id, job_name, frequency_per_day, expected_time, days_of_week })
    });

    if (res.ok) {
        closeModal('modal-job');
        document.getElementById('form-job').reset();
        loadClientsPageData();
    } else {
        alert('Erro ao cadastrar job');
    }
}

async function deleteClient(id) {
    if (confirm('Deseja realmente excluir este cliente e todos os seus jobs?')) {
        await fetch(`/api/clients/${id}`, { method: 'DELETE' });
        loadClientsPageData();
    }
}

async function deleteJob(id) {
    if (confirm('Deseja realmente excluir este job?')) {
        await fetch(`/api/jobs/${id}`, { method: 'DELETE' });
        loadClientsPageData();
    }
}

// --- HISTORY PAGE ---
async function loadHistoryData() {
    try {
        const client_id = document.getElementById('filter-client')?.value || '';
        const status = document.getElementById('filter-status')?.value || '';
        const start_date = document.getElementById('filter-start')?.value || '';
        const end_date = document.getElementById('filter-end')?.value || '';

        let url = `/api/history?client_id=${client_id}&status=${status}&start_date=${start_date}&end_date=${end_date}`;
        const res = await fetch(url);
        const data = await res.json();

        const tbody = document.getElementById('history-tbody');
        if (tbody) {
            if (data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">Nenhum histórico encontrado para os filtros selecionados.</td></tr>`;
            } else {
                tbody.innerHTML = data.map(r => `
                    <tr>
                        <td>#${r.id}</td>
                        <td><strong>${escapeHtml(r.client_name)}</strong></td>
                        <td>${escapeHtml(r.job_name)}</td>
                        <td>${r.execution_date}</td>
                        <td><span class="status-badge ${r.status}">${r.status}</span></td>
                        <td>${r.bytes_formatted}</td>
                        <td>${r.duration_formatted}</td>
                    </tr>
                `).join('');
            }
        }
    } catch (err) {
        console.error('Erro ao carregar histórico:', err);
    }
}

// --- REPORTS PAGE ---
function initReportsPage() {
    // Definir padrão para os últimos 30 dias
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);

    const startInput = document.getElementById('report-start');
    const endInput = document.getElementById('report-end');

    if (startInput && !startInput.value) startInput.value = formatDateYMD(thirtyDaysAgo);
    if (endInput && !endInput.value) endInput.value = formatDateYMD(today);

    loadReportsData();
}

async function loadReportsData() {
    const start_date = document.getElementById('report-start').value;
    const end_date = document.getElementById('report-end').value;

    try {
        const res = await fetch(`/api/reports?start_date=${start_date}&end_date=${end_date}`);
        const data = await res.json();

        document.getElementById('rep-executions').textContent = data.summary.total_executions;
        document.getElementById('rep-success-rate').textContent = `${data.summary.success_rate}%`;
        document.getElementById('rep-bytes').textContent = data.summary.total_bytes_formatted;
        document.getElementById('rep-duration').textContent = data.summary.total_duration_formatted;

        const tbody = document.getElementById('reports-tbody');
        if (tbody) {
            if (data.records.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Nenhum registro encontrado no período selecionado.</td></tr>`;
            } else {
                tbody.innerHTML = data.records.map(r => `
                    <tr>
                        <td><strong>${escapeHtml(r.client_name)}</strong></td>
                        <td>${escapeHtml(r.job_name)}</td>
                        <td>${r.execution_date}</td>
                        <td><span class="status-badge ${r.status}">${r.status}</span></td>
                        <td>${r.bytes_formatted}</td>
                        <td>${r.duration_formatted}</td>
                    </tr>
                `).join('');
            }
        }
    } catch (err) {
        console.error('Erro ao carregar relatório:', err);
    }
}

function exportReportCSV() {
    const start_date = document.getElementById('report-start').value;
    const end_date = document.getElementById('report-end').value;
    window.location.href = `/api/reports/export?start_date=${start_date}&end_date=${end_date}`;
}

// --- UTILS & MODALS ---
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function formatDateYMD(d) {
    return d.toISOString().split('T')[0];
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m];
    });
}
