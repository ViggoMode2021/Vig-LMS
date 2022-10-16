# Python image base
FROM python:3.8.3-slim

# Run commands to update Linux and install necessary dependencies for psycopg2 (PostgreSQL database adapter for Python)

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2

# Copy to working directory

WORKDIR /application
COPY . .

# Pip install requirements.txt
RUN pip install -r requirements.txt
ENTRYPOINT [ "python" ]

# Expose port 80 for container
EXPOSE 5000

# Run application.py file at startup
CMD [ "app.py" ]
