import json
import csv
import io
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, Response
from sqlalchemy.exc import OperationalError

from config import Config
from database import db, Client, Job, JobResult
from utils import check_missed_jobs, format_bytes, format_duration

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar Banco de Dados
db.init_app(app)

def init_db_with_fallback():
    """
    Tenta conectar ao MySQL. Se falhar e a flag de fallback estiver ativa,
    alterna automaticamente para SQLite em arquivo local.
    """
    with app.app_context():
        try:
            db.create_all()
            print("Conectado ao Banco de Dados MySQL com sucesso!")
        except Exception as e:
            print(f"Aviso: Não foi possível conectar ao MySQL ({e}).")
            if app.config.get('USE_SQLITE_FALLBACK'):
                print("Ativando banco de dados local de fallback SQLite (duplicati_local.db)...")
                app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///duplicati_local.db'
                db.init_app(app)
                db.create_all()
                print("Banco de dados SQLite inicializado!")

        # Inserir dados iniciais se o banco estiver completamente vazio
        if Client.query.count() == 0:
            seed_initial_data()

def seed_initial_data():
    """Insere dados de exemplo para facilitar a primeira navegação."""
    c1 = Client(name="Empresa Alfa TI", email="ti@alfa.com.br", contact_phone="(11) 98888-1111", notes="Servidores Principais")
    c2 = Client(name="Beta Logística", email="suporte@betalog.com", contact_phone="(21) 97777-2222", notes="Filial Rio")
    c3 = Client(name="Gama Saúde", email="admin@gamasaude.med.br", contact_phone="(31) 96666-3333", notes="Prontuários eletrônicos")
    
    db.session.add_all([c1, c2, c3])
    db.session.commit()

    j1 = Job(client_id=c1.id, job_name="Alfa-DB-Backup", frequency_per_day=1, days_of_week="MON,TUE,WED,THU,FRI,SAT,SUN", expected_time="23:00")
    j2 = Job(client_id=c1.id, job_name="Alfa-Arquivos-PDF", frequency_per_day=2, days_of_week="MON,TUE,WED,THU,FRI", expected_time="12:00,18:00")
    j3 = Job(client_id=c2.id, job_name="Beta-ERP-Daily", frequency_per_day=1, days_of_week="MON,TUE,WED,THU,FRI", expected_time="20:00")
    j4 = Job(client_id=c3.id, job_name="Gama-Prontuarios-Full", frequency_per_day=1, days_of_week="MON,TUE,WED,THU,FRI,SAT,SUN", expected_time="02:00")
    
    db.session.add_all([j1, j2, j3, j4])
    db.session.commit()

    now = datetime.now()
    r1 = JobResult(job_id=j1.id, execution_date=now - timedelta(days=1), bytes_copied=15420000000, status="Success", duration_seconds=1450, log_summary="Backup concluído com sucesso.")
    r2 = JobResult(job_id=j2.id, execution_date=now - timedelta(days=1), bytes_copied=420000000, status="Success", duration_seconds=120, log_summary="Backup parcial efetuado.")
    r3 = JobResult(job_id=j3.id, execution_date=now - timedelta(days=1), bytes_copied=8900000000, status="Warning", duration_seconds=2100, log_summary="Alerta: 2 arquivos bloqueados durante a leitura.")
    r4 = JobResult(job_id=j1.id, execution_date=now, bytes_copied=16200000000, status="Success", duration_seconds=1520, log_summary="Backup diário concluído.")
    
    db.session.add_all([r1, r2, r3, r4])
    db.session.commit()

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---

