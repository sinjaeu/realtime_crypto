from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import redis
import json
import requests
import joblib
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
import os

# 로컬 모듈 임포트
from database import get_db, User, Portfolio, Transaction, create_tables
from auth import (
    authenticate_user, create_access_token, get_current_user,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)
from trading import trading_service

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic 모델들
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    balance: float
    created_at: str

# 거래 관련 Pydantic 모델들
class TradeRequest(BaseModel):
    symbol: str
    quantity: float
    trade_type: str  # "BUY" or "SELL"

class AIAssistantRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class AIAssistantResponse(BaseModel):
    success: bool
    response: str
    suggestions: Optional[List[str]] = None
    timestamp: str

class TradeResponse(BaseModel):
    success: bool
    message: str
    transaction: Dict[str, Any]
    portfolio: Optional[Dict[str, Any]]
    new_balance: float
    is_active: bool

app = FastAPI(title="CryptoTrader API", version="1.0.0")

# 앱 시작 시 데이터베이스 테이블 생성
@app.on_event("startup")
def startup_event():
    create_tables()
    logger.info("✅ 데이터베이스 테이블 초기화 완료")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:3000"],
    allow_methods = ["*"],
    allow_headers = ['*'],
)

# Redis 연결 설정
def get_redis_client():
    """Redis 클라이언트 연결 (Docker 환경 고려)"""
    try:
        # Docker Compose 환경에서는 서비스명으로 접근
        redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis 연결 성공 (Docker 내부)")
        return redis_client
    except Exception as e:
        logger.warning(f"⚠️ Docker Redis 연결 실패, 로컬 시도: {e}")
        try:
            # 로컬 개발 환경에서는 localhost 사용
            redis_client = redis.Redis(host='localhost', port=16379, db=0, decode_responses=True)
            redis_client.ping()
            logger.info("✅ Redis 연결 성공 (로컬)")
            return redis_client
        except Exception as e2:
            logger.error(f"❌ Redis 연결 완전 실패: {e2}")
            return None

# 전역 Redis 클라이언트 초기화
redis_client = get_redis_client()

def safe_decode(value):
    """Redis 값을 안전하게 디코딩"""
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return value

@app.get("/api/hello")
async def hello():
    return {'message' : "Hello from FastAPI!!"}

@app.get("/api/market/prices")
async def get_market_prices():
    """현재 시장 가격 정보 조회"""
    global redis_client
    
    # Redis 연결 확인 및 재연결 시도
    if not redis_client:
        redis_client = get_redis_client()
    
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis 서버에 연결할 수 없습니다")
    
    try:
        # Redis에서 현재 가격 데이터 가져오기
        current_prices = redis_client.hgetall("current_prices")
        last_updates = redis_client.hgetall("last_update")
        
        if not current_prices:
            return {"message": "데이터가 없습니다. Producer가 실행 중인지 확인해주세요.", "data": []}
        
        market_data = []
        
        # 모든 코인 가져오기 (알파벳 순)
        symbols = sorted(current_prices.keys())
        
        for symbol in symbols:
            try:
                price = safe_decode(current_prices[symbol])
                last_update = safe_decode(last_updates.get(symbol, ""))
                
                # 실제 가격 변동률 계산
                change_percent = 0.0
                change_class = "neutral"
                change_str = "0.00%"
                
                try:
                    current_price_val = float(price)
                    
                    # 5분 변동률 계산 (5초마다 수집하므로 5분 = 60개)
                    price_history = redis_client.lrange(f"price_history:{symbol}", 0, 60)  # 5분 전 (60 * 5초 = 300초 = 5분)
                    
                    if len(price_history) >= 20:  # 최소 20개 데이터가 있을 때 (1분 40초)
                        # 가장 오래된 가격 (5분 전 또는 사용 가능한 가장 오래된 가격)
                        old_price_index = min(len(price_history) - 1, 59)  # 최대 60개째
                        old_price = float(safe_decode(price_history[old_price_index]))
                        
                        if old_price > 0:
                            # 변동률 계산
                            change_percent = round(((current_price_val - old_price) / old_price) * 100, 2)
                            change_class = "positive" if change_percent > 0 else ("negative" if change_percent < 0 else "neutral")
                            change_str = f"+{change_percent}%" if change_percent > 0 else f"{change_percent}%"
                    elif len(price_history) >= 2:
                        # 데이터가 적을 때는 단기 변동률 사용
                        previous_price = float(safe_decode(price_history[1]))
                        if previous_price > 0:
                            change_percent = round(((current_price_val - previous_price) / previous_price) * 100, 2)
                            change_class = "positive" if change_percent > 0 else ("negative" if change_percent < 0 else "neutral")
                            change_str = f"+{change_percent}%" if change_percent > 0 else f"{change_percent}%"
                        
                except (ValueError, TypeError, IndexError) as e:
                    logger.warning(f"변동률 계산 오류 - {symbol}: {e}")
                    # 오류 시 기본값
                    change_percent = 0.0
                    change_class = "neutral" 
                    change_str = "0.00%"
                
                market_data.append({
                    "symbol": symbol,
                    "price": float(price),
                    "formatted_price": f"{float(price):,.4f}",
                    "change": change_str,
                    "change_percent": change_percent,
                    "change_class": change_class,
                    "last_update": last_update
                })
                
            except (ValueError, TypeError) as e:
                logger.warning(f"데이터 파싱 오류 - {symbol}: {e}")
                continue
        
        # 가격 순으로 정렬 (높은 순)
        market_data.sort(key=lambda x: x["price"], reverse=True)
        
        return {
            "success": True,
            "data": market_data,
            "total_symbols": len(current_prices),
            "returned_symbols": len(market_data)
        }
        
    except Exception as e:
        logger.error(f"시장 데이터 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 조회 중 오류 발생: {str(e)}")

