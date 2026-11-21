# Imagen de la API FECNA (Render, Fly.io o cualquier host Docker).
#
# Solo instala api/requirements-docker.txt (lo mínimo de runtime). Los datos viven
# en Postgres (DATABASE_URL), no en la imagen. Sin ANTHROPIC_API_KEY la API cae al
# agente determinístico, que usa SQLite local: en ese modo hay que montar la base.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements-docker.txt api/requirements-docker.txt
RUN pip install --no-cache-dir -r api/requirements-docker.txt

COPY fecna_agent/ fecna_agent/
COPY api/ api/

# Render inyecta $PORT; 7860 es el valor por defecto (Hugging Face Spaces).
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
