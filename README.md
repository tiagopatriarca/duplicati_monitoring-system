# 🛡️ DuplicatiShield - Sistema de Monitoramento de Backups Duplicati (Python + MySQL + Docker)

Sistema completo em Python para recepção de notificações/webhooks do **Duplicati**, armazenamento de histórico em banco de dados **MySQL**, gerenciamento de agendamento/frequência por cliente, alertas dinâmicos para **jobs não executados (destaque para investigação)** e relatórios consolidados por período com exportação CSV e impressão.

---

## 🚀 Como Executar com Docker & Docker Compose (Recomendado)

O projeto já inclui toda a estrutura necessária para subir o banco **MySQL 8.0** e o container da aplicação **Python/Flask** com um único comando.

### 1. Clonar ou Acessar a Pasta do Projeto
```bash
cd C:\Users\DATEN\.gemini\antigravity\scratch\duplicati_monitoring
```

### 2. Iniciar os Containers Docker
```bash
docker-compose up -d --build
```
> Isso irá:
> - Subir o container MySQL (`duplicati_mysql_db`) na porta `3306` com inicialização automática do banco e tabelas (`schema.sql`).
> - Construir a imagem Python (`duplicati_web_app`) e subir o servidor na porta `5000`.

### 3. Acessar a Aplicação
Abra seu navegador em:
👉 **[http://localhost:5000](http://localhost:5000)**

---

## 💻 Como Executar em Modo Local (Sem Docker)

Caso queira executar a aplicação diretamente no seu ambiente Python local:

1. **Instalar dependências**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Iniciar a aplicação**:
   ```bash
   python app.py
   ```
   *(O sistema detectará se o MySQL está offline e ativará automaticamente um banco de dados SQLite local de fallback para testes sem interrupções).*

---

## 📡 Como Configurar o Duplicati para Enviar Notificações

No painel do Duplicati (em cada job de backup ou nas **Opções Avançadas Globais**), adicione a seguinte opção:

```text
--send-http-url=http://<IP-DO-SEU-SERVIDOR>:5000/api/webhook/duplicati
--send-http-result-output-format=json
```

### Testar Envio de Webhooks Imediatamente:
Você pode executar o script de teste incluído no projeto:
```bash
python simulate_webhook.py
```

---

## 📋 Recursos Principais do Sistema

1. **Monitoramento de Histórico**:
   - Data e hora exata da execução.
   - Volume de dados transferidos (formatado em KB/MB/GB/TB).
   - Status da execução (`Success`, `Warning`, `Error`, `Fatal`).
   - Duração da rotina (formatado em minutos/segundos).

2. **Destaque Visual para Jobs Não Realizados (Investigação)**:
   - Configuração de frequência diária (ex: 1x, 2x ao dia) e dias da semana ativos (ex: Seg-Sex).
   - Painel inteligente que detecta a ausência de logs na data agendada e sinaliza o job com um **alerta pulsante vermelho de destaque**.

3. **Gerenciador de Clientes e Jobs**:
   - Agrupamento de rotinas por cliente corporativo.
   - Modais para cadastro rápido de novos clientes e regras de backup.

4. **Área de Relatórios por Período**:
   - Seleção de intervalo de datas (Data Inicial até Data Final).
   - Estatísticas consolidadas (Total de execuções, taxa de sucesso %, volume total).
   - Exportação em formato **CSV** e suporte a **Impressão/PDF**.
