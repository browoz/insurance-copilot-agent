FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data/sample ./data/sample
COPY docs ./docs
COPY mcp_server.py .
COPY README.md .

ENV PYTHONPATH=/app/app
EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
