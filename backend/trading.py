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
            
            # Portfolio 테이블 사용 안 함 - Transaction만 기록
            
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
            # 거래 내역 기반으로 보유 수량 확인
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.symbol == symbol,
                Transaction.status == "COMPLETED"
            ).all()
            
            # 현재 보유 수량 계산
            current_quantity = 0
            for tx in transactions:
                if tx.transaction_type == "BUY":
                    current_quantity += tx.quantity
                elif tx.transaction_type == "SELL":
                    current_quantity -= tx.quantity
            
            if current_quantity < quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"보유 수량 부족: 매도 요청 {quantity}개, 보유 수량 {current_quantity}개"
                )
            
            # 현재 가격 조회
            current_price = self.get_current_price(symbol)
            
            # 매도 금액 계산
            total_revenue = quantity * current_price
            fee = self.calculate_fee(total_revenue)
            net_revenue = total_revenue - fee
            
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
                "new_balance": user.balance
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logging.error(f"매도 오류: {e}")
            raise HTTPException(status_code=500, detail="매도 처리 실패")
    
    def get_user_portfolio(self, user: User, db: Session) -> Dict[str, Any]:
        """거래 내역 기반 사용자 포트폴리오 조회"""
        try:
            # 모든 거래 내역 조회
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.status == "COMPLETED"
            ).order_by(Transaction.created_at.asc()).all()
            
            # 심볼별 포지션 계산
            positions = {}
            
            for tx in transactions:
                symbol = tx.symbol
                if symbol not in positions:
                    positions[symbol] = {
                        'quantity': 0,
                        'total_cost': 0,  # 수수료 제외한 순수 매입 비용
                        'total_fees': 0,  # 수수료만 따로 계산
                        'total_sold': 0
                    }
                
                if tx.transaction_type == "BUY":
                    positions[symbol]['quantity'] += tx.quantity
                    # tx.total_amount는 수수료 제외된 순수 거래 금액
                    positions[symbol]['total_cost'] += tx.total_amount
                    positions[symbol]['total_fees'] += tx.fee if tx.fee else 0
                elif tx.transaction_type == "SELL":
                    # 매도 시 FIFO 방식으로 평균 매입가 조정
                    sold_quantity = tx.quantity
                    original_quantity = positions[symbol]['quantity']
                    positions[symbol]['quantity'] -= sold_quantity
                    
                    # 매도한 비율만큼 투자 비용 차감 (정밀도 개선)
                    if original_quantity > 0:
                        sold_ratio = sold_quantity / original_quantity
                        # 매도 후 남은 비율만큼만 유지
                        remaining_ratio = 1 - sold_ratio
                        positions[symbol]['total_cost'] *= remaining_ratio
                        positions[symbol]['total_fees'] *= remaining_ratio
                        
                        # 음수 방지
                        if positions[symbol]['quantity'] < 0.00000001:  # 소수점 8자리 이하는 0으로 처리
                            positions[symbol]['quantity'] = 0
                            positions[symbol]['total_cost'] = 0
                            positions[symbol]['total_fees'] = 0
                    
                    positions[symbol]['total_sold'] += tx.total_amount
            
            # 포트폴리오 데이터 생성
            portfolio_data = []
            total_value = 0
            total_invested = 0
            
            for symbol, position in positions.items():
                if position['quantity'] > 0:  # 보유 수량이 있는 경우만
                    try:
                        current_price = self.get_current_price(symbol)
                        current_value = position['quantity'] * current_price
                        
                        # 평균 매입가 계산 (수수료 제외한 순수 가격)
                        if position['quantity'] > 0:
                            avg_price = position['total_cost'] / position['quantity']
                        else:
                            avg_price = 0
                        
                        # 실제 투자 금액 (수수료 포함)
                        invested_amount = position['total_cost'] + position['total_fees']
                        profit_loss = current_value - invested_amount
                        profit_loss_pct = (profit_loss / invested_amount * 100) if invested_amount > 0 else 0
                        
                        portfolio_item = {
                            "symbol": symbol,
                            "quantity": position['quantity'],
                            "avg_price": avg_price,
                            "current_price": current_price,
                            "total_invested": invested_amount,
                            "current_value": current_value,
                            "profit_loss": profit_loss,
                            "profit_loss_pct": profit_loss_pct
                        }
                        portfolio_data.append(portfolio_item)
                        
                        total_value += current_value
                        total_invested += invested_amount
                        
                    except Exception as e:
                        logging.warning(f"포트폴리오 {symbol} 가격 조회 실패: {e}")
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
                "portfolios": portfolio_data,
                "holding_count": len(portfolio_data)
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
