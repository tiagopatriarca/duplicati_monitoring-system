from datetime import datetime, date
from database import Job, JobResult, Client

DAY_MAP = {
    0: 'MON',
    1: 'TUE',
    2: 'WED',
    3: 'THU',
    4: 'FRI',
    5: 'SAT',
    6: 'SUN'
}

DAY_LABELS_PT = {
    'MON': 'Segunda-feira',
    'TUE': 'Terça-feira',
    'WED': 'Quarta-feira',
    'THU': 'Quinta-feira',
    'FRI': 'Sexta-feira',
    'SAT': 'Sábado',
    'SUN': 'Domingo'
}

def format_bytes(size_bytes):
    """Formata quantidade de bytes em KB, MB, GB, TB legíveis."""
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"

def format_duration(seconds):
    """Formata duração em segundos para HH:MM:SS ou 'Xm Ys'."""
    if not seconds or seconds < 0:
        return "0s"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def check_missed_jobs(target_date=None, allowed_client_ids=None):
    """
    Verifica a conformidade dos jobs para uma determinada data.
    Suporta filtragem por clientes autorizados (allowed_client_ids).
    """
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

    day_code = DAY_MAP[target_date.weekday()]
    
    query = Job.query.filter_by(active=True)
    if allowed_client_ids is not None:
        query = query.filter(Job.client_id.in_(allowed_client_ids))

    all_jobs = query.all()
    missed_jobs = []

    for job in all_jobs:
        configured_days = job.get_days_list()
        
        if day_code in configured_days:
            start_dt = datetime.combine(target_date, datetime.min.time())
            end_dt = datetime.combine(target_date, datetime.max.time())
            
            executions_today = JobResult.query.filter(
                JobResult.job_id == job.id,
                JobResult.execution_date >= start_dt,
                JobResult.execution_date <= end_dt
            ).all()

            executed_count = len(executions_today)
            required_count = job.frequency_per_day

            if executed_count < required_count:
                last_status = executions_today[-1].status if executions_today else "Nenhuma Execução"
                
                missed_jobs.append({
                    'job_id': job.id,
                    'job_name': job.job_name,
                    'client_id': job.client_id,
                    'client_name': job.client.name if job.client else 'Desconhecido',
                    'target_date': target_date.strftime('%Y-%m-%d'),
                    'day_of_week': DAY_LABELS_PT.get(day_code, day_code),
                    'frequency_per_day': required_count,
                    'executions_found': executed_count,
                    'missing_executions': required_count - executed_count,
                    'expected_time': job.expected_time or 'Não especificado',
                    'last_status': last_status,
                    'status_alert': 'NÃO EXECUTADO' if executed_count == 0 else 'PARCIALMENTE EXECUTADO',
                    'needs_investigation': True
                })

    return missed_jobs
