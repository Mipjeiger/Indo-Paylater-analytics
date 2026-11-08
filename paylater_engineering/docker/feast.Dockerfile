FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Install Feast and its dependencies
RUN pip install --no-cache-dir feast==0.41.0

# Copy source code for Feast service (placeholder)
WORKDIR /app
COPY . /app

CMD ["python", "-m", "feast", "serve", "--config", "app/feast/feature_store.yaml"]
