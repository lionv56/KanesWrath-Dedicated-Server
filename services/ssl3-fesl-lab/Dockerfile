ARG LAB_BASE=python:3.12-slim
FROM ${LAB_BASE}
USER root
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /lab
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py bootstrap.py test_lab.py ./
USER 65534:65534
CMD ["python", "test_lab.py"]
