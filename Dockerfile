FROM python:3.12

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y libgl1-mesa-glx

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ ./

# Expose port for Flask
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
