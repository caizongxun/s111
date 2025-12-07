#!/usr/bin/env python
"""
独立运行脚本：回测所有模型
直接运行此脚本测试现有模型的真实准确度
"""

import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from config import COINS, TIMEFRAMES, BINANCE_API_KEY, BINANCE_API_SECRET
from data_fetcher import BinanceDataFetcher
from model_trainer import ModelManager
from backtest_validator import BacktestValidator


def main():
    """主函数 - 运行完整回测"""
    
    logger.info("=" * 80)
    logger.info("🚀 STARTING BACKTEST VALIDATION")
    logger.info("=" * 80)
    
    try:
        # 1. 初始化系统
        logger.info("\n📌 Step 1: Initializing system...")
        data_fetcher = BinanceDataFetcher(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            testnet=True
        )
        model_manager = ModelManager()
        
        logger.info(f"✅ System initialized")
        logger.info(f"   Coins: {len(COINS)}")
        logger.info(f"   Timeframes: {len(TIMEFRAMES)}")
        logger.info(f"   Total Models: {len(COINS) * len(TIMEFRAMES)}")
        
        # 2. 初始化回测验证器
        logger.info("\n📌 Step 2: Initializing backtest validator...")
        validator = BacktestValidator(
            data_fetcher=data_fetcher,
            model_manager=model_manager,
            test_data_dir="./test_data"
        )
        logger.info("✅ Backtest validator ready")
        
        # 3. 获取 2000 根 K 线测试数据
        logger.info("\n📌 Step 3: Fetching 2000 K-lines historical data...")
        logger.info("   This may take a few minutes...")
        
        test_results = validator.run_full_backtest(
            coins=COINS,
            timeframes=TIMEFRAMES,
            fetch_new=False   # 重新下载 2000 根 K 线
        )
        
        # 4. 生成详细报告
        logger.info("\n📌 Step 4: Generating detailed report...")
        validator.print_detailed_report()
        
        # 5. 保存结果
        logger.info("\n📌 Step 5: Saving results...")
        report_file = "./test_data/backtest_report.json"
        logger.info(f"✅ Report saved to: {report_file}")
        
        # 6. 汇总
        logger.info("\n" + "=" * 80)
        logger.info("📊 BACKTEST SUMMARY")
        logger.info("=" * 80)
        
        if test_results:
            results = test_results['results']
            
            if results:
                # 按准确度排序
                sorted_results = sorted(
                    results, 
                    key=lambda x: x['directional_accuracy'], 
                    reverse=True
                )
                
                logger.info(f"\n✅ Total Models Tested: {len(results)}/{test_results['total_models']}")
                logger.info("\n🏆 TOP 5 BEST MODELS:")
                for i, model in enumerate(sorted_results[:5], 1):
                    print(f"\n  {i}. {model['coin']} {model['timeframe']}")
                    print(f"     Direction Accuracy: {model['directional_accuracy']:.2%}")
                    print(f"     Precision UP: {model['precision_up']:.2%}")
                    print(f"     Precision DOWN: {model['precision_down']:.2%}")
                    print(f"     Trade Success: {model['trade_success_rate']:.2%}")
                    print(f"     RMSE: {model['rmse']:.4f}")
                    print(f"     MAE: {model['mae']:.4f}")
                
                logger.info("\n🔴 BOTTOM 5 WORST MODELS:")
                for i, model in enumerate(sorted_results[-5:], 1):
                    print(f"\n  {i}. {model['coin']} {model['timeframe']}")
                    print(f"     Direction Accuracy: {model['directional_accuracy']:.2%}")
                    print(f"     Precision UP: {model['precision_up']:.2%}")
                    print(f"     Precision DOWN: {model['precision_down']:.2%}")
                    print(f"     Trade Success: {model['trade_success_rate']:.2%}")
                    print(f"     RMSE: {model['rmse']:.4f}")
                    print(f"     MAE: {model['mae']:.4f}")
                
                # 统计汇总
                report = validator.accuracy_report
                logger.info("\n📈 STATISTICS:")
                print(f"\n  平均方向准确度: {report['avg_directional_accuracy']:.2%}")
                print(f"  平均买入信号准确率: {report['avg_precision_up']:.2%}")
                print(f"  平均卖出信号准确率: {report['avg_precision_down']:.2%}")
                print(f"  平均交易成功率: {report['avg_trade_success_rate']:.2%}")
                print(f"  高精度模型 (>55%): {len(report['high_accuracy_models'])} 个")
                print(f"  低精度模型 (<50%): {len(report['low_accuracy_models'])} 个")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ BACKTEST VALIDATION COMPLETE!")
        logger.info("=" * 80)
        logger.info("\n📁 Test data saved in: ./test_data/")
        logger.info("📄 Report saved as: ./test_data/backtest_report.json")
        logger.info("\n💡 Next steps:")
        logger.info("   1. Review the accuracy report")
        logger.info("   2. Only use models with >55% directional accuracy")
        logger.info("   3. Adjust confidence threshold based on results")
        logger.info("   4. Set BUY/SELL_SIGNAL_THRESHOLD to 0.55 or higher\n")
    
    except KeyboardInterrupt:
        logger.info("\n⚠️ Backtest interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error during backtest: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
