FROM python:3.12-slim

WORKDIR /srv

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY models models
COPY data data
COPY simulation simulation
COPY financial financial

ENV PYTHONPATH=/srv/backend:/srv
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
