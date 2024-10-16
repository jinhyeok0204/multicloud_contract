FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY .env .env

# 환경 변수 설정
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Flask 애플리케이션 실행
CMD ["flask", "run", "--host=0.0.0.0"]
