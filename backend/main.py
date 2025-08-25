from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
import redis
import json
from typing import List, Dict, Any, Optional
import logging

# 로컬 모듈 임포트
from database import get_db, User, create_tables
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
                    
                    # 24시간 변동률 계산 (5초마다 수집하므로 24시간 = 17280개)
                    # 실제로는 현재 데이터량에 맞춰 조정
                    price_history = redis_client.lrange(f"price_history:{symbol}", 0, 288)  # 24분 전 (288 * 5초 = 1440초 = 24분)
                    
                    if len(price_history) >= 100:  # 최소 100개 데이터가 있을 때
                        # 가장 오래된 가격 (24분 전 또는 사용 가능한 가장 오래된 가격)
                        old_price_index = min(len(price_history) - 1, 287)  # 최대 288개째
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
        return portfolio
        
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

# 보호된 라우트 예제
@app.get("/api/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    """인증이 필요한 보호된 라우트"""
    return {
        "message": f"안녕하세요, {current_user.username}님!",
        "user_id": current_user.id,
        "balance": current_user.balance
    }
