from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# SQLite 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///./crypto_trader.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 사용자 모델
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    balance = Column(Float, default=1000000.0)  # 초기 가상 자금 100만 달러
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)  # SQLite는 Boolean 대신 Integer 사용
    
    # 관계 설정
    portfolios = relationship("Portfolio", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

# 포트폴리오 모델
class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)  # 예: BTCUSDC
    quantity = Column(Float, default=0.0)  # 보유 수량
    avg_price = Column(Float, default=0.0)  # 평균 매입가
    total_invested = Column(Float, default=0.0)  # 총 투자금액
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    user = relationship("User", back_populates="portfolios")

# 거래 내역 모델
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)  # 예: BTCUSDC
    transaction_type = Column(String, nullable=False)  # 'BUY' or 'SELL'
    quantity = Column(Float, nullable=False)  # 거래 수량
    price = Column(Float, nullable=False)  # 거래 당시 가격
    total_amount = Column(Float, nullable=False)  # 총 거래 금액
    fee = Column(Float, default=0.0)  # 거래 수수료 (0.1%)
    status = Column(String, default="COMPLETED")  # PENDING, COMPLETED, CANCELLED
    notes = Column(Text, nullable=True)  # 거래 메모
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    user = relationship("User", back_populates="transactions")

# 데이터베이스 테이블 생성
def create_tables():
    Base.metadata.create_all(bind=engine)

# 데이터베이스 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 초기 데이터베이스 설정
if __name__ == "__main__":
    create_tables()
    print("✅ 데이터베이스 테이블이 생성되었습니다.")
