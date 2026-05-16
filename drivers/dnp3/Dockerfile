FROM python:3.11-slim
WORKDIR /app
COPY dnp3/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY base_driver.py .
COPY dnp3/main.py .
CMD ["python", "main.py"]
