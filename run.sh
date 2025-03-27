#!/bin/bash
echo "Running server"
PORT=${PORT:-8000}

# Navigate to the project directory if not already there
cd "$(dirname "$0")"

# Set the environment variable for Django's settings module
export DJANGO_SETTINGS_MODULE=mysite.settings

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the Gunicorn server using the WSGI application
echo "Starting gunicorn server..."
gunicorn mysite.wsgi:application --bind 0.0.0.0:$PORT