@app.get("/api/market/top-gainers")
async def get_top_gainers(limit: int = 10):
    """상승률 높은 코인 순위 조회"""
    global redis_client
    
    # Redis 연결 확인 및 재연결 시도
    if not redis_client:
        redis_client = get_redis_client()
    
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis 서버에 연결할 수 없습니다")
    
    try:
        # 현재 가격 정보
        current_prices = redis_client.hgetall("current_prices")
        last_updates = redis_client.hgetall("last_update")
        
        if not current_prices:
            return {
                "success": False,
                "message": "현재 시장 데이터를 찾을 수 없습니다",
                "data": []
            }

        gainers = []
        
        for symbol in current_prices.keys():
            try:
                price = safe_decode(current_prices[symbol])
                last_update = safe_decode(last_updates.get(symbol, ""))
                
                # 가격 변동률 계산
                change_percent = 0.0
                current_price_val = float(price)
                
                # 5분 전 가격과 비교 (60개 * 5초 = 300초 = 5분)
                price_history = redis_client.lrange(f"price_history:{symbol}", 0, 60)
                
                if len(price_history) >= 20:  # 최소 20개 데이터 (1분 40초)
                    old_price_index = min(len(price_history) - 1, 59)  # 최대 60개째
                    old_price = float(safe_decode(price_history[old_price_index]))
                    
                    if old_price > 0:
                        change_percent = ((current_price_val - old_price) / old_price) * 100
                
                # 안전한 price_history 처리 (최대 60개, 시간순 정렬)
                safe_price_history = []
                try:
                    # Redis에서 가져온 데이터를 시간순으로 정렬 (오래된 것부터)
                    raw_history = [float(safe_decode(p)) for p in price_history[:60] if p]
                    safe_price_history = list(reversed(raw_history))  # 오래된 것부터 최신 순으로
                except (ValueError, TypeError):
                    safe_price_history = []

                gainers.append({
                    "symbol": safe_decode(symbol),
                    "price": current_price_val,
                    "formatted_price": f"{current_price_val:.4f}",
                    "change_percent": change_percent,
                    "change": f"+{change_percent:.2f}%" if change_percent > 0 else f"{change_percent:.2f}%",
                    "change_class": "positive" if change_percent > 0 else ("negative" if change_percent < 0 else "neutral"),
                    "last_update": last_update,
                    "price_history": safe_price_history
                })
                
            except (ValueError, TypeError) as e:
                logger.warning(f"가격 데이터 처리 오류 - {symbol}: {e}")
                continue
        
        # 상승한 코인만 필터링 (양의 변동률, 최소 0.01% 이상)
        positive_gainers = [coin for coin in gainers if coin['change_percent'] > 0.01]
        
        # 디버그 정보 출력
        logger.info(f"전체 코인: {len(gainers)}개, 상승 코인: {len(positive_gainers)}개")
        if positive_gainers:
            top_3 = [f"{coin['symbol']}: {coin['change_percent']:.2f}%" for coin in sorted(positive_gainers, key=lambda x: x['change_percent'], reverse=True)[:3]]
            logger.info(f"상위 3개 상승률: {top_3}")
        
        # 상승률 순으로 정렬
        positive_gainers.sort(key=lambda x: x['change_percent'], reverse=True)
        
        return {
            "success": True,
            "data": positive_gainers[:limit],
            "total_symbols": len(positive_gainers),
            "total_all_symbols": len(gainers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"상위 상승 코인 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 조회 중 오류 발생: {str(e)}")

@app.get("/api/market/symbol/{symbol}")
async def get_symbol_data(symbol: str):
    """특정 심볼의 상세 정보 조회"""
    global redis_client
    
    # Redis 연결 확인 및 재연결 시도
    if not redis_client:
        redis_client = get_redis_client()
    
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis 서버에 연결할 수 없습니다")
    
    try:
        # 현재 가격
        current_price = redis_client.hget("current_prices", symbol)
        if not current_price:
            raise HTTPException(status_code=404, detail=f"심볼 '{symbol}'을 찾을 수 없습니다")
        
        # 가격 히스토리 (최근 100개)
        price_history = redis_client.lrange(f"price_history:{symbol}", 0, 99)
        last_update = redis_client.hget("last_update", symbol)
        
        # 가격 히스토리를 float로 변환
        history_floats = []
        for price in price_history:
            try:
                history_floats.append(float(safe_decode(price)))
            except (ValueError, TypeError):
                continue
        
        return {
            "success": True,
            "symbol": symbol,
            "current_price": float(safe_decode(current_price)),
            "price_history": history_floats,
            "history_length": len(history_floats),
            "last_update": safe_decode(last_update) if last_update else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"심볼 데이터 조회 오류 - {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 조회 중 오류 발생: {str(e)}")

@app.get("/api/status")
async def get_system_status():
    """시스템 상태 확인"""
    global redis_client
    
    status = {
        "api": "running",
        "redis": "disconnected",
        "data_available": False
    }
    
    # Redis 연결 확인 및 재연결 시도
    if not redis_client:
        redis_client = get_redis_client()
    
    if redis_client:
        try:
            redis_client.ping()
            status["redis"] = "connected"
            
            # 데이터 존재 여부 확인
            current_prices = redis_client.hgetall("current_prices")
            status["data_available"] = len(current_prices) > 0
            status["total_symbols"] = len(current_prices)
            
        except Exception as e:
            logger.error(f"Redis 상태 확인 오류: {e}")
    
    return status

# ===============================
# 🔐 인증 API 엔드포인트
# ===============================

@app.post("/api/auth/register", response_model=dict)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """회원가입"""
    try:
        # 중복 사용자명 확인
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 사용자명입니다"
            )
        
        # 중복 이메일 확인
        existing_email = db.query(User).filter(User.email == user.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 이메일입니다"
            )
        
        # 새 사용자 생성
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"✅ 새 사용자 등록: {user.username}")
        
        return {
            "success": True,
            "message": "회원가입이 완료되었습니다",
            "user": {
                "id": db_user.id,
                "username": db_user.username,
                "email": db_user.email,
                "balance": db_user.balance
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"회원가입 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다"
        )

@app.post("/api/auth/login", response_model=Token)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """로그인"""
    try:
        # 사용자 인증
        user = authenticate_user(db, user_credentials.username, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자명 또는 비밀번호가 올바르지 않습니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # JWT 토큰 생성
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        logger.info(f"✅ 사용자 로그인: {user.username}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "balance": user.balance,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 중 오류가 발생했습니다"
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """현재 사용자 정보 조회"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "balance": current_user.balance,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "is_active": bool(current_user.is_active)
    }

@app.post("/api/auth/logout")
async def logout_user():
    """로그아웃 (클라이언트에서 토큰 삭제)"""
    return {"message": "로그아웃되었습니다"}

@app.post("/api/auth/reset-balance")
async def reset_user_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자 잔고 및 포트폴리오 초기화"""
    try:
        # 사용자 잔고를 기본값으로 재설정
        current_user.balance = 1000000.0
        
        # 해당 사용자의 모든 거래 내역 삭제
        db.query(Transaction).filter(Transaction.user_id == current_user.id).delete()
        
        # 해당 사용자의 모든 포트폴리오 삭제 (사실상 거래 내역 기반이므로 자동 초기화됨)
        db.query(Portfolio).filter(Portfolio.user_id == current_user.id).delete()
        
        db.commit()
        
        logger.info(f"사용자 {current_user.username}의 잔고 및 포트폴리오가 초기화되었습니다.")
        
        return {
            "success": True,
            "message": "잔고와 포트폴리오가 초기화되었습니다.",
            "new_balance": current_user.balance
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"잔고 초기화 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="잔고 초기화 중 오류가 발생했습니다"
        )

# ============================================================================
# 거래 API 엔드포인트
# ============================================================================

@app.post("/api/trade/buy")
async def buy_crypto(
    trade_request: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """암호화폐 매수"""
    try:
        if trade_request.quantity <= 0:
            raise HTTPException(status_code=400, detail="수량은 0보다 커야 합니다")
        
        result = trading_service.buy_crypto(
            user=current_user,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            db=db
        )
        
        logger.info(f"매수 완료: {current_user.username} - {trade_request.symbol} {trade_request.quantity}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"매수 API 오류: {e}")
        raise HTTPException(status_code=500, detail="매수 처리 중 오류가 발생했습니다")

@app.post("/api/trade/sell")
async def sell_crypto(
    trade_request: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """암호화폐 매도"""
    try:
        if trade_request.quantity <= 0:
            raise HTTPException(status_code=400, detail="수량은 0보다 커야 합니다")
        
        result = trading_service.sell_crypto(
            user=current_user,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            db=db
        )
        
        logger.info(f"매도 완료: {current_user.username} - {trade_request.symbol} {trade_request.quantity}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"매도 API 오류: {e}")
        raise HTTPException(status_code=500, detail="매도 처리 중 오류가 발생했습니다")

@app.get("/api/portfolio")
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 포트폴리오 조회"""
    try:
        portfolio = trading_service.get_user_portfolio(user=current_user, db=db)
        return {
            "success": True,
            "data": portfolio
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"포트폴리오 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="포트폴리오 조회 중 오류가 발생했습니다")

@app.get("/api/transactions")
async def get_transactions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 거래 내역 조회"""
    try:
        transactions = trading_service.get_user_transactions(
            user=current_user, 
            db=db, 
            limit=limit
        )
        return {"transactions": transactions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"거래 내역 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="거래 내역 조회 중 오류가 발생했습니다")

# ============================================================================
# AI 어시스턴트 API 엔드포인트
# ============================================================================

@app.post("/api/ai/assistant", response_model=AIAssistantResponse)
async def ai_assistant_chat(
    request: AIAssistantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 어시스턴트와의 채팅 (기존 XGBoost 모델 활용)"""
    try:
        logger.info(f"AI 어시스턴트 요청 - 사용자: {current_user.username}, 메시지: {request.message[:50]}...")
        # 사용자의 포트폴리오와 시장 정보를 컨텍스트로 가져오기
        context_data = await get_user_context_for_ai(current_user, db)
        
        # AI 응답 생성 (기존 ML 모델 활용)
        ai_response = await generate_ai_response_with_ml(request.message, context_data)
        
        return AIAssistantResponse(
            success=True,
            response=ai_response["response"],
            suggestions=ai_response.get("suggestions", []),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"AI 어시스턴트 오류: {e}")
        return AIAssistantResponse(
            success=False,
            response="죄송합니다. 현재 AI 어시스턴트 서비스에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
            suggestions=[],
            timestamp=datetime.now().isoformat()
        )

@app.get("/api/ai/predictions/{symbol}")
async def get_price_predictions(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """특정 코인의 가격 예측 (XGBoost 모델 사용)"""
    try:
        predictions = await predict_coin_price(symbol)
        return {
            "success": True,
            "symbol": symbol,
            "predictions": predictions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"가격 예측 오류: {e}")
        raise HTTPException(status_code=500, detail="가격 예측 중 오류가 발생했습니다")

async def get_user_context_for_ai(user: User, db: Session) -> Dict[str, Any]:
    """AI를 위한 사용자 컨텍스트 정보 수집"""
    try:
        # 포트폴리오 정보
        portfolio_data = trading_service.get_user_portfolio(user, db)
        
        # 최근 거래 내역
        recent_transactions = trading_service.get_user_transactions(user, db, limit=5)
        
        # 시장 정보 (Redis에서)
        market_data = await get_market_data_for_ai()
        
        return {
            "user": {
                "balance": user.balance,
                "username": user.username
            },
            "portfolio": portfolio_data,
            "recent_transactions": recent_transactions,
            "market_data": market_data
        }
        
    except Exception as e:
        logger.error(f"AI 컨텍스트 수집 오류: {e}")
        return {"user": {"balance": user.balance, "username": user.username}}

async def get_market_data_for_ai() -> List[Dict[str, Any]]:
    """AI 분석을 위한 시장 데이터 수집"""
    try:
        global redis_client
        if not redis_client:
            logger.warning("Redis 클라이언트가 연결되지 않음")
            return []
        
        market_data = []
        # price_history 키를 사용해서 코인 목록 가져오기
        all_price_keys = redis_client.keys("price_history:*")
        logger.info(f"발견된 가격 히스토리 키: {len(all_price_keys)}개")
        
        symbols = [safe_decode(key).replace('price_history:', '') 
                  for key in all_price_keys][:50]  # 최대 50개 코인
        
        for symbol in symbols:
            try:
                # price_history에서 최신 가격과 히스토리 가져오기
                price_history = redis_client.lrange(f"price_history:{symbol}", -60, -1)
                
                if price_history and len(price_history) >= 5:  # 최소 5개 데이터 필요
                    history = [float(safe_decode(p)) for p in price_history if p]
                    current_price = history[-1] if history else None  # 가장 최신 가격
                    
                    if current_price and len(history) >= 5:  # 충분한 히스토리가 있을 때만
                        # 5분 변동률 계산 (현재가 vs 5분 전)
                        old_price = history[0] if len(history) >= 5 else history[-1]
                        change_percent = ((current_price - old_price) / old_price) * 100
                        
                        # 볼륨 추정 (가격 변동성 기반)
                        volatility = sum(abs(history[i] - history[i-1]) for i in range(1, len(history))) / len(history)
                        
                        market_data.append({
                            "symbol": symbol,
                            "price": current_price,
                            "change_percent": round(change_percent, 2),
                            "trend": "상승" if change_percent > 0.1 else "하락" if change_percent < -0.1 else "보합",
                            "volatility": round(volatility, 6),
                            "data_points": len(history),
                            "market_cap_rank": len(market_data) + 1  # 간단한 순위
                        })
            except Exception as e:
                logger.debug(f"심볼 {symbol} 데이터 처리 오류: {e}")
                continue
        
        # 변동률 기준으로 정렬하여 상위 20개 반환
        sorted_data = sorted(market_data, key=lambda x: abs(x.get('change_percent', 0)), reverse=True)
        logger.info(f"시장 데이터 수집 완료: {len(market_data)}개 코인, 상위 20개 반환")
        return sorted_data[:20]
        
    except Exception as e:
        logger.error(f"시장 데이터 수집 오류: {e}")
        return []

async def predict_coin_price(symbol: str) -> Dict[str, Any]:
    """XGBoost 모델을 사용한 코인 가격 예측"""
    try:
        # 모델 파일 경로
        model_path = "/app/models/xgboost_best_model.pkl"
        encoder_path = "/app/models/label_encoder.pkl"
        
        # 모델이 존재하지 않으면 기본 예측 반환
        if not os.path.exists(model_path) or not os.path.exists(encoder_path):
            logger.warning(f"모델 파일이 없습니다: {model_path}, {encoder_path}")
            return {
                "current_price": 0,
                "predicted_price": 0,
                "change_percent": 0,
                "trend": "unknown",
                "confidence": 0,
                "message": "모델을 학습 중입니다. 잠시 후 다시 시도해주세요."
            }
        
        # 모델 로드
        model = joblib.load(model_path)
        encoder = joblib.load(encoder_path)
        
        # Redis에서 가격 데이터 가져오기
        global redis_client
        if not redis_client:
            raise Exception("Redis 연결 없음")
            
        price_history = redis_client.lrange(f"price_history:{symbol}", 0, 10)
        logger.info(f"AI 예측 데이터 확인 - {symbol}: {len(price_history)}개 데이터")
        
        if len(price_history) < 10:
            # 전체 데이터 개수도 확인
            total_data = redis_client.llen(f"price_history:{symbol}")
            logger.warning(f"AI 예측 데이터 부족 - {symbol}: {len(price_history)}/10개, 전체: {total_data}개")
            return {
                "current_price": 0,
                "predicted_price": 0,
                "change_percent": 0,
                "trend": "unknown",
                "confidence": 0,
                "message": f"데이터 부족: {len(price_history)}/10개 (전체: {total_data}개)"
            }
        
        # 특성 데이터 준비
        prices = [float(safe_decode(p)) for p in price_history[:10]]
        prices.reverse()  # 시간순 정렬
        
        # 심볼 인코딩
        try:
            symbol_encoded = encoder.transform([symbol])[0]
        except:
            # 새로운 심볼인 경우 평균값 사용
            symbol_encoded = 0
        
        # 특성 벡터 생성 (symbol_encoded + 10개 가격)
        features = [symbol_encoded] + prices
        features_df = pd.DataFrame([features], columns=['symbol_encoded'] + [f'price_{i+1}' for i in range(10)])
        
        # 예측 수행
        prediction = model.predict(features_df)[0]
        current_price = prices[-1]
        change_percent = ((prediction - current_price) / current_price) * 100
        
        return {
            "current_price": current_price,
            "predicted_price": float(prediction),
            "change_percent": float(change_percent),
            "trend": "상승" if change_percent > 0 else "하락" if change_percent < 0 else "보합",
            "confidence": min(abs(change_percent) * 10, 100)  # 간단한 신뢰도 계산
        }
        
    except Exception as e:
        logger.error(f"가격 예측 오류 ({symbol}): {e}")
        return {
            "prediction": "예측 중 오류가 발생했습니다.",
            "confidence": 0,
            "trend": "unknown"
        }

async def generate_ai_response_with_ml(message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """ML 모델을 활용한 AI 응답 생성"""
    try:
        message_lower = message.lower()
        user_balance = context.get('user', {}).get('balance', 0)
        portfolio = context.get('portfolio', {})
        market_data = context.get('market_data', [])
        
        # 예측 관련 질문
        if any(keyword in message_lower for keyword in ['예측', '전망', '미래', '오를까', '내릴까']):
            # 포트폴리오에서 주요 코인 예측
            predictions_text = ""
            if portfolio.get('portfolios'):
                for holding in portfolio['portfolios'][:3]:  # 상위 3개만
                    symbol = holding.get('symbol', '')
                    if symbol:
                        pred = await predict_coin_price(symbol)
                        trend_emoji = "📈" if pred.get('trend') == '상승' else "📉" if pred.get('trend') == '하락' else "➡️"
                        predictions_text += f"\n{trend_emoji} **{symbol}**: {pred.get('change_percent', 0):.2f}% 예상 ({pred.get('trend', 'unknown')})"
            
            # 포트폴리오가 없으면 주요 시장 코인들을 예측
            if not predictions_text:
                # 주요 코인들 예측 (포트폴리오 유무와 관계없이)
                major_coins = ['BTCUSDC', 'ETHUSDC', 'ADAUSDC', 'DOTUSDC', 'BNBUSDC']
                available_coins = market_data[:3] if market_data else []
                
                # 시장 데이터가 있으면 그것을 사용, 없으면 주요 코인 사용
                coins_to_predict = available_coins if available_coins else [{'symbol': coin} for coin in major_coins]
                
                for coin in coins_to_predict[:3]:
                    symbol = coin.get('symbol', '')
                    if symbol:
                        pred = await predict_coin_price(symbol)
                        if pred.get('current_price'):  # 예측이 성공했을 때만
                            trend_emoji = "📈" if pred.get('trend') == '상승' else "📉" if pred.get('trend') == '하락' else "➡️"
                            predictions_text += f"\n{trend_emoji} **{symbol}**: {pred.get('change_percent', 0):.2f}% 예상 ({pred.get('trend', 'unknown')})"
            
            no_data_msg = "\n📊 예측할 수 있는 코인 데이터가 부족합니다."
            return {
                "response": f"""
🤖 **AI 가격 예측 분석**

XGBoost 머신러닝 모델 기반 예측 결과:
{predictions_text if predictions_text else no_data_msg}

⚠️ **예측 정확도 안내**
- AI 모델은 과거 데이터 기반 예측입니다
- 실제 시장은 예측과 다를 수 있습니다
- 투자 결정 시 다양한 요소를 종합적으로 고려하세요

📈 **활용 방법**
- 상승 예측 코인: 매수 타이밍 고려
- 하락 예측 코인: 손절 또는 관망
- 보합 예측 코인: 추가 분석 필요
""",
                "suggestions": [
                    "내 포트폴리오 분석해줘",
                    "리스크 관리 방법 알려줘",
                    "상승률 높은 코인 추천해줘"
                ]
            }
        
        # 포트폴리오 분석
        elif any(keyword in message_lower for keyword in ['포트폴리오', '자산', '보유', '분석']):
            return await generate_portfolio_analysis_with_ml(portfolio, user_balance)
        
        # 추천 관련
        elif any(keyword in message_lower for keyword in ['추천', '코인', '매수', '투자']):
            return await generate_investment_recommendations(market_data, user_balance)
        
        # 기본 응답 (시장 데이터 부족 시에도 유용한 정보 제공)
        else:
            return generate_default_ai_response(user_balance, portfolio, market_data)
            
    except Exception as e:
        logger.error(f"ML AI 응답 생성 오류: {e}")
        return {
            "response": "죄송합니다. AI 분석 중 오류가 발생했습니다.",
            "suggestions": []
        }

async def generate_portfolio_analysis_with_ml(portfolio: Dict[str, Any], user_balance: float) -> Dict[str, Any]:
    """ML 기반 포트폴리오 분석"""
    total_assets = portfolio.get('total_assets', 0)
    holding_count = portfolio.get('holding_count', 0)
    profit_loss = portfolio.get('total_profit_loss', 0)
    
    if holding_count == 0:
        return {
            "response": f"""
🤖 **포트폴리오 AI 분석**

현재 보유 자산이 없습니다.
- 현재 잔고: ${user_balance:,.2f}
- 투자 준비 완료! 🚀

🧠 **AI 투자 제안**
1. 분산 투자로 리스크 감소
2. 주요 코인(BTC, ETH)부터 시작
3. 총 자산의 5-10%씩 분할 투자

📊 **추천 전략**
- 상승률 TOP에서 모멘텀 강한 코인 확인
- AI 예측 기능으로 향후 전망 분석
- 점진적 매수로 평단가 관리
""",
            "suggestions": [
                "코인 가격 예측해줘",
                "상승률 높은 코인 추천해줘",
                "투자 전략 알려줘"
            ]
        }
    
    # ML 예측으로 각 보유 코인 분석
    analysis_text = ""
    for holding in portfolio.get('portfolios', [])[:5]:
        symbol = holding.get('symbol', '')
        quantity = holding.get('quantity', 0)
        avg_price = holding.get('avg_price', 0)
        current_value = holding.get('current_value', 0)
        
        if symbol:
            pred = await predict_coin_price(symbol)
            trend_emoji = "📈" if pred.get('trend') == '상승' else "📉" if pred.get('trend') == '하락' else "➡️"
            analysis_text += f"\n{trend_emoji} **{symbol}**: {quantity:.4f}개 보유, AI 예측 {pred.get('change_percent', 0):+.2f}%"
    
    profit_pct = (profit_loss / (total_assets - profit_loss)) * 100 if total_assets > profit_loss else 0
    status = "수익" if profit_loss > 0 else "손실" if profit_loss < 0 else "보합"
    
    return {
        "response": f"""
🤖 **AI 포트폴리오 분석**

💰 **현재 상태**
- 총 자산: ${total_assets:,.2f}
- 보유 코인: {holding_count}개
- 손익: ${profit_loss:,.2f} ({profit_pct:+.2f}%) - {status}
- 현금: ${user_balance:,.2f}

🧠 **AI 보유 코인 분석**
{analysis_text if analysis_text else "분석할 보유 코인이 없습니다."}

📊 **AI 추천 액션**
{"🎉 수익 실현 타이밍을 고려해보세요!" if profit_loss > 0 else "📉 추가 매수 또는 손절을 신중히 고려하세요." if profit_loss < 0 else "📊 시장 동향을 지켜보며 기회를 노려보세요."}
""",
        "suggestions": [
            "코인 가격 예측해줘",
            "리스크 관리 방법",
            "매수/매도 타이밍"
        ]
    }

async def generate_investment_recommendations(market_data: List[Dict], user_balance: float) -> Dict[str, Any]:
    """AI 기반 투자 추천"""
    recommendations = ""
    
    # 상위 변동성 코인들에 대한 AI 예측
    for i, coin in enumerate(market_data[:3], 1):
        symbol = coin.get('symbol', '')
        current_trend = coin.get('trend', 'unknown')
        change_pct = coin.get('change_percent', 0)
        
        if symbol:
            pred = await predict_coin_price(symbol)
            ai_trend = pred.get('trend', 'unknown')
            ai_change = pred.get('change_percent', 0)
            
            trend_match = "✅" if current_trend == ai_trend else "⚠️"
            recommendations += f"\n{i}. **{symbol}** {trend_match}\n"
            recommendations += f"   현재: {change_pct:+.2f}% ({current_trend})\n"
            recommendations += f"   AI 예측: {ai_change:+.2f}% ({ai_trend})\n"
    
    return {
        "response": f"""
🤖 **AI 투자 추천 분석**

🧠 **머신러닝 기반 분석**
{recommendations if recommendations else "분석할 시장 데이터가 부족합니다."}

💡 **AI 투자 전략**
1. **트렌드 일치**: 현재 상승 + AI 상승 예측 = 강한 매수 신호
2. **역방향 기회**: 현재 하락 + AI 상승 예측 = 저점 매수 기회
3. **주의 신호**: 현재 상승 + AI 하락 예측 = 수익 실현 고려

⚠️ **투자 원칙**
- 총 자산의 5-10%씩 분산 투자
- AI 예측과 기술적 분석 병행
- 감정보다는 데이터 기반 결정

💰 **투자 가능 금액**: ${user_balance:,.2f}
""",
        "suggestions": [
            "특정 코인 예측해줘",
            "포트폴리오 분석해줘",
            "리스크 관리 방법"
        ]
    }

def generate_default_ai_response(user_balance: float, portfolio: Dict, market_data: List) -> Dict[str, Any]:
    """기본 AI 응답 (시장 데이터 부족 시에도 유용한 정보 제공)"""
    
    # 시장 데이터 상태 확인
    data_status = f"📊 {len(market_data)}개 코인 실시간 분석 중" if market_data else "⚠️ 시장 데이터 수집 중..."
    portfolio_count = portfolio.get('holding_count', len(portfolio.get('portfolios', [])))
    
    # 기본 조언 제공
    basic_advice = ""
    if user_balance < 10000:
        basic_advice = "\n💡 **초보자 가이드**: 소액부터 시작해서 경험을 쌓아보세요!"
    elif user_balance > 100000:
        basic_advice = "\n💡 **고액 투자자**: 분산 투자로 리스크를 관리하세요!"
    
    return {
        "response": f"""
🤖 **암호화폐 AI 어시스턴트**

안녕하세요! XGBoost 머신러닝 모델을 활용한 AI 투자 어시스턴트입니다.

💰 **현재 상태**
- 잔고: ${user_balance:,.2f}
- 포트폴리오: {portfolio_count}개 코인 보유
- {data_status}
{basic_advice}

🧠 **AI 기능**
- 🔮 가격 예측: XGBoost 모델 기반 향후 가격 전망
- 📈 포트폴리오 분석: 보유 자산 AI 분석 
- 🎯 투자 추천: 시장 데이터 + AI 예측 결합
- ⚖️ 리스크 관리: 손실 최소화 전략

🔍 **질문 예시**
- "주요 코인 가격 예측해줘" (포트폴리오 없어도 가능!)
- "내 포트폴리오 분석해줘"
- "지금 투자하기 좋은 코인은?"
- "리스크 관리 방법 알려줘"

⚠️ **면책 조항**: AI 예측은 참고용이며, 투자 결정은 본인 책임입니다.
""",
        "suggestions": [
            "주요 코인 가격 예측해줘",
            "포트폴리오 분석해줘", 
            "지금 투자하기 좋은 코인은?",
            "리스크 관리 방법 알려줘"
        ]
    }

# AI 어시스턴트 테스트 API
@app.get("/api/ai/test")
async def test_ai_auth(current_user: User = Depends(get_current_user)):
    """AI 어시스턴트 인증 테스트"""
    return {
        "success": True,
        "message": f"AI 어시스턴트 인증 성공! 사용자: {current_user.username}",
        "user_id": current_user.id,
        "username": current_user.username
    }

@app.get("/api/ai/debug/{symbol}")
async def debug_coin_data(symbol: str, current_user: User = Depends(get_current_user)):
    """코인 데이터 디버그 정보"""
    try:
        global redis_client
        if not redis_client:
            return {"error": "Redis 연결 없음"}
        
        # 전체 데이터 개수
        total_count = redis_client.llen(f"price_history:{symbol}")
        
        # 최근 10개 데이터
        recent_data = redis_client.lrange(f"price_history:{symbol}", 0, 9)
        
        # 키 존재 여부
        key_exists = redis_client.exists(f"price_history:{symbol}")
        
        # 현재 가격
        current_price = redis_client.get(f"current_prices:{symbol}")
        
        return {
            "symbol": symbol,
            "total_data_count": total_count,
            "recent_data_count": len(recent_data),
            "key_exists": bool(key_exists),
            "current_price": safe_decode(current_price) if current_price else None,
            "recent_prices": [safe_decode(p) for p in recent_data[:5]] if recent_data else [],
            "redis_keys_sample": [key.decode('utf-8') for key in redis_client.keys("price_history:*")[:5]]
        }
        
    except Exception as e:
        logger.error(f"코인 데이터 디버그 오류: {e}")
        return {"error": str(e)}

# 보호된 라우트 예제
@app.get("/api/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    """인증이 필요한 보호된 라우트"""
    return {
        "message": f"안녕하세요, {current_user.username}님!",
        "user_id": current_user.id,
        "balance": current_user.balance
    }
