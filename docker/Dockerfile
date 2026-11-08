ARG PYTHON_BASE=python:3.12-slim
FROM ${PYTHON_BASE}

WORKDIR /app

COPY scripts/worker.py /app/worker.py
COPY scripts/test_readonly.py /app/test_readonly.py

RUN chmod +x /app/worker.py /app/test_readonly.py

CMD ["python", "--version"]
