from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta, timezone
from xgboost import XGBRegressor
from sklearn.model_selection import KFold, GridSearchCV
import requests
import json
import logging
import redis
import pytz
import psycopg2
import os
import joblib

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
    file_name = 'xgboost_regressor_model'
    file_dir = f'models/{file_name}.pkl'

    if os.path.exists(file_dir):
        try:
            with open(file_dir, 'rb') as f:
                xgb_model = joblib.load(f)
            print(f"모델 로드 완료: {file_dir}")
            
        except Exception as e:
            print(f"모델 로드 실패: {e}")
            xgb_model = None
    else:
        print(f"모델 파일 없음: {file_dir}")
        xgb_model = XGBRegressor()
        param_grid = {
            'booster' : ['gbtree'],
            'slient' : [1],
            'eta' : [0.01, 0.05, 0.1, 0.2],
            'max_depth' : [3, 5, 10],
            'min_child_weight' : [0.5, 1, 2],
            'gamma' : [0, 1, 2, 3],
            'objective' : ['reg:linear']
        }

        cv = KFold(n_splits = 6, random_state = 1)
        gsc = GridSearchCV(xgb_model, param_grid = param_grid, cv = cv, scoring = 'neg_mean_squared_error', n_jobs = 4)
        # gsc.fit()

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