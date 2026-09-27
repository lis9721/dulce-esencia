# Imagen del backend (FastAPI). Construir desde la carpeta backend/:
#   docker build -t essentia-api .
#   docker run --env-file .env -p 8000:8000 essentia-api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

# Dependencias primero: la capa se reutiliza mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY database ./database
COPY uploads ./uploads

# No se corre como root dentro del contenedor.
RUN useradd --create-home appuser && chown -R appuser /srv
USER appuser

EXPOSE 8000
# Las plataformas (Railway, Render...) inyectan $PORT; en local queda 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
