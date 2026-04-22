FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py db.py email_router.py agenda_router.py ./
COPY static/ ./static/

# Volume para persistir o banco SQLite entre reinicializações
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/email.db

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
