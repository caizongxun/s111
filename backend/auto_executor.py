"""
【修復版本】auto_executor.py

核心更新：
1. ✅ 新增 place_manual_order 方法，支持手動開單
2. ✅ 整合 get_fetcher() 使用全局連接
3. ✅ 完善的精度處理和訂單類型支持
"""

import logging
import math
from datetime import datetime
from binance.client import Client
from backend.data_fetcher import get_fetcher

logger = logging.getLogger(__name__)

class AutoTradeExecutor:
    def __init__(self, api_key, api_secret, testnet=True, stop_loss_percent=2.0, take_profit_percent=5.0):
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        self.trade_history = []
        
        # 嘗試獲取全局 fetcher，如果失敗則暫時不報錯（可能在測試）
        self.fetcher = get_fetcher()
        if self.fetcher:
            self.client = self.fetcher.client
        else:
            logger.warning("⚠️ AutoTradeExecutor initialized without fetcher, will retry in methods")
            self.client = None

    def _ensure_client(self):
        """確保 client 可用"""
        if not self.client:
            self.fetcher = get_fetcher()
            if self.fetcher:
                self.client = self.fetcher.client
            else:
                raise RuntimeError("Fetcher not initialized")

    def get_symbol_info(self, symbol):
        """獲取交易對精度信息"""
        self._ensure_client()
        try:
            info = self.client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    # 獲取價格精度
                    price_precision = s['pricePrecision']
                    # 獲取數量精度
                    quantity_precision = s['quantityPrecision']
                    return {
                        'pricePrecision': price_precision,
                        'quantityPrecision': quantity_precision
                    }
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
        
        # 默認值
        return {'pricePrecision': 2, 'quantityPrecision': 3}

    async def execute_trade(self, signal, account_balance):
        """
        執行自動交易 (兼容 async)
        """
        try:
            symbol = signal['coin']
            side = signal['signal'] # BUY or SELL
            price = float(signal['current_price'])
            
            # 簡單的倉位管理：使用餘額的 10%
            position_size_usdt = account_balance * 0.1
            quantity = position_size_usdt / price
            
            # 調用手動下單邏輯執行
            result = self.place_manual_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                leverage=5, # 自動交易默認 5 倍
                stop_loss_percent=self.stop_loss_percent * 100,
                take_profit_percent=self.take_profit_percent * 100,
                current_price=price
            )
            return result
            
        except Exception as e:
            logger.error(f"Auto trade execution failed: {e}")
            return None

    def place_manual_order(self, symbol, side, quantity, leverage, stop_loss_percent, take_profit_percent, current_price):
        """
        手動開單核心邏輯
        """
        self._ensure_client()
        try:
            logger.info(f"🚀 開始執行下單: {symbol} {side} {quantity}")
            
            # 1. 獲取精度信息
            meta = self.get_symbol_info(symbol)
            qty_precision = meta['quantityPrecision']
            price_precision = meta['pricePrecision']
            
            # 2. 設置槓桿
            try:
                self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            except Exception as e:
                logger.warning(f"Leverage update failed (might be already set): {e}")

            # 3. 規範化數量
            # round(10.1234, 2) -> 10.12
            quantity = round(float(quantity), qty_precision)
            
            # 4. 下市價單
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            # 獲取成交均價
            avg_price = float(order.get('avgPrice', 0))
            if avg_price == 0:
                avg_price = float(current_price)
                
            logger.info(f"✅ 主訂單成交: ID {order['orderId']} @ {avg_price}")

            # 5. 計算止盈止損價格
            sl_price = 0
            tp_price = 0
            
            if side == 'BUY':
                sl_price = avg_price * (1 - stop_loss_percent / 100)
                tp_price = avg_price * (1 + take_profit_percent / 100)
                exit_side = 'SELL'
            else:
                sl_price = avg_price * (1 + stop_loss_percent / 100)
                tp_price = avg_price * (1 - take_profit_percent / 100)
                exit_side = 'BUY'
                
            # 規範化價格
            sl_price = round(sl_price, price_precision)
            tp_price = round(tp_price, price_precision)

            sl_order_res = None
            tp_order_res = None

            # 6. 下止損單
            try:
                sl_order_res = self.client.futures_create_order(
                    symbol=symbol,
                    side=exit_side,
                    type='STOP_MARKET',
                    stopPrice=sl_price,
                    closePosition=True
                )
                logger.info(f"🛡️ 止損單已設置: {sl_price}")
            except Exception as e:
                logger.error(f"❌ 止損單設置失敗: {e}")

            # 7. 下止盈單
            try:
                tp_order_res = self.client.futures_create_order(
                    symbol=symbol,
                    side=exit_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp_price,
                    closePosition=True
                )
                logger.info(f"💰 止盈單已設置: {tp_price}")
            except Exception as e:
                logger.error(f"❌ 止盈單設置失敗: {e}")

            # 8. 記錄交易
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': avg_price,
                'leverage': leverage,
                'orderId': order['orderId'],
                'sl_price': sl_price,
                'tp_price': tp_price,
                'pnl': 0
            }
            self.trade_history.append(trade_record)
            
            return trade_record

        except Exception as e:
            logger.error(f"❌ 手動下單失敗: {e}")
            raise e

    def get_trade_stats(self):
        """獲取交易統計"""
        return {
            "total_trades": len(self.trade_history),
            "last_trade": self.trade_history[-1] if self.trade_history else None
        }

# 全局實例
_executor_instance = None

def init_auto_executor(api_key, api_secret, testnet, stop_loss_percent, take_profit_percent):
    global _executor_instance
    _executor_instance = AutoTradeExecutor(api_key, api_secret, testnet, stop_loss_percent, take_profit_percent)
    return _executor_instance

def get_auto_executor():
    return _executor_instance
