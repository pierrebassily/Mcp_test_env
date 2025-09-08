FROM python:3.10-slim
WORKDIR /app
COPY ../requirements.txt ./
COPY . .
RUN pip install --no-cache-dir -r requirements.txt gradio
CMD ["python", "client.py"]
