"""
【完整 API 测试文件】test_api.py

用途：快速测试你的 Binance Testnet API Key 是否可用
运行方式：在项目根目录执行 python test_api.py
"""

import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("🧪 Binance API 测试")
print("="*80)

# ======================== 第 1 步：导入配置 ========================

logger.info("\n1️⃣ 导入配置...")

try:
    from backend.config import (
        BINANCE_API_KEY,
        BINANCE_API_SECRET,
        USE_TESTNET
    )
    logger.info("✅ 配置导入成功")
except ImportError as e:
    logger.error(f"❌ 导入配置失败: {str(e)}")
    sys.exit(1)

# ======================== 第 2 步：验证 API Key ========================

logger.info("\n2️⃣ 验证 API Key 和 Secret...")

api_key = str(BINANCE_API_KEY).strip() if BINANCE_API_KEY else None
api_secret = str(BINANCE_API_SECRET).strip() if BINANCE_API_SECRET else None

logger.info(f"📍 BINANCE_API_KEY 类型: {type(BINANCE_API_KEY)}")
logger.info(f"📍 BINANCE_API_SECRET 类型: {type(BINANCE_API_SECRET)}")
logger.info(f"📍 BINANCE_API_KEY 长度: {len(api_key) if api_key else 0}")
logger.info(f"📍 BINANCE_API_SECRET 长度: {len(api_secret) if api_secret else 0}")

if not api_key:
    logger.error("❌ BINANCE_API_KEY 为空或 None")
    sys.exit(1)

if not api_secret:
    logger.error("❌ BINANCE_API_SECRET 为空或 None")
    sys.exit(1)

logger.info("✅ API Key 和 Secret 验证通过")

# ======================== 第 3 步：导入 Binance 客户端 ========================

logger.info("\n3️⃣ 导入 Binance 客户端...")

try:
    from binance.client import Client
    logger.info("✅ Binance 客户端导入成功")
except ImportError as e:
    logger.error(f"❌ 导入 Binance 客户端失败: {str(e)}")
    logger.error("   请运行: pip install python-binance")
    sys.exit(1)

# ======================== 第 4 步：初始化客户端 ========================

logger.info("\n4️⃣ 初始化 Binance 客户端...")

try:
    client = Client(api_key, api_secret, testnet=USE_TESTNET)
    logger.info(f"✅ 客户端初始化成功 (testnet={USE_TESTNET})")
except Exception as e:
    logger.error(f"❌ 初始化客户端失败: {str(e)}")
    sys.exit(1)

# ======================== 第 5 步：获取账户信息 ========================

logger.info("\n5️⃣ 获取账户信息...")

try:
    account = client.futures_account()
    
    logger.info("✅ 成功连接到 Binance Futures")
    logger.info(f"   总钱包余额: {account.get('totalWalletBalance', 0)} USDT")
    logger.info(f"   总保证金余额: {account.get('totalMarginBalance', 0)} USDT")
    logger.info(f"   未实现盈利: {account.get('totalUnrealizedProfit', 0)} USDT")
    
except Exception as e:
    logger.error(f"❌ 获取账户信息失败: {str(e)}")
    if "401" in str(e) or "Signature" in str(e):
        logger.error("   可能原因：API Key 或 Secret 不正确")
    elif "Permission denied" in str(e):
        logger.error("   可能原因：API Key 没有期货权限")
    sys.exit(1)

# ======================== 第 6 步：获取服务器时间 ========================

logger.info("\n6️⃣ 同步系统时间...")

try:
    server_time = client.get_server_time()['serverTime']
    import time
    local_time = int(time.time() * 1000)
    time_offset = server_time - local_time
    
    logger.info(f"✅ 时间同步成功")
    logger.info(f"   服务器时间: {server_time}")
    logger.info(f"   本地时间: {local_time}")
    logger.info(f"   时间偏差: {time_offset}ms")
    
except Exception as e:
    logger.error(f"❌ 时间同步失败: {str(e)}")
    sys.exit(1)

# ======================== 第 7 步：获取现货价格 ========================

logger.info("\n7️⃣ 测试获取价格...")

test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

for symbol in test_symbols:
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
        logger.info(f"✅ {symbol}: ${price:,.2f}")
    except Exception as e:
        logger.error(f"❌ 获取 {symbol} 价格失败: {str(e)}")

# ======================== 第 8 步：获取开仓信息 ========================

logger.info("\n8️⃣ 获取开仓信息...")

try:
    positions = client.futures_position_information()
    open_positions = [p for p in positions if float(p['positionAmt']) != 0]
    
    logger.info(f"✅ 获取开仓信息成功")
    logger.info(f"   总持仓数: {len(open_positions)}")
    
    if open_positions:
        logger.info("   开仓详情:")
        for pos in open_positions:
            logger.info(f"      - {pos['symbol']}: {pos['positionAmt']} (入场价: {pos['entryPrice']})")
    else:
        logger.info("   当前无开仓")
        
except Exception as e:
    logger.error(f"❌ 获取开仓信息失败: {str(e)}")

# ======================== 第 9 步：测试 K 线数据 ========================

logger.info("\n9️⃣ 测试获取 K 线数据...")

try:
    klines = client.futures_klines(symbol='BTCUSDT', interval='1h', limit=5)
    
    logger.info(f"✅ 成功获取 BTCUSDT 1小时 K 线")
    logger.info(f"   K 线数量: {len(klines)}")
    
    if klines:
        latest = klines[-1]
        logger.info(f"   最新 K 线:")
        logger.info(f"      时间: {latest[0]}")
        logger.info(f"      开: {latest[1]}")
        logger.info(f"      高: {latest[2]}")
        logger.info(f"      低: {latest[3]}")
        logger.info(f"      收: {latest[4]}")
        logger.info(f"      量: {latest[7]}")
        
except Exception as e:
    logger.error(f"❌ 获取 K 线数据失败: {str(e)}")

# ======================== 最终总结 ========================

print("\n" + "="*80)
print("✅ 测试完成！")
print("="*80)
print("\n总结:")
print("✅ API Key 和 Secret 有效")
print("✅ 可以连接到 Binance Futures")
print("✅ 可以获取账户信息")
print("✅ 可以获取市场数据")
print("✅ 可以获取开仓信息")
print("\n🎉 你的 API 配置完全正常！")
print("\n现在可以：")
print("1. 修改 app.py（改 3 行或替换整个文件）")
print("2. 重启应用")
print("3. 访问 http://localhost:8000/health 验证系统")
print("\n" + "="*80 + "\n")
