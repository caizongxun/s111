#!/usr/bin/env python
"""
训练所有模型的脚本
必须在回测前运行此脚本
"""

import sys
import logging
from pathlib import Path
import time

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


def main():
    """主函数 - 训练所有模型"""
    
    logger.info("=" * 80)
    logger.info("🚀 STARTING MODEL TRAINING")
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
        
        # 2. 获取数据
        logger.info("\n📌 Step 2: Fetching training data...")
        all_data = data_fetcher.fetch_all_data()
        logger.info(f"✅ Data fetched for {len(all_data)} coins")
        
        # 3. 训练所有模型
        logger.info("\n📌 Step 3: Training all models...")
        logger.info("This will take several minutes...\n")
        
        trained_count = 0
        failed_count = 0
        
        total_models = len(COINS) * len(TIMEFRAMES)
        
        for coin_idx, coin in enumerate(COINS, 1):
            for tf_idx, timeframe in enumerate(TIMEFRAMES, 1):
                model_num = (coin_idx - 1) * len(TIMEFRAMES) + tf_idx
                
                try:
                    logger.info(f"\n[{model_num}/{total_models}] Training {coin} {timeframe}...")
                    
                    # 获取数据
                    if coin not in all_data or timeframe not in all_data[coin]:
                        logger.warning(f"  ⚠️ No data for {coin} {timeframe}, skipping...")
                        failed_count += 1
                        continue
                    
                    df = all_data[coin][timeframe]
                    
                    if df is None or len(df) < 100:
                        logger.warning(f"  ⚠️ Insufficient data for {coin} {timeframe} ({len(df) if df is not None else 0} rows)")
                        failed_count += 1
                        continue
                    
                    # 获取或创建模型
                    model = model_manager.get_or_create_model(coin, timeframe)
                    
                    # 训练模型
                    start_time = time.time()
                    history = model.train(df, epochs=20, batch_size=32)
                    elapsed = time.time() - start_time
                    
                    if history:
                        # 保存模型
                        model.save_model()
                        
                        train_loss = history.history['loss'][-1]
                        logger.info(f"  ✅ Training completed in {elapsed:.2f}s")
                        logger.info(f"     Final loss: {train_loss:.6f}")
                        
                        trained_count += 1
                    else:
                        logger.warning(f"  ❌ Training failed for {coin} {timeframe}")
                        failed_count += 1
                
                except Exception as e:
                    logger.error(f"  ❌ Error training {coin} {timeframe}: {str(e)}")
                    failed_count += 1
                    continue
        
        # 4. 生成报告
        logger.info("\n" + "=" * 80)
        logger.info("📊 TRAINING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✅ Successfully trained: {trained_count}/{total_models}")
        logger.info(f"❌ Failed: {failed_count}/{total_models}")
        logger.info(f"📈 Success rate: {(trained_count/total_models)*100:.1f}%")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ MODEL TRAINING COMPLETE!")
        logger.info("=" * 80)
        logger.info("\n💡 Next steps:")
        logger.info("   1. Run backtest to evaluate models: python run-backtest.py")
        logger.info("   2. Review the backtest report")
        logger.info("   3. Adjust confidence threshold based on results")
        logger.info("   4. Start auto trading\n")
    
    except KeyboardInterrupt:
        logger.info("\n⚠️ Training interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error during training: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
