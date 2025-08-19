from kafka import KafkaConsumer
import json
import redis
import time

pool = redis.ConnectionPool(host = 'redis', port = 6379, db = 0)
r = redis.Redis(connection_pool = pool)

consumer = KafkaConsumer(
    'crypto-topic',
    bootstrap_servers=['kafka:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='my-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

for message in consumer:
    timestamp = int(time.time())
    data = message.value
    
    for symbol, price in data.items():
        r.lpush(f"price_history:{symbol}", price)
        
        # 현재 가격 (Hash 구조)
        r.hset("current_prices", symbol, price)
        r.hset("last_update", symbol, timestamp)