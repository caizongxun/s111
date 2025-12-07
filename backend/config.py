"""
【完整修復版本】config.py
- 修復 API Key/Secret（需您自行替換）
- 修復幣種列表（10 種支持的幣種）
- 修復幣種數量驗證
"""

# ======================== API 配置 ========================

# ⚠️ 重要：請替換為您的真實 Binance Testnet API Key
# 獲取方式：https://testnet.binancefutures.com/cn/futures/setting/myKey

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# ======================== 服務器配置 ========================

API_HOST = "0.0.0.0"

API_PORT = 8000

API_DEBUG = True

# ======================== 交易對配置 ========================

# 10 種幣種（修復版本 - 移除不支持的幣種）
COINS = [
    # 藍籌幣 (Tier 1)
    'BTCUSDT',      # Bitcoin - 市值最大的加密貨幣
    'ETHUSDT',      # Ethereum - 智能合約平台
    'BNBUSDT',      # Binance Coin - 幣安生態代幣
    
    # L2 / 新興 (Tier 2)
    'ADAUSDT',      # Cardano - POS 區塊鏈
    'SOLUSDT',      # Solana - 高速區塊鏈
    'DOGEUSDT',     # Dogecoin - 社區驅動的幣
    'MATICUSDT',    # Polygon - 以太坊 L2 解決方案
    'AVAXUSDT',     # Avalanche - 高性能區塊鏈
    
    # DeFi (Tier 3)
    'UNIUSDT',      # Uniswap - DEX 龍頭
    'LINKUSDT',     # Chainlink - 預言機龍頭
    
    # ✅ 已移除（Testnet 不支持）：
    # 'AAVEUSDT',   # ❌ Testnet 不支持
    # 'XRPUSDT',    # ❌ Testnet 不支持
    # 'LTCUSDT',    # ❌ Testnet 不支持
    # 'FTMUSDT',    # ❌ Testnet 不支持
]

# 驗證幣種數量
assert len(COINS) == 10, f"必須恰好 10 種幣種，目前有 {len(COINS)} 種"

# ======================== 時間框架配置 ========================

# 3 個主要時間框架
TIMEFRAMES = [
    '15m',  # 15 分鐘 - 超短線交易
    '1h',   # 1 小時 - 短線交易
    '4h',   # 4 小時 - 中短線交易
]

# 驗證時間框架數量
assert len(TIMEFRAMES) == 3, f"必須恰好 3 個時間框架，目前有 {len(TIMEFRAMES)} 個"

# ======================== 計算訓練規模 ========================

TOTAL_MODELS = len(COINS) * len(TIMEFRAMES)  # 30 個模型

# ======================== 模型訓練配置 ========================

LSTM_UNITS = 128

DROPOUT_RATE = 0.2

EPOCHS = 50

BATCH_SIZE = 32

LOOKBACK_PERIOD = 60

TRAIN_TEST_SPLIT = 0.8

VALIDATION_SPLIT = 0.1

MODELS_DIR = './backend/models'

# ======================== 信號閾值配置 ========================

# BUY 信號閾值
BUY_SIGNAL_THRESHOLD = 0.55  # 預測價格上升 55% 以上時發出買入信號

# SELL 信號閾值
SELL_SIGNAL_THRESHOLD = 0.55  # 預測價格下降 55% 以上時發出賣出信號

# ======================== 自動交易配置 ========================

# 置信度閾值（只有超過此值的信號才會自動交易）
AUTO_TRADE_CONFIDENCE_THRESHOLD = 0.60  # 60%

# 倉位管理
DEFAULT_POSITION_SIZE = 0.05  # 基礎倉位：賬戶的 5%

MAX_POSITION_SIZE = 0.2  # 最大倉位：賬戶的 20%

# 止損止盈設置
STOP_LOSS_PERCENT = 0.02  # 止損：2%

TAKE_PROFIT_PERCENT = 0.05  # 止盈：5%

# 交易歷史
TRADE_HISTORY_FILE = './trades_history.json'

# ======================== 數據配置 ========================

DATA_DIR = './backend/data'

TEST_DATA_DIR = './test_data'

# ======================== 回測配置 ========================

BACKTEST_K_LINES = 2000  # 回測時使用的 K 線數量

BACKTEST_MIN_DATA = 100  # 最少需要的 K 線數量

BACKTEST_REPORT_FILE = './test_data/backtest_report.json'

# ======================== API 限制配置 ========================

# Binance futures_klines 最多返回 1500 根 K 線
MAX_KLINES_PER_REQUEST = 1500

# 請求間隔（秒）
REQUEST_INTERVAL = 0.5

# ======================== 日誌配置 ========================

