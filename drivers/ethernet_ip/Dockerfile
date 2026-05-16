FROM python:3.11-slim
WORKDIR /app
COPY ethernet_ip/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY base_driver.py .
COPY ethernet_ip/main.py .
CMD ["python", "main.py"]
