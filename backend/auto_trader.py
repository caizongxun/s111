"""
Auto Trading Module - 自动交易模块
处理自动开单、风险管理、交易历史
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from binance.client import Client

from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET,
    AUTO_TRADE_CONFIDENCE_THRESHOLD,
    MANUAL_TRADE_CONFIDENCE_THRESHOLD,
    DEFAULT_POSITION_SIZE, MAX_POSITION_SIZE,
    STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT,
    ORDER_TYPE, TRADE_HISTORY_FILE
)

logger = logging.getLogger(__name__)


class AutoTrader:
    """自动交易系统"""
    
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        self.api_key = api_key or BINANCE_API_KEY
        self.api_secret = api_secret or BINANCE_API_SECRET
        self.testnet = testnet
        
        # 初始化币安客户端
        self.client = Client(self.api_key, self.api_secret, testnet=testnet)
        
        # 交易历史
        self.trade_history = self.load_trade_history()
        
        logger.info("AutoTrader initialized (testnet={})".format(testnet))
    
    def evaluate_signal(self, prediction_data: dict) -> dict:
        """
        评估交易信号
        
        Args:
            prediction_data: 预测数据（来自 /predict 端点）
            
        Returns:
            {
                'should_auto_trade': bool,  # 是否自动开单
                'should_recommend': bool,   # 是否推荐（但不自动）
                'action': 'BUY'/'SELL'/'HOLD',
                'confidence': float,        # 置信度 0-1
                'reason': str               # 原因说明
            }
        """
        signal = prediction_data['signal']
        confidence = signal['confidence']
        trade_signal = signal['signal']
        price_change = signal['price_change_percent']
        
        result = {
            'coin': prediction_data['coin'],
            'timeframe': prediction_data['timeframe'],
            'current_price': signal['current_price'],
            'predicted_price': signal['predicted_price'],
            'price_change_percent': price_change,
            'confidence': confidence,
            'signal': trade_signal,
            'should_auto_trade': False,
            'should_recommend': False,
            'action': 'HOLD',
            'reason': ''
        }
        
        # 判断是否推荐
        if confidence >= MANUAL_TRADE_CONFIDENCE_THRESHOLD:
            result['should_recommend'] = True
            
            # 判断是否自动开单
            if confidence >= AUTO_TRADE_CONFIDENCE_THRESHOLD and trade_signal in ['BUY', 'SELL']:
                result['should_auto_trade'] = True
                result['action'] = trade_signal
                result['reason'] = f"高置信度 ({confidence*100:.1f}%) {trade_signal} 信号，自动开单"
            else:
                result['reason'] = f"置信度 ({confidence*100:.1f}%)，推荐但不自动开单"
        else:
            result['reason'] = f"置信度过低 ({confidence*100:.1f}%)，不推荐开单"
        
        return result
    
    def place_order(self, coin: str, side: str, confidence: float) -> dict:
        """
        执行交易订单
        
        Args:
            coin: 币种（如 BTCUSDT）
            side: 方向（BUY 或 SELL）
            confidence: 置信度
            
        Returns:
            订单结果
        """
        try:
            # 获取账户信息
            account = self.client.futures_account()
            balance = float(account['totalWalletBalance'])
            
            # 计算头寸大小
            position_size = DEFAULT_POSITION_SIZE * confidence
            position_size = min(position_size, MAX_POSITION_SIZE)
            
            # 计算交易量（简化计算）
            notional_value = balance * position_size / 100
            
            # 获取当前价格
            ticker = self.client.futures_symbol_ticker(symbol=coin)
            current_price = float(ticker['price'])
            
            quantity = notional_value / current_price
            quantity = round(quantity, 4)
            
            # 执行订单
            if ORDER_TYPE == "MARKET":
                order = self.client.futures_create_order(
                    symbol=coin,
                    side=side,
                    type="MARKET",
                    quantity=quantity
                )
            else:
                order = self.client.futures_create_order(
                    symbol=coin,
                    side=side,
                    type="LIMIT",
                    timeInForce='GTC',
                    quantity=quantity,
                    price=current_price
                )
            
            # 记录交易
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'coin': coin,
                'side': side,
                'quantity': quantity,
                'price': current_price,
                'confidence': confidence,
                'order_id': order['orderId'],
                'status': order['status']
            }
            
            self.trade_history.append(trade_record)
            self.save_trade_history()
            
            logger.info(f"Order placed: {coin} {side} {quantity} @ {current_price}")
            
            return {
                'status': 'success',
                'order': order,
                'trade_record': trade_record
            }
        
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_open_positions(self) -> List[dict]:
        """获取所有未平仓头寸"""
        try:
            positions = self.client.futures_account()['positions']
            open_positions = [
                {
                    'symbol': p['symbol'],
                    'quantity': float(p['positionAmt']),
                    'entry_price': float(p['entryPrice']),
                    'unrealized_profit': float(p['unrealizedProfit'])
                }
                for p in positions if float(p['positionAmt']) != 0
            ]
            return open_positions
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []
    
    def close_position(self, coin: str) -> dict:
        """平仓"""
        try:
            position = self.client.futures_account()
            pos_amount = 0
            for p in position['positions']:
                if p['symbol'] == coin:
                    pos_amount = float(p['positionAmt'])
                    break
            
            if pos_amount == 0:
                return {'status': 'error', 'message': 'No open position'}
            
            # 确定卖出方向
            side = "SELL" if pos_amount > 0 else "BUY"
            quantity = abs(pos_amount)
            
            order = self.client.futures_create_order(
                symbol=coin,
                side=side,
                type="MARKET",
                quantity=quantity
            )
            
            logger.info(f"Position closed: {coin} {side} {quantity}")
            
            return {
                'status': 'success',
                'order': order
            }
        
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def load_trade_history(self) -> List[dict]:
        """加载交易历史"""
        try:
            if Path(TRADE_HISTORY_FILE).exists():
                with open(TRADE_HISTORY_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading trade history: {str(e)}")
        
        return []
    
    def save_trade_history(self):
        """保存交易历史"""
        try:
            with open(TRADE_HISTORY_FILE, 'w') as f:
                json.dump(self.trade_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trade history: {str(e)}")
    
    def get_trade_stats(self) -> dict:
        """获取交易统计"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'win_rate': 0,
                'total_profit': 0
            }
        
        total = len(self.trade_history)
        buys = len([t for t in self.trade_history if t['side'] == 'BUY'])
        sells = len([t for t in self.trade_history if t['side'] == 'SELL'])
        
        return {
            'total_trades': total,
            'buy_trades': buys,
            'sell_trades': sells,
            'avg_confidence': sum(t['confidence'] for t in self.trade_history) / total if total > 0 else 0,
            'last_trade': self.trade_history[-1] if self.trade_history else None
        }
    
    def update_trade_history_from_binance(self):
        """从币安更新交易历史状态"""
        try:
            for trade in self.trade_history[-10:]:  # 只检查最近10笔
                if trade['status'] in ['NEW', 'PARTIALLY_FILLED']:
                    order = self.client.futures_get_order(
                        symbol=trade['coin'],
                        orderId=trade['order_id']
                    )
                    trade['status'] = order['status']
            
            self.save_trade_history()
        except Exception as e:
            logger.error(f"Error updating trade history: {str(e)}")


def main():
    """Test the auto trader"""
    logger.info("Auto Trader Test")
    trader = AutoTrader(testnet=True)
    
    # 测试信号评估
    test_prediction = {
        'coin': 'BTCUSDT',
        'timeframe': '1h',
        'current_price': 42000,
        'predicted_price': 42840,
        'signal': {
            'signal': 'BUY',
            'confidence': 0.75,
            'price_change_percent': 2.0
        }
    }
    
    result = trader.evaluate_signal(test_prediction)
    logger.info(f"Signal evaluation: {result}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
