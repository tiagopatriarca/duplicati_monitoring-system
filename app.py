import json
import csv
import io
import uuid
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config import Config
from database import db, Client, Job, JobResult, User, Group, group_clients, generate_webhook_token
from utils import check_missed_jobs, format_bytes, format_duration

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar Banco de Dados
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- INICIALIZAÇÃO DO BANCO E MIGRAÇÕES AUTOMÁTICAS ---

def init_db_with_fallback():
    """
    Tenta conectar ao MySQL com retentativas para aguardar o banco estar pronto.
    Garante que os dados cadastrados no MySQL sejam carregados corretamente.
    """
    import time
    max_retries = 10
    connected = False
    
    for i in range(max_retries):
        try:
            db.create_all()
            db.session.execute(text("SELECT 1"))
            print("Conectado ao Banco de Dados MySQL com sucesso!")
            connected = True
            break
        except Exception as e:
            print(f"Tentativa {i+1}/{max_retries} de conexão com MySQL ({e}). Aguardando 2s...")
            time.sleep(2)

    if not connected and app.config.get('USE_SQLITE_FALLBACK'):
        print("Ativando banco de dados local de fallback SQLite (duplicati_local.db)...")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///duplicati_local.db'
        db.init_app(app)
        db.create_all()

    try:
        seed_initial_data()
        # Garantir permissão total para o grupo Administradores (usando crases para o MySQL 8.0)
        with db.engine.connect() as conn:
            conn.execute(text("UPDATE `groups` SET can_view_all_clients = 1 WHERE id = 1 OR name = 'Administradores'"))
            conn.execute(text("UPDATE `users` SET group_id = 1 WHERE username = 'admin'"))
            conn.commit()
    except Exception as e:
        print(f"Aviso na verificação de dados: {e}")

def seed_initial_data():
    admin_group = Group.query.filter_by(name="Administradores").first()
    if not admin_group:
        admin_group = Group(
            name="Administradores",
            description="Acesso total a todos os clientes",
            can_manage_users=True,
            can_manage_clients=True,
            can_view_all_clients=True
        )
        db.session.add(admin_group)
        db.session.commit()

    admin_user = User.query.filter_by(username="admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@duplicatishield.com",
            group_id=admin_group.id,
            active=True
        )
        admin_user.set_password("duplicati")
        db.session.add(admin_user)
        db.session.commit()

with app.app_context():
    init_db_with_fallback()

# --- ROTAS DE AUTENTICAÇÃO E PERFIL ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.active:
                error = "Sua conta está desativada. Fale com o administrador."
            else:
                login_user(user)
                return redirect(url_for('index'))
        else:
            error = "Usuário ou senha incorretos."

    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/profile', methods=['PUT'])