def init_db_with_fallback():
    """
    Tenta conectar ao MySQL. Se falhar e a flag de fallback estiver ativa,
    alterna automaticamente para SQLite em arquivo local.
    """
    try:
        db.create_all()
        print("Conectado ao Banco de Dados MySQL com sucesso!")
    except Exception as e:
        print(f"Aviso: Não foi possível conectar ao MySQL ({e}).")
        if app.config.get('USE_SQLITE_FALLBACK'):
            print("Ativando banco de dados local de fallback SQLite (duplicati_local.db)...")
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///duplicati_local.db'
            db.init_app(app)
            db.create_all()
            print("Banco de dados SQLite inicializado!")

    try:
        # Inserir dados iniciais se o banco estiver completamente vazio
        if Client.query.count() == 0:
            seed_initial_data()
    except Exception as e:
        print(f"Erro ao verificar/inserir dados iniciais: {e}")

def seed_initial_data():
    """Insere dados de exemplo para facilitar a primeira navegação."""
    c1 = Client(name="Empresa Alfa TI", email="ti@alfa.com.br", contact_phone="(11) 98888-1111", notes="Servidores Principais")
    c2 = Client(name="Beta Logística", email="suporte@betalog.com", contact_phone="(21) 97777-2222", notes="Filial Rio")
    c3 = Client(name="Gama Saúde", email="admin@gamasaude.med.br", contact_phone="(31) 96666-3333", notes="Prontuários eletrônicos")
    
    db.session.add_all([c1, c2, c3])
    db.session.commit()

    j1 = Job(client_id=c1.id, job_name="Alfa-DB-Backup", frequency_per_day=1, days_of_week="MON,TUE,WED,THU,FRI,SAT,SUN", expected_time="23:00")
    j2 = Job(client_id=c1.id, job_name="Alfa-Arquivos-PDF", frequency_per_day=2, days_of_week="MON,TUE,WED,THU,FRI", expected_time="12:00,18:00")
    j3 = Job(client_id=c2.id, job_name="Beta-ERP-Daily", frequency_per_day=1, days_of_week="MON,TUE,WED,THU,FRI", expected_time="20:00")
    j4 = Job(client_id=c3.id, job_name="Gama-Prontuarios-Full", frequency_per_day=1, days_of_week="MON,TUE,WED,THU,FRI,SAT,SUN", expected_time="02:00")
    
    db.session.add_all([j1, j2, j3, j4])
    db.session.commit()

    now = datetime.now()
    r1 = JobResult(job_id=j1.id, execution_date=now - timedelta(days=1), bytes_copied=15420000000, status="Success", duration_seconds=1450, log_summary="Backup concluído com sucesso.")
    r2 = JobResult(job_id=j2.id, execution_date=now - timedelta(days=1), bytes_copied=420000000, status="Success", duration_seconds=120, log_summary="Backup parcial efetuado.")
    r3 = JobResult(job_id=j3.id, execution_date=now - timedelta(days=1), bytes_copied=8900000000, status="Warning", duration_seconds=2100, log_summary="Alerta: 2 arquivos bloqueados durante a leitura.")
    r4 = JobResult(job_id=j1.id, execution_date=now, bytes_copied=16200000000, status="Success", duration_seconds=1520, log_summary="Backup diário concluído.")
    
    db.session.add_all([r1, r2, r3, r4])
    db.session.commit()

# Inicializar Banco de Dados tanto em execução via `python app.py` quanto em `Gunicorn`
with app.app_context():
    init_db_with_fallback()

# --- ROTAS DA INTERFACE WEB ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clients')
def clients_page():
    return render_template('clients.html')

@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/reports')
def reports_page():
    return render_template('reports.html')

@app.route('/webhook-guide')
def webhook_guide_page():
    return render_template('webhook_guide.html')

