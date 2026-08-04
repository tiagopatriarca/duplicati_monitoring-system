-- Criar o banco de dados se não existir
CREATE DATABASE IF NOT EXISTS duplicati_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE duplicati_monitor;

-- Tabela de Clientes
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    contact_phone VARCHAR(50),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    status VARCHAR(50) NOT NULL, -- Success, Warning, Error, Fatal
    duration_seconds INT DEFAULT 0,
    log_summary TEXT,
    raw_payload TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Inserção de dados iniciais para demonstração (Dados de Exemplo)
INSERT INTO clients (id, name, email, contact_phone, notes) VALUES
(1, 'Empresa Alfa TI', 'ti@alfa.com.br', '(11) 98888-1111', 'Cliente Corporativo - Servidores Principais'),
(2, 'Beta Logística', 'suporte@betalog.com', '(21) 97777-2222', 'Filial Rio de Janeiro - MicroStation'),
(3, 'Gama Saúde', 'admin@gamasaude.med.br', '(31) 96666-3333', 'Banco de dados de Prontuários');

INSERT INTO jobs (id, client_id, job_name, frequency_per_day, days_of_week, expected_time, active) VALUES
(1, 1, 'Alfa-DB-Backup', 1, 'MON,TUE,WED,THU,FRI,SAT,SUN', '23:00', 1),
(2, 1, 'Alfa-Arquivos-PDF', 2, 'MON,TUE,WED,THU,FRI', '12:00,18:00', 1),
(3, 2, 'Beta-ERP-Daily', 1, 'MON,TUE,WED,THU,FRI', '20:00', 1),
(4, 3, 'Gama-Prontuarios-Full', 1, 'MON,TUE,WED,THU,FRI,SAT,SUN', '02:00', 1);

-- Resultados simulados de backups passados
INSERT INTO job_results (job_id, execution_date, bytes_copied, status, duration_seconds, log_summary) VALUES
(1, NOW() - INTERVAL 1 DAY, 15420000000, 'Success', 1450, 'Backup concluído com sucesso sem alertas.'),
(2, NOW() - INTERVAL 1 DAY, 420000000, 'Success', 120, 'Backup parcial dos arquivos PDF concluído.'),
(3, NOW() - INTERVAL 1 DAY, 8900000000, 'Warning', 2100, 'Backup concluído com 2 arquivos travados/em uso.'),
(1, NOW(), 16200000000, 'Success', 1520, 'Backup diário do banco executado perfeitamente.');
