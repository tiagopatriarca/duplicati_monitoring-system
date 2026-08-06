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

    from datetime import timedelta
    eval_date = target_date - timedelta(days=1)
    day_code = DAY_MAP[eval_date.weekday()]
    
    query = Job.query.filter_by(active=True)
    if allowed_client_ids is not None:
        query = query.filter(Job.client_id.in_(allowed_client_ids))

    all_jobs = query.all()
    missed_jobs = []

    for job in all_jobs:
        configured_days = job.get_days_list()
        
        if day_code in configured_days:
            start_dt = datetime.combine(eval_date, datetime.min.time())
            end_dt = datetime.combine(eval_date, datetime.max.time())
            
            executions_eval_date = JobResult.query.filter(
                JobResult.job_id == job.id,
                JobResult.execution_date >= start_dt,
                JobResult.execution_date <= end_dt
            ).all()

            success_executions = [e for e in executions_eval_date if e.status == 'Success']

            if len(success_executions) == 0:
                last_status = executions_eval_date[-1].status if executions_eval_date else "Nenhuma Execução"
                
                missed_jobs.append({
                    'job_id': job.id,
                    'job_name': job.job_name,
                    'client_id': job.client_id,
                    'client_name': job.client.name if job.client else 'Desconhecido',
                    'target_date': eval_date.strftime('%Y-%m-%d'),
                    'day_of_week': DAY_LABELS_PT.get(day_code, day_code),
                    'frequency_per_day': job.frequency_per_day,
                    'executions_found': len(executions_eval_date),
                    'missing_executions': job.frequency_per_day - len(executions_eval_date),
                    'expected_time': job.expected_time or 'Não especificado',
                    'last_status': last_status,
                    'status_alert': 'FALHA OU NÃO EXECUTADO',
                    'needs_investigation': True
                })

    return missed_jobs
