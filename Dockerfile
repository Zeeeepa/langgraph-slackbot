# Use multi-stage build for efficiency
# Stage 1: Build the frontend
FROM node:16-alpine as frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the backend and combine with frontend
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY projector/ /app/projector/

# Copy frontend build from the first stage
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Set environment variables
ENV PYTHONPATH=/app
ENV FRONTEND_BUILD_DIR=/app/frontend/build

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "projector.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