# --- ROTAS DA API ---

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """Retorna métricas gerais do sistema e lista de jobs com pendência/destaque."""
    target_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = date.today()

    try:
        total_clients = Client.query.count()
        total_jobs = Job.query.filter_by(active=True).count()

        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        
        results_today = JobResult.query.filter(
            JobResult.execution_date >= start_dt,
            JobResult.execution_date <= end_dt
        ).all()

        success_today = sum(1 for r in results_today if r.status == 'Success')
        warning_today = sum(1 for r in results_today if r.status == 'Warning')
        error_today = sum(1 for r in results_today if r.status in ('Error', 'Fatal'))
        total_bytes_today = sum(r.bytes_copied for r in results_today)

        missed_jobs = check_missed_jobs(target_date)
        recent_results = JobResult.query.order_by(JobResult.execution_date.desc()).limit(10).all()

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
def api_clients():
    if request.method == 'GET':
        try:
            clients = Client.query.order_by(Client.name).all()
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

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
def api_delete_client(client_id):
    try:
        client = Client.query.get_or_404(client_id)
        db.session.delete(client)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cliente removido com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao excluir cliente: {str(e)}'}), 500

@app.route('/api/jobs', methods=['GET', 'POST'])
def api_jobs():
    if request.method == 'GET':
        try:
            jobs = Job.query.order_by(Job.job_name).all()
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
            if isinstance(days_list, list):
                days_str = ','.join(days_list)
            else:
                days_str = str(days_list)

            job = Job(
                client_id=int(client_id),
                job_name=job_name,
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

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def api_delete_job(job_id):
    try:
        job = Job.query.get_or_404(job_id)
        db.session.delete(job)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Job removido com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao excluir job: {str(e)}'}), 500


@app.route('/api/history')
def api_history():
    query = JobResult.query.join(Job).join(Client)

    # Filtro por Cliente
    client_id = request.args.get('client_id')
    if client_id:
        query = query.filter(Job.client_id == client_id)

    # Filtro por Status
    status = request.args.get('status')
    if status:
        query = query.filter(JobResult.status == status)

    # Filtro por Período de Datas
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date:
        dt_start = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(JobResult.execution_date >= dt_start)
    
    if end_date:
        dt_end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(JobResult.execution_date < dt_end)

    results = query.order_by(JobResult.execution_date.desc()).all()
    return jsonify([r.to_dict() for r in results])

@app.route('/api/reports')
def api_reports():
    """Gera dados analíticos de relatório por período."""
    start_date_str = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    client_id = request.args.get('client_id')

    dt_start = datetime.strptime(start_date_str, '%Y-%m-%d')
    dt_end = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

    query = JobResult.query.join(Job).filter(
        JobResult.execution_date >= dt_start,
        JobResult.execution_date < dt_end
    )

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

    return jsonify({
        'period': {'start': start_date_str, 'end': end_date_str},
        'summary': {
            'total_executions': total_executions,
            'success_count': success_count,
            'warning_count': warning_count,
            'error_count': error_count,
            'success_rate': success_rate,
            'total_bytes_formatted': format_bytes(total_bytes),
            'total_duration_formatted': format_duration(total_seconds)
        },
        'records': [r.to_dict() for r in results]
    })

@app.route('/api/reports/export')
def api_reports_export_csv():
    """Exporta o relatório do período selecionado em arquivo CSV."""
    start_date_str = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    client_id = request.args.get('client_id')

    dt_start = datetime.strptime(start_date_str, '%Y-%m-%d')
    dt_end = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

    query = JobResult.query.join(Job).filter(
        JobResult.execution_date >= dt_start,
        JobResult.execution_date < dt_end
    )

    if client_id:
        query = query.filter(Job.client_id == client_id)

    results = query.order_by(JobResult.execution_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # Cabeçalho do CSV
    writer.writerow(['ID', 'Cliente', 'Nome do Job', 'Data Execução', 'Status', 'Tamanho Copiado', 'Duração', 'Resumo Log'])

    for r in results:
        dict_r = r.to_dict()
        writer.writerow([
            dict_r['id'],
            dict_r['client_name'],
            dict_r['job_name'],
            dict_r['execution_date'],
            dict_r['status'],
            dict_r['bytes_formatted'],
            dict_r['duration_formatted'],
            dict_r['log_summary']
        ])

    csv_data = output.getvalue()
    filename = f"relatorio_backups_{start_date_str}_a_{end_date_str}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

# --- RECEPTOR DE WEBHOOK DO DUPLICATI ---

@app.route('/api/webhook/duplicati', methods=['POST'])
def webhook_duplicati():
    """
    Endpoint de recepção de notificações do Duplicati (--send-http-url).
    Suporta payload em JSON ou Form Data gerado pelo Duplicati.
    """
    try:
        data = {}
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            # Duplicati envia dados via Form ou JSON bruto no body
            try:
                raw_body = request.get_data(as_text=True)
                data = json.loads(raw_body)
            except Exception:
                data = request.form.to_dict()

        # Extrair dados principais do Duplicati
        # Duplicati envia os parâmetros com prefixo "Extra/" ou "Main/" ou em JSON direto
        backup_name = (
            data.get('Extra', {}).get('BackupName') or 
            data.get('BackupName') or 
            data.get('backup_name') or 
            data.get('OperationName') or 
            'Backup Desconhecido'
        )

        parsed_result = (
            data.get('ParsedResult') or 
            data.get('Main', {}).get('ParsedResult') or 
            data.get('Result') or 
            'Success'
        )

        # Mapeamento do resultado do Duplicati para o padrão do sistema
        status_map = {
            'Success': 'Success',
            'Warning': 'Warning',
            'Error': 'Error',
            'Fatal': 'Fatal'
        }
        status = status_map.get(parsed_result, 'Success')

        # Extração do tamanho copiado em bytes
        bytes_copied = 0
        main_data = data.get('Main', {})
        if isinstance(main_data, dict):
            bytes_copied = (
                main_data.get('SizeOfAddedFiles', 0) or 
                main_data.get('BytesUploaded', 0) or 
                main_data.get('SizeOfExaminedFiles', 0)
            )
        if not bytes_copied:
            bytes_copied = data.get('BytesUploaded', 0) or data.get('SizeOfAddedFiles', 0)

        try:
            bytes_copied = int(bytes_copied)
        except Exception:
            bytes_copied = 0

        # Duração em segundos
        duration_seconds = 0
        duration_str = main_data.get('Duration') or data.get('Duration')
        if duration_str:
            try:
                # Duplicati formata duração em "00:15:30.123" ou em segundos soltos
                if ':' in str(duration_str):
                    parts = str(duration_str).split('.')[0].split(':')
                    if len(parts) == 3:
                        duration_seconds = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                else:
                    duration_seconds = int(float(duration_str))
            except Exception:
                duration_seconds = 0

        # Localizar ou criar o Job automaticamente
        job = Job.query.filter_by(job_name=backup_name).first()
        
        if not job:
            # Tentar associar ao primeiro cliente existente ou criar cliente padrão
            default_client = Client.query.first()
            if not default_client:
                default_client = Client(name="Cliente Padrão Webhook", notes="Criado automaticamente pelo Webhook")
                db.session.add(default_client)
                db.session.commit()

            job = Job(
                client_id=default_client.id,
                job_name=backup_name,
                frequency_per_day=1,
                days_of_week="MON,TUE,WED,THU,FRI,SAT,SUN",
                expected_time="22:00"
            )
            db.session.add(job)
            db.session.commit()

        # Registrar o Resultado no Histórico
        result = JobResult(
            job_id=job.id,
            execution_date=datetime.now(),
            bytes_copied=bytes_copied,
            status=status,
            duration_seconds=duration_seconds,
            log_summary=f"Recebido via Webhook do Duplicati. Status original: {parsed_result}",
            raw_payload=json.dumps(data, ensure_ascii=False)
        )
        db.session.add(result)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Resultado de backup registrado com sucesso!',
            'job_id': job.id,
            'result_id': result.id
        }), 200

    except Exception as e:
        app.logger.error(f"Erro ao processar webhook do Duplicati: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db_with_fallback()
    app.run(host='0.0.0.0', port=5000, debug=True)
