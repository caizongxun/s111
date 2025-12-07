"""
【修復版本】data_fetcher.py

核心修復：
1. ✅ 實現單例模式 (Singleton Pattern)
2. ✅ 添加 init_fetcher 和 get_fetcher 全局函數
3. ✅ 讓其他模塊可以直接調用 get_fetcher() 獲取實例
"""

import pandas as pd
import numpy as np
from binance.client import Client
import logging
from pathlib import Path
from datetime import datetime, timedelta
import time

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from backend.config import USE_TESTNET
except ImportError:
    from config import USE_TESTNET
    logger.warning("⚠️ 使用本地 config.py")

# 全局實例
_global_fetcher = None

def init_fetcher(api_key: str, api_secret: str, testnet: bool = None):
    """初始化全局數據獲取器"""
    global _global_fetcher
    if _global_fetcher is not None:
        logger.warning("⚠️ Fetcher already initialized")
        return _global_fetcher
        
    try:
        _global_fetcher = BinanceDataFetcher(api_key, api_secret, testnet)
        logger.info("✅ Global data fetcher initialized")
        return _global_fetcher
    except Exception as e:
        logger.error(f"❌ Failed to init global fetcher: {e}")
        raise

def get_fetcher():
    """獲取全局數據獲取器實例"""
    global _global_fetcher
    if _global_fetcher is None:
        logger.warning("⚠️ 全局數據獲取器未初始化，請先調用 init_fetcher()")
        return None
    return _global_fetcher

class BinanceDataFetcher:
    """改進的幣安數據獲取器 - 包含時間同步修復和配置一致性修復"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = None):
        """
        初始化數據獲取器
        Args:
            api_key: Binance API Key
            api_secret: Binance API Secret
            testnet: 是否使用測試網。如果為 None，從 config.USE_TESTNET 讀取
        """
        if not api_key or not api_secret:
            logger.error("❌ API Key 或 Secret 未提供")
            raise ValueError("API Key and Secret are required")
            
        self.api_key = api_key
        self.api_secret = api_secret
        
        # 如果未指定 testnet，使用配置文件中的值
        if testnet is None:
            testnet = USE_TESTNET
        self.testnet = testnet
        
        self.time_offset = 0  # 時間偏移量
        
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            logger.info(f"✅ Binance client initialized (testnet={testnet})")
            
            # 同步系統時間與服務器時間
            self._sync_time()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Binance client: {str(e)}")
            raise

    def _sync_time(self):
        """同步本地時間與 Binance 服務器時間"""
        try:
            logger.info("🔄 正在同步系統時間...")
            server_time = self.client.get_server_time()['serverTime']
            local_time = int(time.time() * 1000)
            self.time_offset = server_time - local_time
            logger.info(f"✅ 時間同步完成，偏移量: {self.time_offset}ms")
            
            if abs(self.time_offset) > 1000:
                logger.warning(f"⚠️ 時間偏差較大: {abs(self.time_offset)}ms")
        except Exception as e:
            logger.error(f"❌ Failed to sync time: {str(e)}")

    def fetch_klines(self, symbol: str, interval: str, limit: int = 1500) -> pd.DataFrame:
        """獲取 K 線數據"""
        try:
            limit = int(limit)
            if limit > 1500:
                limit = 1500
                
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            if not klines:
                return None
                
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            return df.dropna()
            
        except Exception as e:
            logger.error(f"❌ Error fetching klines for {symbol} {interval}: {str(e)}")
            return None

    def get_latest_data(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """獲取最新的 K 線數據"""
        return self.fetch_klines(symbol, interval, limit)

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加技術指標特徵"""
        try:
            if df is None or len(df) < 30:
                return df
                
            df = df.sort_values('close_time').reset_index(drop=True)
            
            # RSI
            df['rsi_14'] = self._calculate_rsi(df['close'], period=14)
            
            # MACD
            df['macd'], df['macd_signal'], df['macd_hist'] = self._calculate_macd(df['close'])
            
            # Bollinger Bands
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
            
            # ATR
            df['atr_14'] = self._calculate_atr(df, period=14)
            
            # Volume MA
            df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
            
            # ROC
            df['roc_12'] = self._calculate_roc(df['close'], period=12)
            
            # Close MA & Std
            df['close_ma_5'] = df['close'].rolling(window=5).mean()
            df['close_std_5'] = df['close'].rolling(window=5).std()
            
            return df.bfill()
            
        except Exception as e:
            logger.error(f"Error adding indicators: {e}")
            return df

    def _calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, series, fast=12, slow=26, signal=9):
        exp1 = series.ewm(span=fast, adjust=False).mean()
        exp2 = series.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

    def _calculate_bollinger_bands(self, series, period=20, std_dev=2):
        ma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = ma + (std * std_dev)
        lower = ma - (std * std_dev)
        return upper, ma, lower

    def _calculate_atr(self, df, period=14):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(window=period).mean()

    def _calculate_roc(self, series, period=12):
        return ((series - series.shift(period)) / series.shift(period)) * 100

    def get_account_balance(self):
        """獲取賬戶餘額"""
        try:
            account = self.client.futures_account()
            
            total_wallet_balance = float(account.get('totalWalletBalance', 0))
            total_unrealized_profit = float(account.get('totalUnrealizedProfit', 0))
            total_margin_balance = float(account.get('totalMarginBalance', 0))
            total_position_initial_margin = float(account.get('totalPositionInitialMargin', 0))
            total_open_order_initial_margin = float(account.get('totalOpenOrderInitialMargin', 0))
            
            return {
                'totalWalletBalance': total_wallet_balance,
                'totalUnrealizedProfit': total_unrealized_profit,
                'totalMarginBalance': total_margin_balance,
                'totalPositionInitialMargin': total_position_initial_margin,
                'totalOpenOrderInitialMargin': total_open_order_initial_margin
            }
        except Exception as e:
            logger.error(f"❌ Failed to get account balance: {str(e)}")
            return None

    def get_current_price(self, symbol: str):
        """獲取當前價格"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"❌ Failed to get price for {symbol}: {str(e)}")
            return None

    def get_open_positions(self):
        """獲取當前持倉"""
        try:
            positions = self.client.futures_position_information()
            return [p for p in positions if float(p['positionAmt']) != 0]
        except Exception as e:
            logger.error(f"❌ Failed to get positions: {str(e)}")
            return []

    def get_funding_rate(self, symbol: str):
        """獲取資金費率"""
        try:
            funding = self.client.futures_funding_rate(symbol=symbol, limit=1)
            if funding:
                return {
                    'symbol': symbol,
                    'fundingRate': float(funding[0]['fundingRate']),
                    'time': datetime.fromtimestamp(funding[0]['fundingTime']/1000).isoformat()
                }
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get funding rate: {str(e)}")
            return None

    def get_order_book(self, symbol: str, limit: int = 20):
        """獲取訂單簿"""
        try:
            depth = self.client.futures_order_book(symbol=symbol, limit=limit)
            return {
                'bids': [[float(p), float(q)] for p, q in depth['bids']],
                'asks': [[float(p), float(q)] for p, q in depth['asks']]
            }
        except Exception as e:
            logger.error(f"❌ Failed to get orderbook: {str(e)}")
            return None
