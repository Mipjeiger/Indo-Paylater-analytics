FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Install Feast and its dependencies
RUN pip install --no-cache-dir feast>=0.50.0

# Copy source code for Feast service (placeholder)
WORKDIR /workspace

CMD ["feast", "-c", "app/feast", "serve", "--host", "0.0.0.0", "--port", "6566"]