# ── Build stage ──────────────────────────────────────────────────────────────
# Use a slim Python 3.13 image to keep the layer small.
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build tools needed by some wheels (e.g. chromadb's C extensions).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy only the dependency manifest first so Docker can cache this layer.
COPY requirements.txt .

# Install into a prefix that the runtime stage can copy wholesale.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

# Carry across the installed packages from the builder.
COPY --from=builder /install /usr/local

# Copy application source (everything not excluded by .dockerignore).
COPY . .

# Create a non-root user so the container does not run as root.
RUN addgroup --system astraops \
    && adduser --system --ingroup astraops astraops \
    && chown -R astraops:astraops /app

USER astraops

# The PORT env var is set by Render (and most other PaaS providers).
# Fall back to 8000 for local `docker run` usage.
ENV PORT=8000

EXPOSE ${PORT}

# uvicorn reads $PORT at shell-expansion time via the exec form + shell wrapper.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
