from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db, User, Portfolio, Transaction
from auth import get_current_user
import redis
import json
from typing import Dict, Any
import logging

# Redis 클라이언트 설정
def get_redis_client():
    try:
        client = redis.Redis(host='redis', port=6379, decode_responses=True)
        client.ping()
        return client
    except:
        try:
            client = redis.Redis(host='localhost', port=16379, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            logging.error(f"Redis 연결 실패: {e}")
            return None

redis_client = get_redis_client()

class TradingService:
    def __init__(self):
        self.trading_fee_rate = 0.001  # 0.1% 거래 수수료
    
    def get_current_price(self, symbol: str) -> float:
        """Redis에서 현재 가격 조회"""
        try:
            if not redis_client:
                raise HTTPException(status_code=503, detail="Redis 연결 불가")
            
            price_data = redis_client.hget("current_prices", symbol)
            if not price_data:
                raise HTTPException(status_code=404, detail=f"심볼 {symbol}의 가격 정보를 찾을 수 없습니다")
            
            return float(price_data)
        except Exception as e:
            logging.error(f"가격 조회 오류: {e}")
            raise HTTPException(status_code=500, detail="가격 조회 실패")
    
    def calculate_fee(self, amount: float) -> float:
        """거래 수수료 계산"""
        return amount * self.trading_fee_rate
    
    def buy_crypto(self, 
                   user: User, 
                   symbol: str, 
                   quantity: float, 
                   db: Session) -> Dict[str, Any]:
        """암호화폐 매수"""
        try:
            # 현재 가격 조회
            current_price = self.get_current_price(symbol)
            
            # 총 필요 금액 계산 (수수료 포함)
            total_cost = quantity * current_price
            fee = self.calculate_fee(total_cost)
            total_amount = total_cost + fee
            
            # 잔고 확인
            if user.balance < total_amount:
                raise HTTPException(
                    status_code=400, 
                    detail=f"잔고 부족: 필요 금액 ${total_amount:.2f}, 보유 잔고 ${user.balance:.2f}"
                )
            
            # 포트폴리오 업데이트 또는 생성
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == user.id,
                Portfolio.symbol == symbol
            ).first()
            
            if portfolio:
                # 기존 포트폴리오 업데이트 (평균 매입가 계산)
                total_quantity = portfolio.quantity + quantity
                total_investment = portfolio.total_invested + total_cost
                new_avg_price = total_investment / total_quantity if total_quantity > 0 else current_price
                
                portfolio.quantity = total_quantity
                portfolio.avg_price = new_avg_price
                portfolio.total_invested = total_investment
            else:
                # 새 포트폴리오 생성
                portfolio = Portfolio(
                    user_id=user.id,
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=current_price,
                    total_invested=total_cost
                )
                db.add(portfolio)
            
            # 거래 내역 저장
            transaction = Transaction(
                user_id=user.id,
                symbol=symbol,
                transaction_type="BUY",
                quantity=quantity,
                price=current_price,
                total_amount=total_cost,
                fee=fee,
                status="COMPLETED"
            )
            db.add(transaction)
            
            # 사용자 잔고 업데이트
            user.balance -= total_amount
            
            # 데이터베이스 커밋
            db.commit()
            db.refresh(portfolio)
            db.refresh(transaction)
            db.refresh(user)
            
            return {
                "success": True,
                "message": f"{symbol} {quantity}개 매수 완료",
                "transaction": {
                    "id": transaction.id,
                    "symbol": symbol,
                    "type": "BUY",
                    "quantity": quantity,
                    "price": current_price,
                    "total_cost": total_cost,
                    "fee": fee,
                    "total_amount": total_amount
                },
                "portfolio": {
                    "symbol": symbol,
                    "quantity": portfolio.quantity,
                    "avg_price": portfolio.avg_price,
                    "total_invested": portfolio.total_invested
                },
                "new_balance": user.balance
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logging.error(f"매수 오류: {e}")
            raise HTTPException(status_code=500, detail="매수 처리 실패")
    
    def sell_crypto(self, 
                    user: User, 
                    symbol: str, 
                    quantity: float, 
                    db: Session) -> Dict[str, Any]:
        """암호화폐 매도"""
        try:
            # 포트폴리오 확인
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == user.id,
                Portfolio.symbol == symbol
            ).first()
            
            if not portfolio or portfolio.quantity < quantity:
                available_qty = portfolio.quantity if portfolio else 0
                raise HTTPException(
                    status_code=400, 
                    detail=f"보유 수량 부족: 매도 요청 {quantity}개, 보유 수량 {available_qty}개"
                )
            
            # 현재 가격 조회
            current_price = self.get_current_price(symbol)
            
            # 매도 금액 계산
            total_revenue = quantity * current_price
            fee = self.calculate_fee(total_revenue)
            net_revenue = total_revenue - fee
            
            # 포트폴리오 업데이트
            portfolio.quantity -= quantity
            if portfolio.quantity == 0:
                # 모든 수량을 매도한 경우 포트폴리오 삭제
                db.delete(portfolio)
            else:
                # 일부 매도의 경우 투자금액 비례 감소
                sold_ratio = quantity / (portfolio.quantity + quantity)
                portfolio.total_invested *= (1 - sold_ratio)
            
            # 거래 내역 저장
            transaction = Transaction(
                user_id=user.id,
                symbol=symbol,
                transaction_type="SELL",
                quantity=quantity,
                price=current_price,
                total_amount=total_revenue,
                fee=fee,
                status="COMPLETED"
            )
            db.add(transaction)
            
            # 사용자 잔고 업데이트
            user.balance += net_revenue
            
            # 데이터베이스 커밋
            db.commit()
            if portfolio.quantity > 0:
                db.refresh(portfolio)
            db.refresh(transaction)
            db.refresh(user)
            
            return {
                "success": True,
                "message": f"{symbol} {quantity}개 매도 완료",
                "transaction": {
                    "id": transaction.id,
                    "symbol": symbol,
                    "type": "SELL",
                    "quantity": quantity,
                    "price": current_price,
                    "total_revenue": total_revenue,
                    "fee": fee,
                    "net_revenue": net_revenue
                },
                "portfolio": {
                    "symbol": symbol,
                    "quantity": portfolio.quantity if portfolio.quantity > 0 else 0,
                    "avg_price": portfolio.avg_price if portfolio.quantity > 0 else 0,
                    "total_invested": portfolio.total_invested if portfolio.quantity > 0 else 0
                } if portfolio.quantity > 0 else None,
                "new_balance": user.balance
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logging.error(f"매도 오류: {e}")
            raise HTTPException(status_code=500, detail="매도 처리 실패")
    
    def get_user_portfolio(self, user: User, db: Session) -> Dict[str, Any]:
        """사용자 포트폴리오 조회"""
        try:
            portfolios = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
            
            portfolio_data = []
            total_value = 0
            total_invested = 0
            
            for portfolio in portfolios:
                try:
                    current_price = self.get_current_price(portfolio.symbol)
                    current_value = portfolio.quantity * current_price
                    profit_loss = current_value - portfolio.total_invested
                    profit_loss_pct = (profit_loss / portfolio.total_invested * 100) if portfolio.total_invested > 0 else 0
                    
                    portfolio_item = {
                        "symbol": portfolio.symbol,
                        "quantity": portfolio.quantity,
                        "avg_price": portfolio.avg_price,
                        "current_price": current_price,
                        "total_invested": portfolio.total_invested,
                        "current_value": current_value,
                        "profit_loss": profit_loss,
                        "profit_loss_pct": profit_loss_pct
                    }
                    portfolio_data.append(portfolio_item)
                    
                    total_value += current_value
                    total_invested += portfolio.total_invested
                    
                except Exception as e:
                    logging.warning(f"포트폴리오 {portfolio.symbol} 가격 조회 실패: {e}")
                    continue
            
            total_profit_loss = total_value - total_invested
            total_profit_loss_pct = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
            
            return {
                "balance": user.balance,
                "total_invested": total_invested,
                "total_value": total_value,
                "total_profit_loss": total_profit_loss,
                "total_profit_loss_pct": total_profit_loss_pct,
                "total_assets": user.balance + total_value,
                "portfolios": portfolio_data
            }
            
        except Exception as e:
            logging.error(f"포트폴리오 조회 오류: {e}")
            raise HTTPException(status_code=500, detail="포트폴리오 조회 실패")
    
    def get_user_transactions(self, user: User, db: Session, limit: int = 50) -> list:
        """사용자 거래 내역 조회"""
        try:
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user.id
            ).order_by(Transaction.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": tx.id,
                    "symbol": tx.symbol,
                    "type": tx.transaction_type,
                    "quantity": tx.quantity,
                    "price": tx.price,
                    "total_amount": tx.total_amount,
                    "fee": tx.fee,
                    "status": tx.status,
                    "created_at": tx.created_at.isoformat()
                }
                for tx in transactions
            ]
            
        except Exception as e:
            logging.error(f"거래 내역 조회 오류: {e}")
            raise HTTPException(status_code=500, detail="거래 내역 조회 실패")

# 거래 서비스 인스턴스
trading_service = TradingService()
