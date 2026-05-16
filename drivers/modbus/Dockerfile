FROM python:3.11-slim
WORKDIR /app
COPY modbus/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY base_driver.py .
COPY modbus/main.py .
CMD ["python", "main.py"]
