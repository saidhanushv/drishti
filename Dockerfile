# ==========================================
# Stage 1: Build Frontend (Angular)
# ==========================================
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Copy package files first for better caching
COPY frontend/package*.json ./
RUN npm ci

# Copy source code
COPY frontend/ ./

# Build the application
RUN npm run build

# ==========================================
# Stage 2: Build Backend & Final Image
# ==========================================
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Pre-computed Data
COPY backend/faiss_index ./faiss_index
COPY backend/promotion_data.duckdb ./promotion_data.duckdb
COPY backend/downloads ./downloads

# Copy Backend Code
COPY backend/*.py ./
COPY backend/app ./app
COPY backend/tools ./tools

# Copy Built Frontend from Stage 1
COPY --from=frontend-build /app/frontend/dist/promo-accelerator-app/browser ./static

# Expose port
EXPOSE 8000

# Set environment variable for production
ENV ENVIRONMENT=production

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
