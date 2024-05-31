FROM python:3.10
EXPOSE 5000
WORKDIR /src

# Install requirements
RUN apt-get update && apt-get -y install
COPY ./requirements.txt requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy app files
COPY app.py .
COPY patch_util.py .

ENV PYTHONUNBUFFERED=1
# CMD ["gunicorn", "--bind", "0.0.0.0:8080"]
# gunicorn doesn't like it when i spin off processes in the app (rude)
CMD ["python", "app.py"]