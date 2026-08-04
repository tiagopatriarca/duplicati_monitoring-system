from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

# Tabela de Associação N:N entre Grupos e Clientes autorizados
group_clients = db.Table('group_clients',
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('clients.id', ondelete='CASCADE'), primary_key=True)
)

class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_manage_clients = db.Column(db.Boolean, default=False)
    can_view_all_clients = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Clientes específicos liberados para este grupo
    allowed_clients = db.relationship('Client', secondary=group_clients, lazy='subquery',
                                      backref=db.backref('groups', lazy=True))
    users = db.relationship('User', backref='group', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or '',
            'can_manage_users': self.can_manage_users,
            'can_manage_clients': self.can_manage_clients,
            'can_view_all_clients': self.can_view_all_clients,
            'allowed_client_ids': [c.id for c in self.allowed_clients],
            'allowed_client_names': [c.name for c in self.allowed_clients]
        }

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_allowed_client_ids(self):
        """Retorna lista de IDs de clientes aos quais o usuário tem acesso."""
        if not self.group or self.group.can_view_all_clients:
            return None  # None significa acesso total a todos os clientes
        return [c.id for c in self.group.allowed_clients]

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email or '',
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else 'Sem Grupo',
            'active': self.active,
            'can_manage_users': self.group.can_manage_users if self.group else False,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com Jobs
    jobs = db.relationship('Job', backref='client', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email or '',
            'contact_phone': self.contact_phone or '',
            'notes': self.notes or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'job_count': len(self.jobs)
        }

class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    job_name = db.Column(db.String(150), nullable=False)
    frequency_per_day = db.Column(db.Integer, default=1)
    days_of_week = db.Column(db.String(100), default='MON,TUE,WED,THU,FRI,SAT,SUN')
    expected_time = db.Column(db.String(10), default='22:00')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com Histórico
    results = db.relationship('JobResult', backref='job', lazy=True, cascade="all, delete-orphan")

    def get_days_list(self):
        if not self.days_of_week:
            return []
        return [d.strip().upper() for d in self.days_of_week.split(',') if d.strip()]

    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else 'Desconhecido',
            'job_name': self.job_name,
            'frequency_per_day': self.frequency_per_day,
            'days_of_week': self.days_of_week,
            'expected_time': self.expected_time,
            'active': self.active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class JobResult(db.Model):
    __tablename__ = 'job_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    execution_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    bytes_copied = db.Column(db.BigInteger, default=0)
    status = db.Column(db.String(50), nullable=False)  # Success, Warning, Error, Fatal
    duration_seconds = db.Column(db.Integer, default=0)
    log_summary = db.Column(db.Text, nullable=True)
    raw_payload = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        from utils import format_bytes, format_duration
        return {
            'id': self.id,
            'job_id': self.job_id,
            'job_name': self.job.job_name if self.job else 'Job Excluído',
            'client_name': self.job.client.name if self.job and self.job.client else 'Desconhecido',
            'client_id': self.job.client_id if self.job else None,
            'execution_date': self.execution_date.strftime('%Y-%m-%d %H:%M:%S') if self.execution_date else '',
            'bytes_copied': self.bytes_copied,
            'bytes_formatted': format_bytes(self.bytes_copied),
            'status': self.status,
            'duration_seconds': self.duration_seconds,
            'duration_formatted': format_duration(self.duration_seconds),
            'log_summary': self.log_summary or ''
        }
