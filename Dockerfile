FROM python:3.12-slim

# this needs to match the directory/package name of the python app
COPY . /fotos
WORKDIR /fotos
RUN mkdir -p /fotos/log

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 8002 available to the world outside this container
EXPOSE 8002

# Define environment variables here
# args are passed it from cli or docker-compose.yml

# Run gunicorn when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:8002", "fotos:app"]
