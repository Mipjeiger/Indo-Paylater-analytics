FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev gcc

# Install Feast with all required database extras and full gRPC reflection support
WORKDIR /workspace

# Set the PYTHONPATH to include the workspace directory
ENV PYTHONPATH=/workspace

# Dependencies for Feast and gRPC
RUN pip install --no-cache-dir \
    "feast[postgres,redis]>=0.41.0" \
    psycopg2-binary \
    redis \
    grpcio \
    grpcio-tools \
    grpcio-health-checking \
    grpcio-reflection

CMD ["feast", "-c", "app/feast", "serve", "--host", "0.0.0.0", "--port", "6566"]