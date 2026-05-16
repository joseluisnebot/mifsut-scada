FROM python:3.11-slim
WORKDIR /app
COPY mqtt_ext/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY base_driver.py .
COPY mqtt_ext/main.py .
CMD ["python", "main.py"]
