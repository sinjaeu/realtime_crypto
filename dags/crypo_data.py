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

def get_crypto_data():
    url = 'https://api.binance.com/api/v3/ticker/price'
    response = requests.get(url)
    data = response.json()
    
    crypto_data = {}
    for item in data:
        crypto_data[item['symbol']] = item['price']
    
    # 전체 데이터 개수 확인
    logging.info(f"📊 총 {len(crypto_data)}개의 암호화폐 데이터 수집 완료")
    
    # 주요 코인들만 선택적으로 출력
    major_coins = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT']
    logging.info("🔥 주요 코인 가격:")
    for symbol in major_coins:
        if symbol in crypto_data:
            logging.info(f"  💰 {symbol}: ${crypto_data[symbol]}")
    
    # 가격 범위 통계
    prices = [float(price) for price in crypto_data.values()]
    if prices:
        logging.info(f"📈 가격 통계:")
        logging.info(f"  최고가: ${max(prices):.8f}")
        logging.info(f"  최저가: ${min(prices):.8f}")
        logging.info(f"  평균가: ${sum(prices)/len(prices):.8f}")
    
    return crypto_data

def save_crypto_data(**context):
    # 이전 태스크에서 crypto_data 가져오기
    crypto_data = context['task_instance'].xcom_pull(task_ids='get_crypto_data')
    
    if not crypto_data:
        logging.error("❌ crypto_data를 가져올 수 없습니다!")
        return
    
    # 현재 시간
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # JSON 파일로 저장
    filename = f'/tmp/crypto_data_{current_time}.json'
    with open(filename, 'w') as f:
        json.dump(crypto_data, f, indent=2)
    
    logging.info(f"💾 데이터 저장 완료: {filename}")
    logging.info(f"📂 저장된 데이터 개수: {len(crypto_data)}개")
    
    # 파일 크기 확인
    import os
    file_size = os.path.getsize(filename)
    logging.info(f"📏 파일 크기: {file_size:,} bytes")
    
    return filename

# 중복 정의 제거됨 - 아래쪽에 새로운 정의 사용

def analyze_crypto_data(**context):
    # 이전 태스크에서 crypto_data 가져오기
    crypto_data = context['task_instance'].xcom_pull(task_ids='get_crypto_data')
    
    if not crypto_data:
        logging.error("❌ crypto_data를 가져올 수 없습니다!")
        return
    
    # 상위 10개 가장 비싼 코인
    sorted_coins = sorted(crypto_data.items(), key=lambda x: float(x[1]), reverse=True)
    logging.info("🏆 상위 10개 고가 코인:")
    for i, (symbol, price) in enumerate(sorted_coins[:10]):
        logging.info(f"  {i+1}. {symbol}: ${price}")
    
    # USDT 거래쌍만 필터링
    usdt_pairs = {k: v for k, v in crypto_data.items() if k.endswith('USDT')}
    logging.info(f"💵 USDT 거래쌍: {len(usdt_pairs)}개")
    
    # 가격 변동 분석 (간단한 예시)
    btc_price = float(crypto_data.get('BTCUSDT', 0))
    eth_price = float(crypto_data.get('ETHUSDT', 0))
    if btc_price > 0 and eth_price > 0:
        eth_btc_ratio = eth_price / btc_price
        logging.info(f"📊 ETH/BTC 비율: {eth_btc_ratio:.6f}")
    
    return {
        'total_coins': len(crypto_data),
        'usdt_pairs': len(usdt_pairs),
        'btc_price': btc_price,
        'eth_price': eth_price
    }

# 태스크 정의
get_crypto_data_task = PythonOperator(
    task_id='get_crypto_data',
    python_callable=get_crypto_data,
    dag=dag,
)

save_crypto_data_task = PythonOperator(
    task_id='save_crypto_data',
    python_callable=save_crypto_data,
    dag=dag,
)

analyze_crypto_data_task = PythonOperator(
    task_id='analyze_crypto_data',
    python_callable=analyze_crypto_data,
    dag=dag,
)

# 태스크 실행 순서
get_crypto_data_task >> [save_crypto_data_task, analyze_crypto_data_task]
    