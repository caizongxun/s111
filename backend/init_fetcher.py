"""
【新增文件】init_fetcher.py - 数据获取器初始化模块

用途：
1. ✅ 初始化全局 BinanceDataFetcher
2. ✅ 验证 API Key 和账户信息
3. ✅ 供 app.py 的 startup() 调用
4. ✅ 可以独立运行获取账户信息（测试用）

运行方式：
- 作为模块：from backend.init_fetcher import init_data_fetcher
- 作为脚本：python init_fetcher.py（获取账户信息）
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

def init_data_fetcher():
    """
    初始化全局数据获取器
    
    Returns:
        BinanceDataFetcher: 初始化后的全局 fetcher 实例
        None: 如果初始化失败
    """
    
    try:
        print("\n" + "="*80)
        print("📥 初始化数据获取器...")
        print("="*80)
        
        # ✅ Step 1: 导入配置
        print("\n1️⃣ 导入配置...")
        try:
            from backend.config import (
                BINANCE_API_KEY,
                BINANCE_API_SECRET,
                USE_TESTNET
            )
            print("✅ 配置导入成功")
        except ImportError as e:
            logger.error(f"❌ 导入配置失败: {str(e)}")
            return None
        
        # ✅ Step 2: 验证 API Key
        print("\n2️⃣ 验证 API Key 和 Secret...")
        
        api_key = str(BINANCE_API_KEY).strip() if BINANCE_API_KEY else None
        api_secret = str(BINANCE_API_SECRET).strip() if BINANCE_API_SECRET else None
        
        print(f"📍 BINANCE_API_KEY 类型: {type(BINANCE_API_KEY)}")
        print(f"📍 BINANCE_API_SECRET 类型: {type(BINANCE_API_SECRET)}")
        print(f"📍 BINANCE_API_KEY 长度: {len(api_key) if api_key else 0}")
        print(f"📍 BINANCE_API_SECRET 长度: {len(api_secret) if api_secret else 0}")
        
        if not api_key:
            logger.error("❌ BINANCE_API_KEY 为空或 None")
            return None
        
        if not api_secret:
            logger.error("❌ BINANCE_API_SECRET 为空或 None")
            return None
        
        print("✅ API Key 和 Secret 验证通过")
        
        # ✅ Step 3: 初始化 BinanceDataFetcher
        print("\n3️⃣ 初始化 BinanceDataFetcher...")
        
        try:
            from backend.data_fetcher import BinanceDataFetcher
            
            fetcher = BinanceDataFetcher(
                api_key=api_key,
                api_secret=api_secret,
                testnet=USE_TESTNET
            )
            
            if not fetcher.is_initialized():
                logger.error("❌ BinanceDataFetcher 初始化失败")
                return None
            
            print("✅ BinanceDataFetcher 初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 初始化 BinanceDataFetcher 失败: {str(e)}")
            return None
        
        # ✅ Step 4: 初始化全局 fetcher
        print("\n4️⃣ 初始化全局数据获取器...")
        
        try:
            from backend.data_fetcher import init_fetcher
            
            global_fetcher = init_fetcher(api_key, api_secret, USE_TESTNET)
            print("✅ 全局数据获取器初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 初始化全局 fetcher 失败: {str(e)}")
            return None
        
        # ✅ Step 5: 测试账户连接
        print("\n5️⃣ 验证账户连接...")
        
        try:
            balance = global_fetcher.get_account_balance()
            
            if balance is None:
                logger.warning("⚠️ 无法获取账户信息")
            else:
                print("✅ 成功连接到 Binance Futures")
                print(f"   💰 总钱包余额: {balance.get('totalWalletBalance', 0):.2f} USDT")
                print(f"   📊 总保证金余额: {balance.get('totalMarginBalance', 0):.2f} USDT")
                print(f"   📈 未实现盈利: {balance.get('totalUnrealizedProfit', 0):.2f} USDT")
        
        except Exception as e:
            logger.warning(f"⚠️ 验证账户连接失败: {str(e)}")
        
        print("\n" + "="*80)
        print("✅ 数据获取器初始化完成！")
        print("="*80 + "\n")
        
        return global_fetcher
    
    except Exception as e:
        logger.error(f"❌ 初始化数据获取器失败: {str(e)}")
        return None


def get_account_info():
    """
    获取账户信息（可以独立运行）
    
    Returns:
        dict: 账户信息
    """
    
    print("\n" + "="*80)
    print("🧪 获取账户信息测试")
    print("="*80)
    
    try:
        # 初始化 fetcher
        fetcher = init_data_fetcher()
        
        if fetcher is None:
            print("❌ Fetcher 初始化失败")
            return None
        
        # 获取账户余额
        print("\n📊 获取账户余额...")
        balance = fetcher.get_account_balance()
        
        if balance:
            print("✅ 账户余额:")
            for key, value in balance.items():
                print(f"   {key}: {value:.2f}")
        
        # 获取开仓信息
        print("\n📈 获取开仓信息...")
        positions = fetcher.get_open_positions()
        
        if positions:
            print(f"✅ 开仓数: {len(positions)}")
            for pos in positions:
                print(f"   {pos['symbol']}: {pos['positionAmt']} (入场价: {pos['entryPrice']})")
        else:
            print("✅ 当前无开仓")
        
        # 获取服务器时间
        print("\n🕐 获取服务器时间...")
        server_time = fetcher.get_server_time()
        
        if server_time:
            print(f"✅ 服务器时间: {server_time}")
        
        print("\n" + "="*80)
        print("✅ 账户信息获取成功!")
        print("="*80 + "\n")
        
        return {
            'balance': balance,
            'positions': positions,
            'server_time': server_time
        }
    
    except Exception as e:
        logger.error(f"❌ 获取账户信息失败: {str(e)}")
        return None


# 主程序 - 可以独立运行
if __name__ == "__main__":
    import logging
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行获取账户信息
    get_account_info()
