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
    
    # Configuração de Fallback para SQLite em desenvolvimento local sem Docker/MySQL
    USE_SQLITE_FALLBACK = os.getenv('USE_SQLITE_FALLBACK', 'true').lower() in ('true', '1')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
