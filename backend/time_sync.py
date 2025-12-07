"""
時間同步守護程序 - 防止時間偏差導致的 API 錯誤
"""

import logging
import time
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class TimeSync:
    """時間同步管理器 - 保持系統時間與服務器同步"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.client = None
        self.time_offset = 0
        self.last_sync = 0
        self.sync_interval = 300  # 每 5 分鐘同步一次
        self._initialized = True
        
        logger.info("✅ TimeSync initialized")
    
    def init_with_client(self, client):
        """初始化並綁定 Binance 客戶端"""
        self.client = client
        self.sync_time()
    
    def sync_time(self):
        """
        同步系統時間與 Binance 服務器時間
        """
        try:
            if self.client is None:
                logger.warning("⚠️ Client not initialized for time sync")
                return False
            
            logger.info("🔄 開始同步系統時間...")
            
            # 獲取服務器時間
            server_time_ms = self.client.get_server_time()['serverTime']
            local_time_ms = int(time.time() * 1000)
            
            # 計算時間差
            self.time_offset = server_time_ms - local_time_ms
            self.last_sync = time.time()
            
            # 轉換為秒顯示
            offset_sec = self.time_offset / 1000
            
            if self.time_offset == 0:
                logger.info("✅ 系統時間與服務器完全同步")
            elif abs(self.time_offset) <= 100:
                logger.info(f"✅ 時間同步完成，偏差: {self.time_offset}ms (可接受)")
            elif abs(self.time_offset) <= 1000:
                logger.warning(f"⚠️ 時間偏差: {offset_sec:.1f}s (較小，應可接受)")
            else:
                logger.error(f"❌ 時間偏差: {offset_sec:.1f}s (過大，可能導致 API 失敗)")
                logger.error("   建議: 檢查系統時間設置")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ 時間同步失敗: {str(e)}")
            return False
    
    def get_server_time(self) -> int:
        """
        獲取當前的服務器時間戳 (毫秒)
        
        Returns:
            服務器時間戳 (毫秒)
        """
        local_time_ms = int(time.time() * 1000)
        server_time_ms = local_time_ms + self.time_offset
        return server_time_ms
    
    def need_resync(self) -> bool:
        """
        檢查是否需要重新同步
        
        Returns:
            是否需要重新同步
        """
        if self.last_sync == 0:
            return True
        
        elapsed = time.time() - self.last_sync
        return elapsed > self.sync_interval
    
    def auto_sync(self):
        """自動同步（如果需要）"""
        if self.need_resync():
            self.sync_time()


# 全局實例
_time_sync = TimeSync()


def get_time_sync() -> TimeSync:
    """獲取全局時間同步實例"""
    return _time_sync


def init_time_sync(client):
    """初始化時間同步"""
    ts = get_time_sync()
    ts.init_with_client(client)
    return ts
