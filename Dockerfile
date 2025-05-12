FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and set permissions for NLTK data directory
RUN mkdir -p /usr/local/share/nltk_data && \
    chmod -R 777 /usr/local/share/nltk_data

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==21.2.0

# Copy project
COPY . .

# Create static directory
RUN mkdir -p /app/staticfiles

# Set environment variable for Django
ENV DJANGO_SETTINGS_MODULE=jobportal.settings

# Generate migrations, apply them, and run the server
CMD python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn jobportal.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120

