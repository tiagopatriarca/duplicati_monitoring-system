/* ==========================================================================
   SISTEMA DE MONITORAMENTO DE JOBS DUPLICATI - LÓGICA DE FRONTEND JS
   ========================================================================== */

let globalClientsCache = [];
let globalJobsCache = [];

document.addEventListener('DOMContentLoaded', () => {
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
async function loadDashboardData() {
    try {
        const res = await fetch('/api/dashboard-stats');
        if (!res.ok) {
            console.error("Erro na API /api/dashboard-stats:", res.status);
            return;
        }
        const data = await res.json();
        if (data.error) {
            console.error("Erro retornado do servidor:", data.error);
            return;
        }

        document.getElementById('stat-total-clients').textContent = data.stats.total_clients || 0;
        document.getElementById('stat-active-jobs').textContent = data.stats.active_jobs || 0;
        document.getElementById('stat-success-today').textContent = data.stats.success_today || 0;
        document.getElementById('stat-alerts-today').textContent = data.stats.alerts_today || 0;
        document.getElementById('stat-errors-today').textContent = data.stats.errors_today || 0;
        document.getElementById('stat-bytes-today').textContent = data.stats.bytes_today_formatted || '0 B';

        // Alertas de Jobs Não Executados / Falhas
        const alertSection = document.getElementById('missed-jobs-alert-section');
        const alertGrid = document.getElementById('missed-jobs-grid');

        if (alertSection && alertGrid && Array.isArray(data.missed_jobs) && data.missed_jobs.length > 0) {
            alertSection.style.display = 'block';
            alertGrid.innerHTML = data.missed_jobs.map(item => `
                <div class="missed-job-card">
                    <div style="font-weight: 700; font-size: 1.05rem; color: #ffffff;">🏢 ${escapeHtml(item.client_name)}</div>
                    <div style="font-size: 0.9rem; color: var(--accent-cyan); margin-top: 2px;">⚡ ${escapeHtml(item.job_name)}</div>
                    <div style="font-size: 0.82rem; color: #f87171; margin-top: 6px; font-weight: 600;">⚠️ ${escapeHtml(item.reason)}</div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">Última Execução: ${item.last_execution}</div>
                </div>
            `).join('');
        } else if (alertSection) {
            alertSection.style.display = 'none';
        }

        // Tabela Rápida dos Últimos Resultados
        const tbody = document.getElementById('recent-results-tbody');
        if (tbody) {
            const recent = Array.isArray(data.recent_results) ? data.recent_results : [];
            if (recent.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Nenhum resultado registrado até o momento.</td></tr>`;
            } else {
                tbody.innerHTML = recent.map(r => {
                    const d = r.details || {};
                    return `
                        <tr class="expandable-row" onclick="toggleHistoryDetail(${r.id})" style="cursor: pointer;" title="Clique para ver arquivos novos e modificados">
                            <td>
                                <span id="arrow-icon-${r.id}" style="display: inline-block; transition: transform 0.2s ease; margin-right: 6px; font-size: 0.75rem; color: var(--accent-blue);">▼</span>
                                <strong>${escapeHtml(r.client_name)}</strong>
                            </td>
                            <td>${escapeHtml(r.job_name)}</td>
                            <td>${r.execution_date}</td>
                            <td><span class="status-badge ${r.status}">${r.status}</span></td>
                            <td>${r.bytes_formatted}</td>
                            <td>${r.duration_formatted}</td>
                        </tr>
                        <tr id="detail-row-${r.id}" class="detail-row-expanded" style="display: none; background: rgba(15, 23, 42, 0.75);">
                            <td colspan="6" style="padding: 1rem 1.5rem;">
                                <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: center; font-size: 0.9rem;">
                                    <div style="background: rgba(6, 182, 212, 0.1); border: 1px solid rgba(6, 182, 212, 0.3); padding: 8px 14px; border-radius: var(--radius-sm);">
                                        <span style="color: var(--accent-cyan); font-weight: 600;">✨ Arquivos Novos:</span>
                                        <strong style="color: #ffffff; margin-left: 6px;">${d.added_count || 0} arquivos</strong>
                                        <span style="color: var(--text-secondary); font-size: 0.82rem; margin-left: 4px;">(${d.added_size || '0 B'})</span>
                                    </div>
                                    <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 8px 14px; border-radius: var(--radius-sm);">
                                        <span style="color: var(--status-warning); font-weight: 600;">✏️ Arquivos Modificados:</span>
                                        <strong style="color: #ffffff; margin-left: 6px;">${d.modified_count || 0} arquivos</strong>
                                        <span style="color: var(--text-secondary); font-size: 0.82rem; margin-left: 4px;">(${d.modified_size || '0 B'})</span>
                                    </div>
                                    <div style="background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border-color); padding: 8px 14px; border-radius: var(--radius-sm);">
                                        <span style="color: var(--text-secondary); font-weight: 500;">🔍 Total Examinado:</span>
                                        <strong style="color: #ffffff; margin-left: 6px;">${d.examined_count || 0} arquivos</strong>
                                        <span style="color: var(--text-secondary); font-size: 0.82rem; margin-left: 4px;">(${d.examined_size || '0 B'})</span>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (err) {
        console.error('Erro ao carregar dashboard:', err);
    }
}

// --- CLIENTS & JOBS PAGE ---
async function loadUsersAndGroupsData() {
    try {
        const [resUsers, resGroups] = await Promise.all([
            fetch('/api/users'),
            fetch('/api/groups')
        ]);

        const rawUsers = await resUsers.json();
        const rawGroups = await resGroups.json();

        const users = Array.isArray(rawUsers) ? rawUsers : [];
        const groups = Array.isArray(rawGroups) ? rawGroups : [];

        renderUsersTable(users);
        renderGroupsTable(groups);
    } catch (e) {
        console.error('Erro ao carregar usuários e grupos:', e);
    }
}

async function loadClientsPageData() {
    try {
        const [resClients, resJobs] = await Promise.all([
            fetch('/api/clients'),
            fetch('/api/jobs')
        ]);
                clientsTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted);">Nenhum cliente cadastrado.</td></tr>`;
            } else {
                clientsTbody.innerHTML = globalClientsCache.map(c => `
                    <tr>
                        <td><strong>${escapeHtml(c.name)}</strong></td>
                        <td>${escapeHtml(c.email || '-')}</td>
                        <td>${escapeHtml(c.contact_phone || '-')}</td>
                        <td><span class="status-badge Success">${c.job_count} job(s)</span></td>
                        <td>
                            <div style="display: flex; gap: 6px;">
                                <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="editClient(${c.id})">✏️ Editar</button>
                                <button class="btn btn-danger" style="padding: 4px 10px; font-size: 0.8rem;" onclick="deleteClient(${c.id})">🗑️ Excluir</button>
                            </div>
                        </td>
                    </tr>
                `).join('');
            }
        }

        // Preencher Select no Modal de Jobs
        const clientSelect = document.getElementById('job-client-id');
        if (clientSelect) {
            clientSelect.innerHTML = globalClientsCache.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
        }

        // Tabela de Jobs com URL Única de Webhook
        const jobsTbody = document.getElementById('jobs-tbody');
        if (jobsTbody) {
            if (globalJobsCache.length === 0) {
                jobsTbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Nenhum job agendado.</td></tr>`;
            } else {
                const currentOrigin = window.location.origin;
                jobsTbody.innerHTML = globalJobsCache.map(j => {
                    const webhookUrl = `${currentOrigin}/api/webhook/job/${j.webhook_token}`;
                    return `
                    <tr>
                        <td><strong>${escapeHtml(j.client_name)}</strong></td>
                        <td>${escapeHtml(j.job_name)}</td>
                        <td>${j.frequency_per_day}x ao dia</td>
                        <td>${j.days_of_week}</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 6px; background: rgba(15,23,42,0.6); padding: 4px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
                                <code style="font-size: 0.75rem; color: #38bdf8; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${webhookUrl}</code>
                                <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.75rem;" onclick="copyWebhookUrl('${webhookUrl}')">📋 Copiar</button>
                            </div>
                        </td>
                        <td>
                            <div style="display: flex; gap: 6px;">
                                <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="editJob(${j.id})">✏️ Editar</button>
                                <button class="btn btn-danger" style="padding: 4px 10px; font-size: 0.8rem;" onclick="deleteJob(${j.id})">🗑️ Excluir</button>
                            </div>
                        </td>
                    </tr>
                `;
                }).join('');
            }
        }
    } catch (err) {
        console.error('Erro ao carregar clientes/jobs:', err);
    }
}

// Modal & Ações de Cliente
function openNewClientModal() {
    document.getElementById('modal-client-title').textContent = 'Novo Cliente';
    document.getElementById('client-id-edit').value = '';
    document.getElementById('form-client').reset();
    openModal('modal-client');
}

function editClient(id) {
    const client = globalClientsCache.find(c => c.id === id);
    if (!client) return;

    document.getElementById('modal-client-title').textContent = 'Editar Cliente';
    document.getElementById('client-id-edit').value = client.id;
    document.getElementById('client-name').value = client.name;
    document.getElementById('client-email').value = client.email;
    document.getElementById('client-phone').value = client.contact_phone;
    document.getElementById('client-notes').value = client.notes;

    openModal('modal-client');
}

async function saveClient(event) {
    event.preventDefault();
    const id = document.getElementById('client-id-edit').value;
    const name = document.getElementById('client-name').value;
    const email = document.getElementById('client-email').value;
    const contact_phone = document.getElementById('client-phone').value;
    const notes = document.getElementById('client-notes').value;

    const url = id ? `/api/clients/${id}` : '/api/clients';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, contact_phone, notes })
        });
        const data = await res.json();

        if (res.ok) {
            closeModal('modal-client');
            loadClientsPageData();
        } else {
            alert(data.error || 'Erro ao salvar cliente');
        }
    } catch (err) {
        alert('Erro ao se comunicar com o servidor: ' + err.message);
    }
}

// Modal & Ações de Job
function openNewJobModal() {
    document.getElementById('modal-job-title').textContent = 'Configurar Novo Job';
    document.getElementById('job-id-edit').value = '';
    document.getElementById('form-job').reset();
    openModal('modal-job');
}

function editJob(id) {
    const job = globalJobsCache.find(j => j.id === id);
    if (!job) return;

    document.getElementById('modal-job-title').textContent = 'Editar Job';
    document.getElementById('job-id-edit').value = job.id;
    document.getElementById('job-client-id').value = job.client_id;
    document.getElementById('job-name').value = job.job_name;
    document.getElementById('job-freq').value = job.frequency_per_day;
    document.getElementById('job-time').value = job.expected_time || '22:00';

    const configuredDays = (job.days_of_week || '').split(',');
    document.querySelectorAll('input[name="days"]').forEach(cb => {
        cb.checked = configuredDays.includes(cb.value);
    });

    openModal('modal-job');
}

async function saveJob(event) {
    event.preventDefault();
    const id = document.getElementById('job-id-edit').value;
    const client_id = document.getElementById('job-client-id').value;
    const job_name = document.getElementById('job-name').value;
    const frequency_per_day = document.getElementById('job-freq').value;
    const expected_time = document.getElementById('job-time').value;

    const checkboxes = document.querySelectorAll('input[name="days"]:checked');
    const days_of_week = Array.from(checkboxes).map(cb => cb.value);

    const url = id ? `/api/jobs/${id}` : '/api/jobs';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_id, job_name, frequency_per_day, expected_time, days_of_week })
        });
        const data = await res.json();

        if (res.ok) {
            closeModal('modal-job');
            loadClientsPageData();
        } else {
            alert(data.error || 'Erro ao salvar job');
        }
    } catch (err) {
        alert('Erro ao se comunicar com o servidor: ' + err.message);
    }
}

async function deleteClient(id) {
    if (confirm('Deseja realmente excluir este cliente e todos os seus jobs?')) {
        try {
            const res = await fetch(`/api/clients/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                loadClientsPageData();
            } else {
                alert(data.error || 'Erro ao excluir cliente');
            }
        } catch (err) {
            alert('Erro de rede ao excluir cliente');
        }
    }
}

async function deleteJob(id) {
    if (confirm('Deseja realmente excluir este job?')) {
        try {
            const res = await fetch(`/api/jobs/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                loadClientsPageData();
            } else {
                alert(data.error || 'Erro ao excluir job');
            }
        } catch (err) {
            alert('Erro de rede ao excluir job');
        }
    }
}

// PERFIL DO USUÁRIO
function openProfileModal() {
    openModal('modal-profile');
}

async function updateProfile(event) {
    event.preventDefault();
    const email = document.getElementById('profile-email').value;
    const password = document.getElementById('profile-password').value;

    try {
        const res = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (res.ok) {
            alert('Perfil atualizado com sucesso!');
            closeModal('modal-profile');
            document.getElementById('profile-password').value = '';
        } else {
            alert(data.error || 'Erro ao atualizar perfil');
        }
    } catch (err) {
        alert('Erro de comunicação: ' + err.message);
    }
}

// HELPER COPIAR URL DO WEBHOOK (Compatível com HTTP e HTTPS)
function copyWebhookUrl(url) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(url).then(() => {
            alert('URL de Webhook copiada com sucesso!\n\nCole no Duplicati na opção:\n--send-http-url=' + url);
        }).catch(() => {
            fallbackCopyText(url);
        });
    } else {
        fallbackCopyText(url);
    }
}

function fallbackCopyText(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            alert('URL de Webhook copiada com sucesso!\n\nCole no Duplicati na opção:\n--send-http-url=' + text);
        } else {
            prompt('Copie a URL abaixo para colocar no Duplicati:', text);
        }
    } catch (err) {
        prompt('Copie a URL abaixo para colocar no Duplicati:', text);
    } finally {
        document.body.removeChild(textArea);
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
                tbody.innerHTML = data.map(r => {
                    const d = r.details || {};
                    return `
                        <tr class="expandable-row" onclick="toggleHistoryDetail(${r.id})" style="cursor: pointer;" title="Clique para expandir arquivos novos e modificados">
                            <td>
                                <span id="arrow-icon-${r.id}" style="display: inline-block; transition: transform 0.2s ease; margin-right: 6px; font-size: 0.75rem; color: var(--accent-blue);">▼</span>
                                #${r.id}
                            </td>
                            <td><strong>${escapeHtml(r.client_name)}</strong></td>
                            <td>${escapeHtml(r.job_name)}</td>
                            <td>${r.execution_date}</td>
                            <td><span class="status-badge ${r.status}">${r.status}</span></td>
                            <td>${r.bytes_formatted}</td>
                            <td>${r.duration_formatted}</td>
                        </tr>
                        <tr id="detail-row-${r.id}" class="detail-row-expanded" style="display: none; background: rgba(15, 23, 42, 0.75);">
                            <td colspan="7" style="padding: 1.2rem 1.5rem; border-bottom: 2px solid var(--accent-blue);">
                                <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: center; font-size: 0.9rem;">
                                    <div style="background: rgba(6, 182, 212, 0.1); border: 1px solid rgba(6, 182, 212, 0.35); padding: 10px 16px; border-radius: var(--radius-sm);">
                                        <span style="color: var(--accent-cyan); font-weight: 600;">✨ Arquivos Novos:</span>
                                        <strong style="color: #ffffff; margin-left: 6px; font-size: 1rem;">${d.added_count || 0} arquivos</strong>
                                        <span style="color: var(--text-secondary); font-size: 0.85rem; margin-left: 6px;">(${d.added_size || '0 B'})</span>
                                    </div>
                                    <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.35); padding: 10px 16px; border-radius: var(--radius-sm);">
                                        <span style="color: var(--status-warning); font-weight: 600;">✏️ Arquivos Modificados:</span>
                                        <strong style="color: #ffffff; margin-left: 6px; font-size: 1rem;">${d.modified_count || 0} arquivos</strong>
                                        <span style="color: var(--text-secondary); font-size: 0.85rem; margin-left: 6px;">(${d.modified_size || '0 B'})</span>
                                    </div>
                                    <div style="background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border-color); padding: 10px 16px; border-radius: var(--radius-sm);">
                                        <span style="color: var(--text-secondary); font-weight: 500;">🔍 Total Examinado:</span>
                                        <strong style="color: #ffffff; margin-left: 6px; font-size: 1rem;">${d.examined_count || 0} arquivos</strong>
                                        <span style="color: var(--text-secondary); font-size: 0.85rem; margin-left: 6px;">(${d.examined_size || '0 B'})</span>
                                    </div>
                                </div>
                                ${r.log_summary ? `<div style="margin-top: 10px; font-size: 0.85rem; color: var(--text-secondary); border-top: 1px dashed var(--border-color); padding-top: 8px;"><strong>Resumo do Log:</strong> ${escapeHtml(r.log_summary)}</div>` : ''}
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (err) {
        console.error('Erro ao carregar histórico:', err);
    }
}

function toggleHistoryDetail(id) {
    const detailRow = document.getElementById(`detail-row-${id}`);
    const arrowIcon = document.getElementById(`arrow-icon-${id}`);
    if (!detailRow) return;

    if (detailRow.style.display === 'none' || !detailRow.style.display) {
        detailRow.style.display = 'table-row';
        if (arrowIcon) arrowIcon.style.transform = 'rotate(180deg)';
    } else {
        detailRow.style.display = 'none';
        if (arrowIcon) arrowIcon.style.transform = 'rotate(0deg)';
    }
}

// --- REPORTS PAGE ---
async function initReportsPage() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);

    const startInput = document.getElementById('report-start');
    const endInput = document.getElementById('report-end');

    if (startInput && !startInput.value) startInput.value = formatDateYMD(thirtyDaysAgo);
    if (endInput && !endInput.value) endInput.value = formatDateYMD(today);

    // Carregar opções de empresas no filtro do relatório
    try {
        const res = await fetch('/api/clients');
        const clients = await res.json();
        const clientSelect = document.getElementById('report-client');
        if (clientSelect) {
            clientSelect.innerHTML = `<option value="">Todas as Empresas</option>` +
                clients.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
        }
    } catch (e) {
        console.error('Erro ao carregar lista de clientes no relatório:', e);
    }

    loadReportsData();
}

async function loadReportsData() {
    const start_date = document.getElementById('report-start').value;
    const end_date = document.getElementById('report-end').value;
    const client_id = document.getElementById('report-client')?.value || '';

    try {
        const res = await fetch(`/api/reports?start_date=${start_date}&end_date=${end_date}&client_id=${client_id}`);
        const data = await res.json();

        document.getElementById('rep-executions').textContent = data.summary.total_executions;
        document.getElementById('rep-success-rate').textContent = `${data.summary.success_rate}%`;
        document.getElementById('rep-bytes').textContent = data.summary.total_bytes_formatted;
        document.getElementById('rep-duration').textContent = data.summary.avg_duration_formatted;

        // Atualizar Título e Período Exclusivo para Impressão
        const printTitle = document.getElementById('print-report-title');
        const printSub = document.getElementById('print-report-subtitle');
        if (printTitle) {
            printTitle.textContent = `Relatório de Backup - ${data.client_name}`;
        }
        if (printSub) {
            printSub.textContent = `Período Selecionado: ${formatDateBR(start_date)} a ${formatDateBR(end_date)}`;
        }

        const tbody = document.getElementById('reports-tbody');
        if (tbody) {
            if (data.records.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Nenhum registro no período.</td></tr>`;
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
    const client_id = document.getElementById('report-client')?.value || '';
    window.location.href = `/api/reports/export?start_date=${start_date}&end_date=${end_date}&client_id=${client_id}`;
}

function formatDateBR(ymd) {
    if (!ymd) return '';
    const parts = ymd.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return ymd;
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