LOG_LEVEL = 'INFO'

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ======================== 監控配置 ========================

# 信號更新間隔（秒）
SIGNAL_UPDATE_INTERVAL = 60  # 每 60 秒更新一次信號

# 賬戶余額刷新間隔（秒）
BALANCE_UPDATE_INTERVAL = 300  # 每 5 分鐘更新一次

# ======================== 風險管理配置 ========================

# 最大同時持倉數
MAX_OPEN_POSITIONS = 5

# 每日最大虧損限制（賬戶百分比）
MAX_DAILY_LOSS_PERCENT = 0.05  # 5%

# 最大連續虧損交易數
MAX_CONSECUTIVE_LOSSES = 3

# ======================== 通知配置 ========================

# 是否啟用通知
ENABLE_NOTIFICATIONS = True

# Telegram 通知配置（可選）
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token"

TELEGRAM_CHAT_ID = "your_telegram_chat_id"

# ======================== 緩存配置 ========================

# 信號緩存時間（秒）
SIGNAL_CACHE_TTL = 300

# 模型緩存時間（秒）
MODEL_CACHE_TTL = 3600

# ======================== 其他配置 ========================

# 是否使用 Testnet
USE_TESTNET = True

# 最小交易金額（USDT）
MIN_TRADE_AMOUNT = 10

# 自動交易是否啟用
AUTO_TRADE_ENABLED = False  # 默認不自動交易，避免誤操作

# ======================== 訓練進度顯示 ========================

if __name__ != "__main__":
    # 只在導入時顯示一次，避免重複輸出
    print(f"""
╔════════════════════════════════════════════╗
║ 加密貨幣 LSTM 交易系統配置 ║
╠════════════════════════════════════════════╣
║ 幣種數量: {len(COINS):>2} 種 ║
║ 時間框架: {len(TIMEFRAMES):>2} 個 ║
║ 總模型數: {TOTAL_MODELS:>2} 個 ║
╠════════════════════════════════════════════╣
║ 幣種列表: ║
""")
    for i, coin in enumerate(COINS, 1):
        print(f"║ {i:>2}. {coin:<30} ║")
    
    print(f"""║ ║
║ 時間框架: ║
║ • {TIMEFRAMES[0]} - 超短線交易 ║
║ • {TIMEFRAMES[1]} - 短線交易 ║
║ • {TIMEFRAMES[2]} - 中短線交易 ║
╠════════════════════════════════════════════╣
║ API 服務器: {API_HOST}:{API_PORT} ║
║ 預估訓練時間: ~30-40 分鐘 (Testnet) ║
║ 預估文件數: 60 個 (模型 + scaler) ║
║ 預估磁盤空間: ~120 MB ║
╚════════════════════════════════════════════╝
""")

# ======================== 配置驗證 ========================

def validate_config():
    """驗證配置是否正確"""
    errors = []
    warnings = []
    
    # 檢查 API Key
    if BINANCE_API_KEY == "您的 Testnet API Key (必須替換)":
        errors.append("❌ BINANCE_API_KEY 未設置 - 必須替換為真實 Key!")
    
    if BINANCE_API_SECRET == "您的 Testnet API Secret (必須替換)":
        errors.append("❌ BINANCE_API_SECRET 未設置 - 必須替換為真實 Secret!")
    
    # 檢查幣種和時間框架
    if len(COINS) != 10:
        errors.append(f"❌ 幣種數量錯誤: {len(COINS)}, 應為 10")
    
    if len(TIMEFRAMES) != 3:
        errors.append(f"❌ 時間框架數量錯誤: {len(TIMEFRAMES)}, 應為 3")
    
    # 檢查參數有效性
    if not (0 < AUTO_TRADE_CONFIDENCE_THRESHOLD < 1):
        errors.append("❌ AUTO_TRADE_CONFIDENCE_THRESHOLD 必須在 0-1 之間")
    
    if not (0 < DEFAULT_POSITION_SIZE < MAX_POSITION_SIZE):
        errors.append("❌ DEFAULT_POSITION_SIZE 必須小於 MAX_POSITION_SIZE")
    
    return errors, warnings

# 在模塊加載時驗證配置
_errors, _warnings = validate_config()

if _warnings:
    print("\n⚠️ 配置警告:")
    for warning in _warnings:
        print(f" {warning}")

if _errors:
    print("\n❌ 配置錯誤:")
    for error in _errors:
        print(f" {error}")
    print("\n✅ 修復方法:")
    print("1. 訪問 https://testnet.binancefutures.com/cn/futures/setting/myKey")
    print("2. 生成新的 API Key 和 Secret")
    print("3. 替換 config.py 中的 BINANCE_API_KEY 和 BINANCE_API_SECRET")
