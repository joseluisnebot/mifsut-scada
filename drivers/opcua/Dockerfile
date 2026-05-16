FROM python:3.11-slim
WORKDIR /app
COPY opcua/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY base_driver.py .
COPY opcua/main.py .
CMD ["python", "main.py"]
