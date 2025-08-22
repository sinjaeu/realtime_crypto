FROM apache/airflow:2.8.1

# requirements.txt 복사 및 설치
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# 사용자 권한 복원
USER airflow
