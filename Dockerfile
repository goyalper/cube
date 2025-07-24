FROM python:3.12

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6

# Set work directory
WORKDIR /app

## Copy Python requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

## Copy Django project and application code
COPY . .

# Collect static files and apply migrations
RUN python manage.py migrate --noinput
RUN python manage.py collectstatic --noinput

# Expose port for Django
EXPOSE 8000
# Run Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
