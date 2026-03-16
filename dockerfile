FROM python:3.14-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY bot.py .
COPY config.py .
COPY models.py .
COPY payloads.py .
COPY __init__.py .

# Install build dependencies and package
RUN pip install --no-cache-dir --upgrade pip==24.3.1 setuptools==75.6.0 wheel==0.45.1 && \
    pip install --no-cache-dir .

EXPOSE 7777

CMD ["python", "bot.py"]
