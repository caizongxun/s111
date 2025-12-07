"""
模型回测验证系统 - 修复版本
使用历史数据测试现有模型的真实准确度
正确加载已训练的模型
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestValidator:
    """回测验证系统 - 用历史数据测试模型准确度"""
    
    def __init__(self, data_fetcher, model_manager, test_data_dir="./test_data"):
        self.data_fetcher = data_fetcher
        self.model_manager = model_manager
        self.test_data_dir = test_data_dir
        self.backtest_results = {}
        self.accuracy_report = {}
        
        # 创建测试数据目录
        Path(test_data_dir).mkdir(exist_ok=True)
    
    def fetch_historical_data(self, coin: str, timeframe: str, limit: int = 2000) -> pd.DataFrame:
        """
        获取历史数据用于回测
        使用本地数据（已训练的数据）
        """
        try:
            logger.info(f"Loading local data for {coin} {timeframe}...")
            df = self.data_fetcher.load_local_data(coin, timeframe)
            
            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {coin} {timeframe}")
                return None
            
            logger.info(f"✅ Using {len(df)} K-lines for {coin} {timeframe}")
            return df
        
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return None
    
    def backtest_model(self, coin: str, timeframe: str, test_df: pd.DataFrame) -> Dict:
        """
        回测单个模型
        
        Args:
            coin: 币种
            timeframe: 时间框架
            test_df: 测试数据 DataFrame
        
        Returns:
            {
                'coin': 币种,
                'timeframe': 时间框架,
                'total_predictions': 总预测数,
                'directional_accuracy': 方向准确度,
                'rmse': 均方根误差,
                'mae': 平均绝对误差,
                'mape': 平均百分比误差,
                'precision_up': 预测涨的准确率,
                'precision_down': 预测跌的准确率,
                'buy_signals': 买入信号数,
                'sell_signals': 卖出信号数,
                'successful_trades': 成功交易数,
                'trade_success_rate': 交易成功率
            }
        """
        try:
            if test_df is None or len(test_df) < 100:
                logger.warning(f"Test data insufficient for {coin} {timeframe}")
                return None
            
            logger.info(f"Backtesting {coin} {timeframe}...")
            
            # 获取模型
            model = self.model_manager.get_or_create_model(coin, timeframe)
            
            # 👈 关键：从磁盘加载模型
            if not model.load_model():
                logger.warning(f"Model file not found for {coin} {timeframe}")
                return None
            
            if model.model is None:
                logger.warning(f"Model not loaded for {coin} {timeframe}")
                return None
            
            # 准备测试数据
            test_prices = test_df['close'].values
            
            predictions = []
            actuals = []
            predictions_buy = []  # 预测涨的信号
            predictions_sell = []  # 预测跌的信号
            
            # 从第 60 根开始预测
            for i in range(60, len(test_prices) - 1):
                try:
                    # 用前 60 根 K 线预测下一根
                    input_data = test_prices[i-60:i]
                    
                    # 预测
                    pred = model.predict(input_data, steps_ahead=1)
                    
                    if pred is not None and len(pred) > 0:
                        predicted_price = pred[0]
                        actual_price = test_prices[i + 1]
                        
                        predictions.append(predicted_price)
                        actuals.append(actual_price)
                        
                        # 记录方向
                        if predicted_price > test_prices[i]:
                            predictions_buy.append((predicted_price, actual_price))
                        else:
                            predictions_sell.append((predicted_price, actual_price))
                
                except Exception as e:
                    logger.debug(f"Error in prediction {i}: {str(e)}")
                    continue
            
            if len(predictions) < 10:
                logger.warning(f"Not enough predictions for {coin} {timeframe}")
                return None
            
            predictions = np.array(predictions)
            actuals = np.array(actuals)
            
            # 计算准确度指标
            
            # 1. 方向准确度
            pred_direction = np.diff(predictions) > 0
            actual_direction = np.diff(actuals) > 0
            directional_accuracy = np.mean(pred_direction == actual_direction)
            
            # 2. 误差指标
            rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
            mae = np.mean(np.abs(predictions - actuals))
            mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100
            
            # 3. 买入信号准确率
            if len(predictions_buy) > 0:
                buy_correct = sum(1 for pred, actual in predictions_buy if actual > pred)
                precision_up = buy_correct / len(predictions_buy)
            else:
                precision_up = 0
            
            # 4. 卖出信号准确率
            if len(predictions_sell) > 0:
                sell_correct = sum(1 for pred, actual in predictions_sell if actual < pred)
                precision_down = sell_correct / len(predictions_sell)
            else:
                precision_down = 0
            
            # 5. 交易成功率
            successful_trades = int(buy_correct if len(predictions_buy) > 0 else 0) + int(sell_correct if len(predictions_sell) > 0 else 0)
            trade_success_rate = successful_trades / len(predictions) if len(predictions) > 0 else 0
            
            result = {
                'coin': coin,
                'timeframe': timeframe,
                'total_predictions': len(predictions),
                'directional_accuracy': float(directional_accuracy),
                'rmse': float(rmse),
                'mae': float(mae),
                'mape': float(mape),
                'precision_up': float(precision_up),
                'precision_down': float(precision_down),
                'buy_signals': len(predictions_buy),
                'sell_signals': len(predictions_sell),
                'successful_trades': successful_trades,
                'trade_success_rate': float(trade_success_rate),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Backtest results for {coin} {timeframe}:")
            logger.info(f"   Direction Accuracy: {directional_accuracy:.2%}")
            logger.info(f"   Precision UP: {precision_up:.2%}")
            logger.info(f"   Precision DOWN: {precision_down:.2%}")
            logger.info(f"   Trade Success Rate: {trade_success_rate:.2%}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error backtesting {coin} {timeframe}: {str(e)}")
            return None
    
    def run_full_backtest(self, coins: List[str], timeframes: List[str], 
                         fetch_new: bool = False) -> Dict:
        """
        运行完整回测（所有币种和时间框架）
        
        Args:
            coins: 币种列表
            timeframes: 时间框架列表
            fetch_new: 是否重新获取数据
        
        Returns:
            完整的回测报告
        """
        try:
            logger.info(f"Starting full backtest for {len(coins)} coins × {len(timeframes)} timeframes...")
            
            all_results = []
            
            for coin_idx, coin in enumerate(coins, 1):
                for tf_idx, timeframe in enumerate(timeframes, 1):
                    model_num = (coin_idx - 1) * len(timeframes) + tf_idx
                    
                    try:
                        logger.info(f"\n[{model_num}/{len(coins) * len(timeframes)}] Processing {coin} {timeframe}...")
                        
                        # 获取测试数据
                        test_df = self.fetch_historical_data(coin, timeframe)
                        
                        if test_df is not None:
                            # 运行回测
                            result = self.backtest_model(coin, timeframe, test_df)
                            if result is not None:
                                all_results.append(result)
                    
                    except Exception as e:
                        logger.error(f"Error processing {coin} {timeframe}: {str(e)}")
                        continue
            
            # 生成报告
            self.generate_report(all_results)
            
            return {
                'total_models': len(coins) * len(timeframes),
                'tested_models': len(all_results),
                'results': all_results,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in full backtest: {str(e)}")
            return None
    
    def generate_report(self, results: List[Dict]):
        """生成回测报告"""
        try:
            if not results:
                logger.warning("No results to generate report")
                return
            
            # 计算统计信息
            dir_accs = [r['directional_accuracy'] for r in results]
            precisions_up = [r['precision_up'] for r in results]
            precisions_down = [r['precision_down'] for r in results]
            trade_rates = [r['trade_success_rate'] for r in results]
            
            report = {
                'total_models_tested': len(results),
                'avg_directional_accuracy': float(np.mean(dir_accs)),
                'avg_precision_up': float(np.mean(precisions_up)),
                'avg_precision_down': float(np.mean(precisions_down)),
                'avg_trade_success_rate': float(np.mean(trade_rates)),
                'best_accuracy_model': max(results, key=lambda x: x['directional_accuracy']),
                'worst_accuracy_model': min(results, key=lambda x: x['directional_accuracy']),
                'high_accuracy_models': [r for r in results if r['directional_accuracy'] > 0.55],
                'low_accuracy_models': [r for r in results if r['directional_accuracy'] < 0.50],
                'timestamp': datetime.now().isoformat()
            }
            
            self.accuracy_report = report
            
            # 保存报告
            report_file = f"{self.test_data_dir}/backtest_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info("=" * 60)
            logger.info("BACKTEST REPORT")
            logger.info("=" * 60)
            logger.info(f"Models Tested: {report['total_models_tested']}")
            logger.info(f"Avg Direction Accuracy: {report['avg_directional_accuracy']:.2%}")
            logger.info(f"Avg Precision UP: {report['avg_precision_up']:.2%}")
            logger.info(f"Avg Precision DOWN: {report['avg_precision_down']:.2%}")
            logger.info(f"Avg Trade Success Rate: {report['avg_trade_success_rate']:.2%}")
            logger.info(f"High Accuracy Models (>55%): {len(report['high_accuracy_models'])}")
            logger.info(f"Low Accuracy Models (<50%): {len(report['low_accuracy_models'])}")
            logger.info("=" * 60)
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return None
    
    def print_detailed_report(self):
        """打印详细报告"""
        if not self.accuracy_report:
            logger.warning("No report available")
            return
        
        report = self.accuracy_report
        
        print("\n" + "=" * 80)
        print("📊 DETAILED BACKTEST REPORT")
        print("=" * 80)
        
        print(f"\n📈 Overall Statistics:")
        print(f"  • Models Tested: {report['total_models_tested']}")
        print(f"  • Avg Direction Accuracy: {report['avg_directional_accuracy']:.2%}")
        print(f"  • Avg Precision UP: {report['avg_precision_up']:.2%}")
        print(f"  • Avg Precision DOWN: {report['avg_precision_down']:.2%}")
        print(f"  • Avg Trade Success Rate: {report['avg_trade_success_rate']:.2%}")
        
        print(f"\n🟢 Best Performing Model:")
        best = report['best_accuracy_model']
        print(f"  • {best['coin']} {best['timeframe']}")
        print(f"  • Direction Accuracy: {best['directional_accuracy']:.2%}")
        print(f"  • Precision UP: {best['precision_up']:.2%}")
        print(f"  • Precision DOWN: {best['precision_down']:.2%}")
        
        print(f"\n🔴 Worst Performing Model:")
        worst = report['worst_accuracy_model']
        print(f"  • {worst['coin']} {worst['timeframe']}")
        print(f"  • Direction Accuracy: {worst['directional_accuracy']:.2%}")
        print(f"  • Precision UP: {worst['precision_up']:.2%}")
        print(f"  • Precision DOWN: {worst['precision_down']:.2%}")
        
        print(f"\n✅ High Accuracy Models (>55%):")
        for model in report['high_accuracy_models']:
            print(f"  • {model['coin']} {model['timeframe']}: {model['directional_accuracy']:.2%}")
        
        print(f"\n❌ Low Accuracy Models (<50%):")
        for model in report['low_accuracy_models']:
            print(f"  • {model['coin']} {model['timeframe']}: {model['directional_accuracy']:.2%}")
        
        print("\n" + "=" * 80 + "\n")
