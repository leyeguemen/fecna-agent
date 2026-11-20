# Imagen de la API FECNA para Hugging Face Spaces (SDK: Docker).
#
# Deliberadamente NO instala el requirements.txt de la raíz (streamlit,
# playwright, fpdf2…: eso es para Streamlit Cloud). Solo instala
# api/requirements-docker.txt, con lo mínimo que necesita en runtime.
#
# El índice semántico (data/chroma/) está en .gitignore y por lo tanto NO
# viaja con el repo: se reconstruye al arrancar (ver api/startup.py,
# ejecutado en el lifespan de api/main.py) a partir de data/fecna_public.db.
# Si por algún motivo sí existe un data/chroma/ local al construir la imagen,
# se copia igual (evita reconstruir en cada arranque).

FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema para pdfplumber (requiere libs de compresión de
# imagen que a veces exige apt en slim; pdfplumber en sí es puro Python +
# pdfminer.six, así que normalmente basta con pip).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements-docker.txt api/requirements-docker.txt
RUN pip install --no-cache-dir -r api/requirements-docker.txt

COPY fecna_agent/ fecna_agent/
COPY api/ api/
COPY data/fecna_public.db data/fecna_public.db

# data/chroma/ normalmente no existe en el checkout (está en .gitignore);
# si existiera, se copiaría acá y se usaría tal cual en el arranque.
# COPY data/chroma data/chroma

# Hugging Face Spaces expone el puerto 7860 por convención.
EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
