-- Criar o banco de dados se não existir
CREATE DATABASE IF NOT EXISTS duplicati_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE duplicati_monitor;

-- Tabela de Grupos (Funções / Permissões)
CREATE TABLE IF NOT EXISTS groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    can_manage_users TINYINT(1) DEFAULT 0,
    can_manage_clients TINYINT(1) DEFAULT 0,
    can_view_all_clients TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Clientes
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    contact_phone VARCHAR(50),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Associação N:N entre Grupos e Clientes autorizados
CREATE TABLE IF NOT EXISTS group_clients (
    group_id INT NOT NULL,
    client_id INT NOT NULL,
    PRIMARY KEY (group_id, client_id),
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150),
    password_hash VARCHAR(255) NOT NULL,
    group_id INT,
    active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Jobs Agendados
CREATE TABLE IF NOT EXISTS jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    job_name VARCHAR(150) NOT NULL,
    frequency_per_day INT DEFAULT 1,
    days_of_week VARCHAR(100) DEFAULT 'MON,TUE,WED,THU,FRI,SAT,SUN',
    expected_time VARCHAR(10) DEFAULT '22:00',
    active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    UNIQUE KEY uq_client_job (client_id, job_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Histórico de Execuções dos Jobs
CREATE TABLE IF NOT EXISTS job_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    execution_date DATETIME NOT NULL,
    bytes_copied BIGINT DEFAULT 0,
    status VARCHAR(50) NOT NULL,
    duration_seconds INT DEFAULT 0,
    log_summary TEXT,
    raw_payload TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Inserção do Grupo Administrador Padrão (ID 1)
INSERT INTO groups (id, name, description, can_manage_users, can_manage_clients, can_view_all_clients) VALUES
(1, 'Administradores', 'Acesso total a todos os clientes e gerenciamento de usuários', 1, 1, 1),
(2, 'Técnicos de Suporte', 'Acesso de monitoramento a clientes autorizados', 0, 0, 0)
ON DUPLICATE KEY UPDATE name=name;

-- Inserção do Usuário Padrão Admin (Senha: duplicati)
-- A senha 'duplicati' é redefinida e garantida automaticamente na inicialização via app.py
INSERT INTO users (id, username, email, password_hash, group_id, active) VALUES
(1, 'admin', 'admin@duplicatishield.com', 'scrypt:32768:8:1$7W3K34Nf1KqO2s9e$e6a575a7c2b64d1f2a33eb221199aef5f7c320d3f820257e3f890e66d48259df92d4fdfa0ecbfae2adfd529e46a7be74a6aa7ec59b5d2dd7b64082fb8f3f80c6', 1, 1)
ON DUPLICATE KEY UPDATE username=username;

-- Dados Iniciais de Exemplo de Clientes
INSERT INTO clients (id, name, email, contact_phone, notes) VALUES
(1, 'Empresa Alfa TI', 'ti@alfa.com.br', '(11) 98888-1111', 'Servidores Principais'),
(2, 'Beta Logística', 'suporte@betalog.com', '(21) 97777-2222', 'Filial Rio de Janeiro'),
(3, 'Gama Saúde', 'admin@gamasaude.med.br', '(31) 96666-3333', 'Banco de dados de Prontuários')
ON DUPLICATE KEY UPDATE name=name;

INSERT INTO jobs (id, client_id, job_name, frequency_per_day, days_of_week, expected_time, active) VALUES
(1, 1, 'Alfa-DB-Backup', 1, 'MON,TUE,WED,THU,FRI,SAT,SUN', '23:00', 1),
(2, 1, 'Alfa-Arquivos-PDF', 2, 'MON,TUE,WED,THU,FRI', '12:00,18:00', 1),
(3, 2, 'Beta-ERP-Daily', 1, 'MON,TUE,WED,THU,FRI', '20:00', 1),
(4, 3, 'Gama-Prontuarios-Full', 1, 'MON,TUE,WED,THU,FRI,SAT,SUN', '02:00', 1)
ON DUPLICATE KEY UPDATE job_name=job_name;

INSERT INTO job_results (job_id, execution_date, bytes_copied, status, duration_seconds, log_summary) VALUES
(1, NOW() - INTERVAL 1 DAY, 15420000000, 'Success', 1450, 'Backup concluído com sucesso.'),
(2, NOW() - INTERVAL 1 DAY, 420000000, 'Success', 120, 'Backup parcial dos arquivos PDF.'),
(3, NOW() - INTERVAL 1 DAY, 8900000000, 'Warning', 2100, 'Alerta: 2 arquivos em uso.'),
(1, NOW(), 16200000000, 'Success', 1520, 'Backup diário executado perfeitamente.');
