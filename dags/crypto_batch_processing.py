from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta, timezone
import requests
import json
import logging
import redis

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.now(timezone(timedelta(hours = 9))),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'crypto_data',
    default_args = default_args,
    description = 'Crypto Data DAG',
    schedule_interval = '0 0 * * *',
)

def _reset_data():
    pool = redis.ConnectionPool(host = 'redis', port = 6379, db = 0)
    r = redis.Redis(connection_pool = pool)

    r.ping()

    r.flushdb()

def _model_train():
    pass

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

model_train >> reset_data