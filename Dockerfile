FROM python:3.12-slim

WORKDIR /app

# Instalar dependências do sistema necessárias para compilar algumas bibliotecas Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar os requerimentos e instalá-los
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante da aplicação
COPY . .

# Comando padrão para rodar a aplicação FastAPI
CMD ["uvicorn", "tools.glpi_tools:app", "--host", "0.0.0.0", "--port", "8000"]
