import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'duplicati_secret_key_default_2026')
    
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_USER = os.getenv('MYSQL_USER', 'duplicati_user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'duplicati_password_123')
    MYSQL_DB = os.getenv('MYSQL_DB', 'duplicati_monitor')
    
    # URL de Conexão com o MySQL via PyMySQL
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    
    # No ambiente Docker (MYSQL_HOST=db), NÃO usar fallback para SQLite para forçar uso do MySQL
    is_docker = MYSQL_HOST in ('db', 'mysql', 'duplicati_mysql_db')
    USE_SQLITE_FALLBACK = False if is_docker else (os.getenv('USE_SQLITE_FALLBACK', 'true').lower() in ('true', '1'))
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
