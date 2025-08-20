from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta, timezone
import requests
import json
import logging
import redis
import pytz
import psycopg2
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.now(pytz.timezone('Asia/Seoul')),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'crypto_batch_processing',
    default_args = default_args,
    description = 'Crypto Data DAG',
    schedule_interval = '0 0 * * *',
)

def _reset_data():
    pool = redis.ConnectionPool(host = 'redis', port = 6379, db = 0)
    r = redis.Redis(connection_pool = pool)

    r.ping()

    r.flushdb()

def _data_save():
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),           # Docker 서비스명
        port=int(os.getenv('POSTGRES_PORT', 5432)),           # 포트
        database=os.getenv('POSTGRES_DB', 'airflow'),         # 데이터베이스명
        user=os.getenv('POSTGRES_USER', 'airflow'),           # 사용자명
        password=os.getenv('POSTGRES_PASSWORD', 'airflow')     # 비밀번호
    )
    cur = conn.cursor()

def _model_train():
    print("안녕")

reset_data = PythonOperator(
    task_id = 'reset_data',
    python_callable = _reset_data,
    dag = dag
)

model_train = PythonOperator(
    task_id = 'model_train',
    python_callable = _model_train,
    dag = dag
)

reset_data >> model_train