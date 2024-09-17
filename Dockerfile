FROM python:3.10.5

RUN apt-get update && apt-get install -y locales && \
    locale-gen pt_BR.UTF-8 && \
    dpkg-reconfigure locales

WORKDIR /app

COPY requirements.txt /app

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
