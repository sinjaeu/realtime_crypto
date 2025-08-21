#!/usr/bin/env python3
"""
Redis 데이터 확인 스크립트
실시간으로 저장되는 암호화폐 데이터를 모니터링합니다.
"""

import redis
import json
import time
from datetime import datetime

def connect_redis():
    """Redis 연결"""
    try:
        pool = redis.ConnectionPool(host='localhost', port=16379, db=0)
        r = redis.Redis(connection_pool=pool)
        r.ping()
        print("✅ Redis 연결 성공!")
        return r
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}")
        return None

def safe_decode(data):
    """데이터를 안전하게 디코딩"""
    if isinstance(data, bytes):
        return data.decode('utf-8')
    return str(data)

def check_redis_data(r):
    """Redis 데이터 확인"""
    try:
        # 데이터베이스 크기 확인
        db_size = r.dbsize()
        print(f"📊 데이터베이스 크기: {db_size}개 키")
        
        # 현재 가격 데이터 확인
        current_prices = r.hgetall("current_prices")
        if current_prices:
            print(f"💰 현재 가격 데이터: {len(current_prices)}개 심볼")
            # USDC 심볼만 표시 (처음 5개)
            usdc_symbols = []
            for k, v in current_prices.items():
                symbol = safe_decode(k)
                if symbol.endswith('USDC'):
                    usdc_symbols.append((symbol, safe_decode(v)))
            
            for symbol, price in usdc_symbols[:5]:
                print(f"  {symbol}: ${price}")
        else:
            print("❌ 현재 가격 데이터가 없습니다.")
        
        # 가격 히스토리 확인
        history_keys = r.keys("price_history:*")
        if history_keys:
            print(f"📈 가격 히스토리: {len(history_keys)}개 심볼")
            # 첫 번째 심볼의 히스토리 확인
            first_key = safe_decode(history_keys[0])
            first_symbol = first_key.replace('price_history:', '')
            history_length = r.llen(f"price_history:{first_symbol}")
            print(f"  {first_symbol}: {history_length}개 가격 데이터")
            
            # 최근 3개 가격 표시
            recent_prices = r.lrange(f"price_history:{first_symbol}", 0, 2)
            decoded_prices = [safe_decode(p) for p in recent_prices]
            print(f"  최근 가격: {decoded_prices}")
        else:
            print("❌ 가격 히스토리가 없습니다.")
        
        # 마지막 업데이트 시간 확인
        last_updates = r.hgetall("last_update")
        if last_updates:
            print(f"🕐 마지막 업데이트: {len(last_updates)}개 심볼")
            # 첫 번째 심볼의 업데이트 시간
            first_key = safe_decode(list(last_updates.keys())[0])
            timestamp = int(safe_decode(last_updates[list(last_updates.keys())[0]]))
            update_time = datetime.fromtimestamp(timestamp)
            print(f"  {first_key}: {update_time}")
        
        # 메모리 사용량 확인
        info = r.info('memory')
        used_memory = info.get('used_memory_human', 'N/A')
        print(f"💾 메모리 사용량: {used_memory}")
        
    except Exception as e:
        print(f"❌ 데이터 확인 중 에러: {e}")
        import traceback
        traceback.print_exc()

def monitor_realtime(r):
    """실시간 모니터링"""
    print("\n🔄 실시간 모니터링 시작 (Ctrl+C로 종료)...")
    try:
        while True:
            print(f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            check_redis_data(r)
            time.sleep(5)  # 5초마다 확인
    except KeyboardInterrupt:
        print("\n⏹️ 모니터링 종료")

def main():
    """메인 함수"""
    print("🔍 Redis 데이터 확인 도구")
    print("=" * 50)
    
    # Redis 연결
    r = connect_redis()
    if not r:
        return
    
    # 한 번 확인
    check_redis_data(r)
    
    # 실시간 모니터링 여부 확인
    choice = input("\n실시간 모니터링을 시작하시겠습니까? (y/n): ").lower()
    if choice == 'y':
        monitor_realtime(r)
    else:
        print("👋 종료합니다.")

if __name__ == "__main__":
    main()
