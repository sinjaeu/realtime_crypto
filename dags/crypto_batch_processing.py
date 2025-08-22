from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta, timezone
from xgboost import XGBRegressor
from sklearn.model_selection import KFold, GridSearchCV, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score
import requests
import json
import logging
import redis
import pytz
import psycopg2
import os
import joblib
import pandas as pd
import numpy as np

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
    default_args=default_args,
    description='Crypto Data Batch Processing and ML Training DAG',
    schedule_interval='0 0 * * *',  # 매일 자정 실행
    catchup=False,  # 과거 실행 건너뛰기
    max_active_runs=1,  # 동시 실행 방지
    tags=['crypto', 'ml', 'xgboost'],
)

def _reset_data():
    """모델 학습 완료 후 Redis 데이터 초기화"""
    pool = redis.ConnectionPool(host='redis', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)
    
    try:
        r.ping()
        print("✅ Redis 연결 성공")
        
        # 현재 데이터 크기 확인
        db_size = r.dbsize()
        print(f"📊 초기화 전 Redis 데이터: {db_size}개 키")
        
        # 모든 데이터 초기화
        r.flushdb()
        print("🔄 Redis 데이터 초기화 완료")
        
        # 초기화 후 확인
        db_size_after = r.dbsize()
        print(f"📊 초기화 후 Redis 데이터: {db_size_after}개 키")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def _data_save():
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),           # Docker 서비스명
        port=int(os.getenv('POSTGRES_PORT', 5432)),           # 포트
        database=os.getenv('POSTGRES_DB', 'airflow'),         # 데이터베이스명
        user=os.getenv('POSTGRES_USER', 'airflow'),           # 사용자명
        password=os.getenv('POSTGRES_PASSWORD', 'airflow')     # 비밀번호
    )
    cur = conn.cursor()

def _get_redis_data(r, symbol):
    """Redis에서 시계열 데이터 가져오기 (전체 데이터)"""
    prices = r.lrange(symbol, 0, -1)  # 전체 데이터 (처음부터 끝까지)
    if prices:
        prices_str = [float(price.decode('utf-8')) for price in prices]
        return prices_str
    return []

def _data_read():
    """Redis에서 모든 코인 데이터 읽기"""
    pool = redis.ConnectionPool(host='redis', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)
    
    try:
        r.ping()
        print("✅ Redis 연결 성공")
        
        price_keys = r.keys('price_history:*')
        price_keys = [key.decode('utf-8') for key in price_keys]
        print(f"📊 총 {len(price_keys)}개 코인 데이터 발견")
        
        all_data = []
        for symbol_key in price_keys:
            data = reversed(_get_redis_data(r, symbol_key))
            symbol = symbol_key.replace('price_history:', '')
            for price in data:
                all_data.append({
                    'symbol': symbol,
                    'price': price
                })
        
        df = pd.DataFrame(all_data)
        print(f"📈 Long format 데이터 크기: {df.shape}")
        return df
        
    except Exception as e:
        print(f"❌ Redis 데이터 읽기 실패: {e}")
        return pd.DataFrame()

def _create_ml_features(df_long):
    """Long format을 ML 학습용으로 변환"""
    
    all_features = []
    
    # 심볼별로 그룹화
    for symbol in df_long['symbol'].unique():
        symbol_data = df_long[df_long['symbol'] == symbol]
        prices = symbol_data['price'].values
        
        # 윈도우 방식으로 특징 생성 (10개 → 1개 예측)
        for i in range(len(prices) - 10):
            features = {
                'symbol': symbol,
                'price_1': float(prices[i]),
                'price_2': float(prices[i+1]), 
                'price_3': float(prices[i+2]),
                'price_4': float(prices[i+3]),
                'price_5': float(prices[i+4]),
                'price_6': float(prices[i+5]),
                'price_7': float(prices[i+6]),
                'price_8': float(prices[i+7]),
                'price_9': float(prices[i+8]),
                'price_10': float(prices[i+9]),
                'target': float(prices[i+10])
            }
            all_features.append(features)
    
    df_ml = pd.DataFrame(all_features)
    print(f"🤖 ML 데이터 크기: {df_ml.shape}")
    return df_ml

def _model_train():
    """최적 파라미터로 XGBoost 모델 학습"""
    
    # 모델 파일 경로
    model_dir = 'models'
    model_file = f'{model_dir}/xgboost_best_model.pkl'
    
    try:
        # models 디렉토리 생성
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
            print(f"📁 {model_dir} 디렉토리 생성")
        
        # 1. 데이터 로드
        print("🔄 Redis에서 데이터 로딩 중...")
        df_long = _data_read()
        
        if df_long.empty:
            print("❌ 데이터가 없습니다. 학습을 종료합니다.")
            return False
            
        # 2. ML 특징 생성
        print("🔧 ML 특징 생성 중...")
        df_ml = _create_ml_features(df_long)
        
        if df_ml.empty:
            print("❌ ML 특징 생성 실패. 학습을 종료합니다.")
            return False
        
        # 3. 데이터 전처리
        print("🎯 데이터 전처리 중...")
        le = LabelEncoder()
        df_ml['symbol_encoded'] = le.fit_transform(df_ml['symbol'])
        
        # 특징 선택
        feature_cols = ['symbol_encoded', 'price_1', 'price_2', 'price_3', 
                       'price_4', 'price_5', 'price_6', 'price_7', 
                       'price_8', 'price_9', 'price_10']
        
        X = df_ml[feature_cols]
        y = df_ml['target']
        
        # 4. Train/Test 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False  # 시계열 데이터이므로 shuffle=False
        )
        
        # 5. 최적 파라미터로 모델 생성
        print("🤖 XGBoost 모델 학습 중...")
        optimal_params = {
            'booster': 'gbtree', 
            'eta': 0.1, 
            'gamma': 0, 
            'max_depth': 10, 
            'min_child_weight': 0.5, 
            'objective': 'reg:linear'
        }
        
        xgb_model = XGBRegressor(**optimal_params)
        
        # 6. 모델 학습
        xgb_model.fit(X_train, y_train)
        
        # 7. 모델 평가
        train_score = xgb_model.score(X_train, y_train)
        test_score = xgb_model.score(X_test, y_test)
        
        y_pred = xgb_model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # 8. 모델 저장
        joblib.dump(xgb_model, model_file)
        joblib.dump(le, f'{model_dir}/label_encoder.pkl')  # LabelEncoder도 저장
        
        # 9. 결과 출력
        print("🎉 모델 학습 완료!")
        print(f"📊 훈련 데이터 크기: {X_train.shape}")
        print(f"📊 테스트 데이터 크기: {X_test.shape}")
        print(f"🎯 Train R²: {train_score:.6f}")
        print(f"🎯 Test R²: {test_score:.6f}")
        print(f"📉 MSE: {mse:.2f}")
        print(f"📈 R² Score: {r2:.6f}")
        print(f"💾 모델 저장: {model_file}")
        print(f"🏷️ LabelEncoder 저장: {model_dir}/label_encoder.pkl")
        
        return True
        
    except Exception as e:
        print(f"❌ 모델 학습 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


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