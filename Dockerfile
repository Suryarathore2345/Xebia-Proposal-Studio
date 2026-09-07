# Xebia Proposal Studio — Render deploy image.
#
# Pinned to 3.12 rather than matching local dev's 3.14: sentence-transformers
# pulls in torch, and prebuilt torch wheels for very new Python versions lag
# behind — 3.12 is the safe, widely-supported choice for a from-scratch
# container build.
FROM python:3.12-slim

# libcairo2: native dependency for cairosvg (icon rasterization).
# fonts-liberation / fonts-crosextra-carlito: metric-compatible substitutes
# for Arial/Calibri so geometry_check.py's real font-metric overflow QA
# still works on Linux, where the real Microsoft fonts aren't available
# (see src/generation/qa/geometry_check.py).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    fonts-liberation \
    fonts-crosextra-carlito \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Render sets $PORT at runtime; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn src.web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
