# The image of the application. The web interface is the default command.
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY src ./src
COPY config ./config

EXPOSE 8000
CMD ["python", "main.py", "--gui", "--host", "0.0.0.0"]
