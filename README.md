# 🛡️ DuplicatiShield - Sistema de Monitoramento de Backups Duplicati (Python + MySQL + Traefik + SSL + Docker)

Sistema completo em Python para recepção de notificações/webhooks do **Duplicati**, armazenamento em **MySQL**, gerenciamento de agendamento/frequência por cliente, **autenticação com controle de acesso por grupos (RBAC)**, **URLs únicas de webhook por Job**, e **Proxy Reverso Traefik** para emissão automática de certificados **SSL (HTTPS)** com Let's Encrypt.

---

## 🔒 Publicação com Domínio & SSL Gratuito (Traefik + Let's Encrypt)

O projeto já inclui o **Traefik v2** integrado no `docker-compose.yml` para gerenciar automaticamente:
- Redirecionamento automático de **HTTP (porta 80)** para **HTTPS (porta 443)**.
- Geração e renovação automática do certificado de segurança **SSL Let's Encrypt**.

### Como configurar seu Domínio:

1. Edite o arquivo `.env` (ou variáveis de ambiente no painel Docker da Hostinger):
   ```env
   DOMAIN_NAME=meubackup.com.br
   LETSENCRYPT_EMAIL=patriarca.info@gmail.com
   ```
2. No seu registrador de domínio (Hostinger, Registro.br, Cloudflare, etc.), crie um **Apontamento tipo A**:
   - **Nome / Host**: `meubackup.com.br` (ou `subdominio.meudominio.com.br`)
   - **Valor / IP**: `187.77.46.13` (IP do seu servidor VPS Hostinger)

---

## 🚀 Como Executar com Docker Compose

```bash
# 1. Acesse a pasta do projeto
cd C:\Users\DATEN\.gemini\antigravity\scratch\duplicati_monitoring

# 2. Suba a aplicação com Traefik, MySQL e Web App
docker-compose up -d --build
```

---

## 🔑 Credenciais Iniciais de Acesso Padrão

- **Usuário**: `admin`
- **Senha**: `duplicati`

---

## 🎯 Integração com o Duplicati via URL Única

Cada job cadastrado na aba **Clientes & Jobs** gera uma **URL de Webhook Exclusiva** (com o token único do job).

Exemplo de uso no Duplicati:
```text
--send-http-url=https://meubackup.com.br/api/webhook/job/job_a8f9c1d2e3f4
```
> O sistema associará os relatórios do backup com 100% de precisão ao Cliente e Job correto no painel.
