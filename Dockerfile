# Usar imagem oficial do Python em versão leve
FROM python:3.11-slim

# Evitar criação de arquivos .pyc e garantir output direto dos logs no terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependências de sistema necessárias para compilação e MySQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho na imagem
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código-fonte da aplicação
COPY . .

# Expor a porta em que a aplicação irá rodar
EXPOSE 5000

# Comando padrão para iniciar o servidor web via Gunicorn em produção
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]
