# The image of the application. The web interface is the default command.
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY src ./src
COPY config ./config
# RapidOCR downloads its models at the first use. Download them now, so that the run needs no internet.
RUN PYTHONPATH=src python -c "from odw2json import ocr; ocr.engine()"

EXPOSE 8000
CMD ["python", "main.py", "--gui", "--host", "0.0.0.0"]
