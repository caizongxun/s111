"""
【修復版本】auto_monitor.py

核心修復：
1. ✅ 所有 Fetcher 初始化替換為 get_fetcher()
2. ✅ 解決 "Fetcher not initialized" 錯誤
3. ✅ 統一使用 app.py 中初始化的全局 Fetcher
"""

import asyncio
import logging
from datetime import datetime
import pandas as pd
from typing import Dict, List, Any

# ✅ 修復：導入 get_fetcher 而不是直接實例化
from backend.data_fetcher import get_fetcher
from backend.config import COINS, TIMEFRAMES, AUTO_TRADE_CONFIDENCE_THRESHOLD, AUTO_TRADE_ENABLED

logger = logging.getLogger(__name__)

class TechnicalSignalScanner:
    """純技術指標掃描器"""
    
    def __init__(self):
        logger.info("✅ TechnicalScanner initialized")

    def generate_signal(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Dict:
        """基於技術指標生成信號"""
        try:
            if df is None or len(df) < 30:
                return {'signal': 'HOLD', 'confidence': 0.0}

            last_row = df.iloc[-1]
            
            # 獲取指標值
            rsi = last_row.get('rsi_14', 50)
            macd = last_row.get('macd', 0)
            macd_signal = last_row.get('macd_signal', 0)
            close = last_row.get('close', 0)
            bb_upper = last_row.get('bb_upper', 0)
            bb_lower = last_row.get('bb_lower', 0)
            
            score = 0
            
            # 1. RSI 策略
            if rsi < 30: score += 1      # 超賣，看漲
            elif rsi > 70: score -= 1    # 超買，看跌
            
            # 2. MACD 策略
            if macd > macd_signal: score += 1  # 金叉
            else: score -= 1                   # 死叉
            
            # 3. 布林帶策略
            if close < bb_lower: score += 1    # 觸底反彈
            elif close > bb_upper: score -= 1  # 觸頂回調
            
            # 判斷方向
            if score >= 2:
                return {
                    'coin': symbol,
                    'timeframe': timeframe,
                    'signal': 'BUY',
                    'confidence': 0.85,  # 技術指標給予較高置信度
                    'current_price': close,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'technical'
                }
            elif score <= -2:
                return {
                    'coin': symbol,
                    'timeframe': timeframe,
                    'signal': 'SELL',
                    'confidence': 0.85,
                    'current_price': close,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'technical'
                }
            
            return {
                'coin': symbol,
                'timeframe': timeframe,
                'signal': 'HOLD',
                'confidence': 0.0,
                'current_price': close,
                'timestamp': datetime.now().isoformat(),
                'type': 'technical'
            }
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return {'signal': 'HOLD', 'confidence': 0.0}

class HybridSignalManager:
    """混合信號管理器 (技術分析 + 機器學習)"""
    
    def __init__(self):
        self.technical_scanner = TechnicalSignalScanner()
        # 暫時禁用 ML 模型以避免錯誤，後續可以重新啟用
        self.ml_predictor = None 
        logger.info("✅ HybridSignalManager initialized")

    def scan_all_signals(self):
        """掃描所有幣種和時間週期"""
        signals_a = []  # 技術指標信號
        signals_b = []  # ML 信號
        
        # ✅ 修復：使用全局 fetcher
        fetcher = get_fetcher()
        if fetcher is None:
            logger.warning("❌ Fetcher not initialized in scan_all_signals")
            return {'all': [], 'consensus': []}

        for coin in COINS:
            for tf in TIMEFRAMES:
                try:
                    # 獲取數據
                    df = fetcher.get_latest_data(coin, tf, limit=100)
                    if df is None: continue
                    
                    # 添加指標
                    df = fetcher.add_technical_indicators(df)
                    
                    # 1. 技術分析信號
                    sig_tech = self.technical_scanner.generate_signal(coin, tf, df)
                    if sig_tech['signal'] != 'HOLD':
                        signals_a.append(sig_tech)
                    
                    # 2. ML 信號 (暫時跳過)
                    pass
                    
                except Exception as e:
                    logger.error(f"Error scanning {coin} {tf}: {e}")
                    continue
        
        # 尋找共識 (目前僅返回技術信號)
        return {
            'all': signals_a,
            'version_a': signals_a,
            'version_b': [],
            'consensus': signals_a  # 暫時將技術信號作為共識
        }

    def get_high_confidence_signals(self):
        """獲取高置信度信號"""
        result = self.scan_all_signals()
        all_signals = result['all']
        return [s for s in all_signals if s['confidence'] >= 0.75]

class PositionMonitor:
    """持倉監控器"""
    
    def __init__(self):
        logger.info("✅ PositionMonitor initialized")

    def check_positions(self):
        """檢查開倉"""
        try:
            # ✅ 修復：使用全局 fetcher
            fetcher = get_fetcher()
            if fetcher is None:
                logger.warning("❌ Fetcher not initialized in check_positions")
                return {'total_positions': 0, 'positions': [], 'total_unrealized_pnl': 0}

            positions = fetcher.get_open_positions()
            
            total_pnl = 0
            position_list = []
            
            for pos in positions:
                symbol = pos['symbol']
                amount = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                mark_price = float(pos['markPrice'])
                
                if amount != 0:
                    pnl = float(pos['unrealizedProfit'])
                    pnl_pct = (pnl / (abs(amount) * entry_price / float(pos['leverage']))) * 100
                    
                    total_pnl += pnl
                    
                    position_list.append({
                        'symbol': symbol,
                        'side': 'LONG' if amount > 0 else 'SHORT',
                        'positionAmt': amount,
                        'entryPrice': entry_price,
                        'markPrice': mark_price,
                        'unrealizedProfit': pnl,
                        'pnl_pct': pnl_pct,
                        'leverage': pos['leverage']
                    })
            
            return {
                'total_positions': len(position_list),
                'positions': position_list,
                'total_unrealized_pnl': total_pnl
            }

        except Exception as e:
            logger.error(f"Error checking positions: {str(e)}")
            return {
                'total_positions': 0,
                'positions': [],
                'total_unrealized_pnl': 0
            }

    def get_account_summary(self):
        """獲取賬戶摘要"""
        try:
            # ✅ 修復：使用全局 fetcher
            fetcher = get_fetcher()
            if fetcher is None:
                logger.warning("❌ Fetcher not initialized in get_account_summary")
                return self._get_empty_summary()

            balance = fetcher.get_account_balance()
            positions = self.check_positions()
            
            return {
                'balance': balance,
                'positions': positions,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting account summary: {str(e)}")
            return self._get_empty_summary()
            
    def _get_empty_summary(self):
        """返回空摘要"""
        return {
            'balance': {
                'totalWalletBalance': 0,
                'totalUnrealizedProfit': 0,
                'totalMarginBalance': 0,
                'totalPositionInitialMargin': 0,
                'totalOpenOrderInitialMargin': 0
            },
            'positions': {
                'total_positions': 0,
                'positions': [],
                'total_unrealized_pnl': 0
            },
            'timestamp': datetime.now().isoformat()
        }

class AutoTradingMonitor:
    """自動交易監控系統 - 完全修復版"""
    
    def __init__(self):
        """初始化監控系統"""
        self.signal_manager = HybridSignalManager()
        self.position_monitor = PositionMonitor()
        self.is_running = False
        
        # ✅ 為了兼容 app.py 的 API 調用
        self.signal_scanner = self.signal_manager 
        
        logger.info("✅ AutoTradingMonitor initialized")

    async def run_monitoring_loop(self, interval: int = 60):
        """運行監控循環"""
        # 避免循環導入
        from backend.auto_executor import get_auto_executor
        
        self.is_running = True
        logger.info(f"🔄 監控循環已啟動，間隔: {interval} 秒")
        
        try:
            while self.is_running:
                try:
                    # 1. 掃描信號
                    result = self.signal_manager.scan_all_signals()
                    signals = result.get('consensus', [])
                    
                    if not AUTO_TRADE_ENABLED:
                        logger.info(f"🔍 掃描完成: 發現 {len(signals)} 個信號 (自動交易未啟用)")
                        await asyncio.sleep(interval)
                        continue

                    # 2. 獲取執行器
                    executor = get_auto_executor()
                    if executor is None:
                        logger.warning("⚠️ Executor not initialized")
                        await asyncio.sleep(interval)
                        continue
                        
                    # 3. 過濾高置信度信號
                    trading_signals = [
                        s for s in signals 
                        if s['confidence'] >= AUTO_TRADE_CONFIDENCE_THRESHOLD
                    ]
                    
                    if not trading_signals:
                        logger.info("💤 無高置信度信號")
                        await asyncio.sleep(interval)
                        continue

                    # 4. 執行交易
                    for signal in trading_signals:
                        try:
                            # 檢查餘額
                            balance_info = self.position_monitor.get_account_summary()
                            wallet_balance = float(balance_info['balance']['totalWalletBalance'])
                            
                            if wallet_balance > 0:
                                logger.info(f"🚀 執行自動交易: {signal['coin']} {signal['signal']}")
                                await executor.execute_trade(signal, wallet_balance)
                            else:
                                logger.warning("⚠️ 餘額不足，無法交易")
                                
                        except Exception as e:
                            logger.error(f"❌ Error executing trade for {signal['coin']}: {str(e)}")
                            
                except Exception as e:
                    logger.error(f"❌ Monitoring loop error: {str(e)}")
                    
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.info("🛑 監控循環已停止")
        except Exception as e:
            logger.error(f"❌ Monitoring loop crashed: {str(e)}")
        finally:
            self.is_running = False

    def stop(self):
        """停止監控"""
        self.is_running = False
        logger.info("🛑 監控已停止")

# 全局實例管理
_monitor_instance = None

def init_auto_monitor():
    """初始化全局監控器"""
    global _monitor_instance
    try:
        _monitor_instance = AutoTradingMonitor()
        return _monitor_instance
    except Exception as e:
        logger.error(f"❌ Failed to init monitor: {str(e)}")
        raise

def get_auto_monitor():
    """獲取全局監控器實例"""
    return _monitor_instance
