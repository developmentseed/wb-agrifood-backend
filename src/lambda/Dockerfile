FROM python:3.11-slim 

ENV LANG en_US.utf8

WORKDIR /asset

COPY . .

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt -t .
