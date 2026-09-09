FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements-lock.txt
COPY app ./app
COPY static ./static
# Warm model initialization during the build verifies bundled model availability.
RUN python -c "from rapidocr_onnxruntime import RapidOCR; RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)"
RUN useradd --create-home --uid 10001 scanpilot
USER scanpilot
EXPOSE 8080
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8080","--workers","1","--limit-concurrency","8","--no-access-log"]
