# Use an official Python runtime as a parent image
FROM python:3.13-slim

#install cron
RUN apt-get update && apt-get install -y cron && apt-get clean all

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# cron file to crontab for the cron.py script
COPY app/crontab /etc/cron.d/qrCron
RUN chmod 644 /etc/cron.d/qrCron

# Expose the port Flask runs on
EXPOSE 5000

# Define environment variable for Flask
ENV FLASK_APP=app.py

# Run the Flask application
ENTRYPOINT [ "/app/app/startUp.sh" ]
###docker build -t guestqrcode .