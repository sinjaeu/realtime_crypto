from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta, timezone
import requests
import json
import logging

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.now(timezone.utc),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(seconds=5),
}

dag = DAG(
    'crypto_data',
    default_args = default_args,
    description = 'Crypto Data DAG',
    schedule_interval = timedelta(seconds=5),
)

