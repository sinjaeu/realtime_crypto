from kafka import KafkaProducer
import json
import requests
import logging
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

while True:
    try:
        url = 'https://api.binance.com/api/v3/ticker/price'
        response = requests.get(url, timeout=10, verify=False)
        data = response.json()
        
        crypto_data = {}
        for item in data:
            if item['symbol'].endswith('USDC'):
                crypto_data[item['symbol']] = item['price']
        logging.info(f"📊 총 {len(crypto_data)}개의 암호화폐 데이터 수집 완료")

        prices = [float(price) for price in crypto_data.values()]
        if prices:
            logging.info(f"📈 가격 통계:")
            logging.info(f"  최고가: ${max(prices):.8f}")
            logging.info(f"  최저가: ${min(prices):.8f}")
            logging.info(f"  평균가: ${sum(prices)/len(prices):.8f}")

        producer.send("crypto-topic", value = crypto_data)
        print("✅ 데이터 전송 완료")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ API 연결 실패: {e}")
        print(f"❌ API 연결 실패: {e}")
        time.sleep(10)  # 에러 시 10초 대기
        continue
    except Exception as e:
        logging.error(f"❌ 예상치 못한 에러: {e}")
        print(f"❌ 예상치 못한 에러: {e}")
        time.sleep(10)
        continue
    
    time.sleep(5)