FROM python:3.12.6-slim

RUN apt-get update

WORKDIR /Feedback-Bot/bin

COPY ./requirements.txt /Feedback-Bot/bin/requirements.txt
RUN pip install -r requirements.txt

COPY . /Feedback-Bot/bin

ENTRYPOINT ["python3", "-B", "-m", "app"]