@login_required
def api_update_profile():
    try:
        data = request.json or {}
        email = data.get('email')
        password = data.get('password')

        if email:
            current_user.email = email
        
        if password and len(password.strip()) > 0:
            if len(password.strip()) < 6:
                return jsonify({'error': 'A nova senha deve ter no mínimo 6 caracteres'}), 400
            current_user.set_password(password.strip())

        db.session.commit()
        return jsonify({'success': True, 'message': 'Perfil atualizado com sucesso!', 'user': current_user.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao atualizar perfil: {str(e)}'}), 500

# --- ROTAS DE PÁGINAS ---

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/clients')
@login_required
def clients_page():
    return render_template('clients.html')

@app.route('/history')
@login_required
def history_page():
    return render_template('history.html')

@app.route('/reports')
@login_required
def reports_page():
    return render_template('reports.html')

@app.route('/users')
@login_required
def users_page():
    if current_user.group and not current_user.group.can_manage_users:
        flash("Você não tem permissão para gerenciar usuários.")
        return redirect(url_for('index'))
    return render_template('users.html')

@app.route('/webhook-guide')
@login_required
def webhook_guide_page():
    return render_template('webhook_guide.html')

# --- ROTAS DE API DA APLICAÇÃO ---

@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    target_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = date.today()

    try:
        allowed_ids = current_user.get_allowed_client_ids()

        client_query = Client.query
        job_query = Job.query.filter_by(active=True)
        result_query = JobResult.query.join(Job)

        if allowed_ids is not None:
            client_query = client_query.filter(Client.id.in_(allowed_ids))
            job_query = job_query.filter(Job.client_id.in_(allowed_ids))
            result_query = result_query.filter(Job.client_id.in_(allowed_ids))

        total_clients = client_query.count()
        total_jobs = job_query.count()

        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        
        results_today = result_query.filter(
            JobResult.execution_date >= start_dt,
            JobResult.execution_date <= end_dt
        ).all()

        success_today = sum(1 for r in results_today if r.status == 'Success')
        warning_today = sum(1 for r in results_today if r.status == 'Warning')
        error_today = sum(1 for r in results_today if r.status in ('Error', 'Fatal'))
        total_bytes_today = sum(r.bytes_copied for r in results_today)

        missed_jobs = check_missed_jobs(target_date, allowed_client_ids=allowed_ids)
        recent_results = result_query.order_by(JobResult.execution_date.desc()).limit(10).all()

        return jsonify({
            'date': target_date.strftime('%Y-%m-%d'),
            'total_clients': total_clients,
            'total_jobs': total_jobs,
            'success_today': success_today,
            'warning_today': warning_today,
            'error_today': error_today,
            'missed_count': len(missed_jobs),
            'total_bytes_today_formatted': format_bytes(total_bytes_today),
            'missed_jobs': missed_jobs,
            'recent_results': [r.to_dict() for r in recent_results]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao obter dados do dashboard: {str(e)}'}), 500

@app.route('/api/clients', methods=['GET', 'POST'])
@login_required
def api_clients():
    allowed_ids = current_user.get_allowed_client_ids()

    if request.method == 'GET':
        try:
            query = Client.query
            if allowed_ids is not None:
                query = query.filter(Client.id.in_(allowed_ids))
            clients = query.order_by(Client.name).all()
            return jsonify([c.to_dict() for c in clients])
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao listar clientes: {str(e)}'}), 500

    if request.method == 'POST':
        try:
            data = request.json or {}
            name = data.get('name')
            if not name:
                return jsonify({'error': 'Nome do cliente é obrigatório'}), 400

            client = Client(
                name=name,
                email=data.get('email'),
                contact_phone=data.get('contact_phone'),
                notes=data.get('notes')
            )
            db.session.add(client)
            db.session.commit()
            return jsonify(client.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao salvar cliente: {str(e)}'}), 500

@app.route('/api/clients/<int:client_id>', methods=['PUT', 'DELETE'])
@login_required
def api_client_detail(client_id):
    client = Client.query.get_or_404(client_id)

    if request.method == 'PUT':
        try:
            data = request.json or {}
            name = data.get('name')
            if not name:
                return jsonify({'error': 'Nome do cliente é obrigatório'}), 400

            client.name = name
            client.email = data.get('email')
            client.contact_phone = data.get('contact_phone')
            client.notes = data.get('notes')

            db.session.commit()
            return jsonify(client.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao editar cliente: {str(e)}'}), 500

    if request.method == 'DELETE':
        try:
            db.session.delete(client)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Cliente removido com sucesso'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao excluir cliente: {str(e)}'}), 500

@app.route('/api/jobs', methods=['GET', 'POST'])
@login_required
def api_jobs():
    allowed_ids = current_user.get_allowed_client_ids()

    if request.method == 'GET':
        try:
            query = Job.query.join(Client)
            if allowed_ids is not None:
                query = query.filter(Job.client_id.in_(allowed_ids))
            jobs = query.order_by(Job.job_name).all()
            return jsonify([j.to_dict() for j in jobs])
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao listar jobs: {str(e)}'}), 500

    if request.method == 'POST':
        try:
            data = request.json or {}
            client_id = data.get('client_id')
            job_name = data.get('job_name')
            
            if not client_id or not job_name:
                return jsonify({'error': 'Cliente e Nome do Job são obrigatórios'}), 400

            days_list = data.get('days_of_week', ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'])
            days_str = ','.join(days_list) if isinstance(days_list, list) else str(days_list)

            job = Job(
                client_id=int(client_id),
                job_name=job_name,
                webhook_token=generate_webhook_token(),
                frequency_per_day=int(data.get('frequency_per_day', 1)),
                days_of_week=days_str,
                expected_time=data.get('expected_time', '22:00'),
                active=data.get('active', True)
            )
            db.session.add(job)
            db.session.commit()
            return jsonify(job.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao salvar job: {str(e)}'}), 500

@app.route('/api/jobs/<int:job_id>', methods=['PUT', 'DELETE'])
@login_required
def api_job_detail(job_id):
    job = Job.query.get_or_404(job_id)

    if request.method == 'PUT':
        try:
            data = request.json or {}
            job_name = data.get('job_name')
            client_id = data.get('client_id')
            if not job_name or not client_id:
                return jsonify({'error': 'Nome do job e cliente são obrigatórios'}), 400

            days_list = data.get('days_of_week', ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'])
            days_str = ','.join(days_list) if isinstance(days_list, list) else str(days_list)

            job.client_id = int(client_id)
            job.job_name = job_name
            job.frequency_per_day = int(data.get('frequency_per_day', 1))
            job.days_of_week = days_str
            job.expected_time = data.get('expected_time', '22:00')

            db.session.commit()
            return jsonify(job.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao editar job: {str(e)}'}), 500

    if request.method == 'DELETE':
        try:
            db.session.delete(job)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Job removido com sucesso'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erro ao excluir job: {str(e)}'}), 500

@app.route('/api/history')
@login_required
def api_history():
    allowed_ids = current_user.get_allowed_client_ids()
    query = JobResult.query.join(Job).join(Client)

    if allowed_ids is not None:
        query = query.filter(Job.client_id.in_(allowed_ids))

    client_id = request.args.get('client_id')
    if client_id:
        query = query.filter(Job.client_id == client_id)

    status = request.args.get('status')
    if status:
        query = query.filter(JobResult.status == status)

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date:
        query = query.filter(JobResult.execution_date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(JobResult.execution_date < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

    results = query.order_by(JobResult.execution_date.desc()).all()
    return jsonify([r.to_dict() for r in results])

@app.route('/api/reports')
@login_required
def api_reports():
    allowed_ids = current_user.get_allowed_client_ids()
    start_date_str = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    client_id = request.args.get('client_id')

    dt_start = datetime.strptime(start_date_str, '%Y-%m-%d')
    dt_end = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

    query = JobResult.query.join(Job).filter(
        JobResult.execution_date >= dt_start,
        JobResult.execution_date < dt_end
    )

    if allowed_ids is not None:
        query = query.filter(Job.client_id.in_(allowed_ids))
    if client_id:
        query = query.filter(Job.client_id == client_id)

    results = query.order_by(JobResult.execution_date.desc()).all()

    total_executions = len(results)
    success_count = sum(1 for r in results if r.status == 'Success')
    warning_count = sum(1 for r in results if r.status == 'Warning')
    error_count = sum(1 for r in results if r.status in ('Error', 'Fatal'))
    total_bytes = sum(r.bytes_copied for r in results)
    total_seconds = sum(r.duration_seconds for r in results)

    success_rate = round((success_count / total_executions * 100), 1) if total_executions > 0 else 0.0
    avg_seconds = round(total_seconds / total_executions) if total_executions > 0 else 0

    client_name = "Todas as Empresas"
    if client_id:
        c = Client.query.get(client_id)
        if c:
            client_name = c.name

    return jsonify({
        'period': {'start': start_date_str, 'end': end_date_str},
        'client_name': client_name,
        'summary': {
            'total_executions': total_executions,
            'success_count': success_count,
            'warning_count': warning_count,
            'error_count': error_count,
            'success_rate': success_rate,
            'total_bytes_formatted': format_bytes(total_bytes),
            'avg_duration_formatted': format_duration(avg_seconds)
        },
        'records': [r.to_dict() for r in results]
    })

@app.route('/api/reports/export')
@login_required
def api_reports_export_csv():
    allowed_ids = current_user.get_allowed_client_ids()
    start_date_str = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    client_id = request.args.get('client_id')

    dt_start = datetime.strptime(start_date_str, '%Y-%m-%d')
    dt_end = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

    query = JobResult.query.join(Job).filter(
        JobResult.execution_date >= dt_start,
        JobResult.execution_date < dt_end
    )

    if allowed_ids is not None:
        query = query.filter(Job.client_id.in_(allowed_ids))
    if client_id:
        query = query.filter(Job.client_id == client_id)

    results = query.order_by(JobResult.execution_date.desc()).all()

    output = io.StringIO()
    # Escore UTF-8 BOM para garantir suporte a acentos no Excel
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Cliente', 'Nome do Job', 'Data Execucao', 'Status', 'Tamanho Copiado (Bytes)', 'Tamanho Formatado', 'Duracao (Segundos)', 'Duracao Formatada', 'Resumo Log'])

    for r in results:
        dict_r = r.to_dict()
        writer.writerow([
            dict_r['id'],
            dict_r['client_name'],
            dict_r['job_name'],
            dict_r['execution_date'],
            dict_r['status'],
            dict_r['bytes_copied'],
            dict_r['bytes_formatted'],
            dict_r['duration_seconds'],
            dict_r['duration_formatted'],
            dict_r['log_summary']
        ])

    csv_data = output.getvalue()
    filename = f"relatorio_backups_{start_date_str}_a_{end_date_str}.csv"

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

# --- APIS DE USUÁRIOS E GRUPOS ---

@app.route('/api/users', methods=['GET', 'POST'])
@login_required
def api_users():
    if request.method == 'GET':
        users = User.query.order_by(User.username).all()
        return jsonify([u.to_dict() for u in users])

    if request.method == 'POST':
        data = request.json or {}
        username = data.get('username')
        password = data.get('password')
        group_id = data.get('group_id')

        if not username or not password or not group_id:
            return jsonify({'error': 'Usuário, senha e grupo são obrigatórios'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Este nome de usuário já está em uso'}), 400

        user = User(
            username=username,
            email=data.get('email'),
            group_id=int(group_id),
            active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        return jsonify({'error': 'O usuário administrador principal não pode ser excluído'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/groups', methods=['GET', 'POST'])
@login_required
def api_groups():
    if request.method == 'GET':
        groups = Group.query.order_by(Group.name).all()
        return jsonify([g.to_dict() for g in groups])

    if request.method == 'POST':
        data = request.json or {}
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Nome do grupo é obrigatório'}), 400

        can_view_all = data.get('can_view_all_clients', False)
        group = Group(
            name=name,
            description=data.get('description'),
            can_manage_users=data.get('can_manage_users', False),
            can_manage_clients=data.get('can_manage_clients', False),
            can_view_all_clients=can_view_all
        )

        if not can_view_all:
            client_ids = data.get('client_ids', [])
            if client_ids:
                clients = Client.query.filter(Client.id.in_(client_ids)).all()
                group.allowed_clients = clients

        db.session.add(group)
        db.session.commit()
        return jsonify(group.to_dict()), 201

@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
@login_required
def api_delete_group(group_id):
    if group_id == 1:
        return jsonify({'error': 'O grupo Administradores principal não pode ser excluído'}), 400
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    return jsonify({'success': True})

def parse_duplicati_payload(data, raw_body=""):
    """
    Extrai status, tamanho em bytes e duração de qualquer versão de JSON ou Form do Duplicati.
    """
    if not isinstance(data, dict):
        return {'status': 'Success', 'bytes_copied': 0, 'duration_seconds': 0, 'backup_name': None}

    dict_sources = [
        data,
        data.get('Data', {}) if isinstance(data.get('Data'), dict) else {},
        data.get('Main', {}) if isinstance(data.get('Main'), dict) else {},
        data.get('Extra', {}) if isinstance(data.get('Extra'), dict) else {},
        data.get('Result', {}) if isinstance(data.get('Result'), dict) else {}
    ]

    backup_name = None
    for src in dict_sources:
        candidate = src.get('BackupName') or src.get('backup_name') or src.get('OperationName')
        if candidate and isinstance(candidate, str) and candidate.strip():
            backup_name = candidate.strip()
            break

    status = 'Success'
    for src in dict_sources:
        candidate = src.get('ParsedResult') or src.get('Result') or src.get('status')
        if candidate and isinstance(candidate, str):
            candidate_str = candidate.strip()
            if candidate_str in ('Success', 'Warning', 'Error', 'Fatal'):
                status = candidate_str
                break

    def find_key(obj, keys):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() in [key.lower() for key in keys]:
                    if v is not None and str(v).strip() != '':
                        return v
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    res = find_key(v, keys)
                    if res is not None:
                        return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_key(item, keys)
                if res is not None:
                    return res
        return None

    # Try to find bytes in order of priority: 
    # 1. BytesUploaded (Actual transfer size)
    # 2. SizeOfModifiedFiles + SizeOfAddedFiles (What changed)
    # 3. SizeOfOpenedFiles or SizeOfExaminedFiles (What was processed)
    def regex_fallback(keys):
        if not raw_body:
            return 0
        import re
        for key in keys:
            pattern = r'\\?["\']?' + key + r'\\?["\']?\s*[:=]\s*(\d+)'
            match = re.search(pattern, raw_body, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0

    def parse_int(v):
        try:
            return int(float(str(v)))
        except:
            return 0

    bytes_uploaded = parse_int(find_key(data, ['BytesUploaded'])) or regex_fallback(['BytesUploaded'])
    bytes_added = parse_int(find_key(data, ['SizeOfAddedFiles', 'AddedFilesSize', 'BytesAdded'])) or regex_fallback(['SizeOfAddedFiles', 'AddedFilesSize', 'BytesAdded'])
    bytes_mod = parse_int(find_key(data, ['SizeOfModifiedFiles', 'ModifiedFilesSize', 'BytesModified'])) or regex_fallback(['SizeOfModifiedFiles', 'ModifiedFilesSize', 'BytesModified'])
    bytes_opened = parse_int(find_key(data, ['SizeOfOpenedFiles', 'OpenedFilesSize', 'BytesOpened'])) or regex_fallback(['SizeOfOpenedFiles', 'OpenedFilesSize', 'BytesOpened'])
    bytes_exam = parse_int(find_key(data, ['SizeOfExaminedFiles', 'ExaminedFilesSize', 'BytesExamined'])) or regex_fallback(['SizeOfExaminedFiles', 'ExaminedFilesSize', 'BytesExamined'])
    
    bytes_copied = 0
    if bytes_uploaded > 0:
        bytes_copied = bytes_uploaded
    elif bytes_added > 0 or bytes_mod > 0:
        bytes_copied = bytes_added + bytes_mod
    elif bytes_opened > 0:
        bytes_copied = bytes_opened
    elif bytes_exam > 0:
        bytes_copied = bytes_exam
    else:
        # Fallback to older generic keys
        bytes_copied = parse_int(find_key(data, ['size'])) or regex_fallback(['size'])

    duration_seconds = 0
    dur_val = find_key(data, ['Duration'])
    if dur_val:
        dur_str = str(dur_val).strip()
        try:
            if ':' in dur_str:
                time_part = dur_str.split('.')[0]
                parts = time_part.split(':')
                if len(parts) == 3:
                    duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:
                    duration_seconds = int(parts[0]) * 60 + int(parts[1])
            else:
                duration_seconds = int(float(dur_str))
        except Exception:
            pass

    if duration_seconds == 0:
        begin_str = None
        end_str = None
        for src in dict_sources:
            if not begin_str: begin_str = src.get('BeginTime') or src.get('Begin') or src.get('StartTime')
            if not end_str: end_str = src.get('EndTime') or src.get('End') or src.get('StopTime')

        if begin_str and end_str:
            try:
                b_str = str(begin_str).split('.')[0].replace('Z', '')
                e_str = str(end_str).split('.')[0].replace('Z', '')
                dt_begin = datetime.fromisoformat(b_str)
                dt_end = datetime.fromisoformat(e_str)
                diff = int((dt_end - dt_begin).total_seconds())
                if diff > 0:
                    duration_seconds = diff
            except Exception:
                pass

    return {
        'backup_name': backup_name,
        'status': status,
        'bytes_copied': bytes_copied,
        'duration_seconds': duration_seconds
    }

# --- RECEPTORES PÚBLICOS DE WEBHOOK DO DUPLICATI ---

@app.route('/api/webhook/job/<webhook_token>', methods=['POST', 'GET'])
@app.route('/api/webhook/duplicati', methods=['POST', 'GET'])
def webhook_duplicati(webhook_token=None):
    """
    Receptor universal e por Token Único de Webhook.
    """
    try:
        data = {}
        raw_body = request.get_data(as_text=True)
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            try:
                data = json.loads(raw_body)
            except Exception:
                data = request.form.to_dict()

        from database import unwrap_duplicati_json
        data = unwrap_duplicati_json(data)

        if not webhook_token:
            webhook_token = request.args.get('token')

        target_job = None
        if webhook_token:
            target_job = Job.query.filter_by(webhook_token=webhook_token).first()

        parsed = parse_duplicati_payload(data, raw_body=raw_body)
        backup_name = parsed['backup_name'] or (target_job.job_name if target_job else 'Backup Desconhecido')
        status = parsed['status']
        bytes_copied = parsed['bytes_copied']
        duration_seconds = parsed['duration_seconds']

        if not target_job:
            target_job = Job.query.filter_by(job_name=backup_name).first()

        if not target_job:
            default_client = Client.query.first()
            if not default_client:
                default_client = Client(name="Cliente Padrão Webhook", notes="Criado automaticamente")
                db.session.add(default_client)
                db.session.commit()

            target_job = Job(
                client_id=default_client.id,
                job_name=backup_name,
                webhook_token=generate_webhook_token(),
                frequency_per_day=1,
                days_of_week="MON,TUE,WED,THU,FRI,SAT,SUN",
                expected_time="22:00"
            )
            db.session.add(target_job)
            db.session.commit()

        result = JobResult(
            job_id=target_job.id,
            execution_date=datetime.now(),
            bytes_copied=bytes_copied,
            status=status,
            duration_seconds=duration_seconds,
            log_summary=f"Recebido via Webhook (Job: {target_job.job_name}). Status: {status}",
            raw_payload=raw_body if raw_body else json.dumps(data, ensure_ascii=False)
        )
        db.session.add(result)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f"Resultado do backup '{target_job.job_name}' registrado com sucesso!",
            'job_id': target_job.id,
            'result_id': result.id,
            'bytes_copied': bytes_copied,
            'duration_seconds': duration_seconds
        }), 200

    except Exception as e:
        app.logger.error(f"Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
