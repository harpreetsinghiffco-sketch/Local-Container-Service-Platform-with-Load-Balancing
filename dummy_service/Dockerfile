FROM python:3.11-alpine

WORKDIR /app

COPY service.py /app/service.py

ENV PORT=9001
ENV SERVICE_ID=srv-docker
ENV SERVICE_NAME=dummy-api-service

EXPOSE 9001

CMD ["python3", "/app/service.py", "--host", "0.0.0.0", "--port", "9001", "--id", "srv-docker"]
