FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SSI_CPU_THREADS=4

WORKDIR /app

# Install a CPU-only PyTorch wheel before resolving project requirements.
RUN python -m pip install --no-cache-dir "torch==2.6.0" \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860
CMD ["uvicorn", "lab.app:app", "--host", "0.0.0.0", "--port", "7860"]
