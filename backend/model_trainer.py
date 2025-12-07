"""
完整的改進 LSTM 模型訓練器 - 支持動態幣種配置
自動訓練 config.py 中定義的所有幣種
修復預測時的數據格式問題
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import logging
from pathlib import Path
import pickle
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LSTMPricePredictor:
    """改進的 LSTM 價格預測模型 - 支持技術指標"""
    
    def __init__(self, coin_symbol: str, timeframe: str, lookback_period: int = 60):
        """初始化預測器"""
        self.coin_symbol = coin_symbol
        self.timeframe = timeframe
        self.lookback_period = lookback_period
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model_name = f"{coin_symbol}_{timeframe}"
        self.rmse = None
        self.mae = None
        self.feature_names = []
        
        # 創建模型目錄
        Path('./backend/models').mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized predictor for {self.model_name}")
    
    def get_feature_columns(self) -> list:
        """獲取要使用的特徵列"""
        features = [
            'close',           # 收盤價（必須）
            'rsi_14',         # RSI
            'macd',           # MACD
            'macd_signal',    # MACD 信號線
            'macd_hist',      # MACD 直方圖
            'bb_upper',       # 布林帶上軌
            'bb_middle',      # 布林帶中軌
            'bb_lower',       # 布林帶下軌
            'atr_14',         # ATR
            'volume_ma_20',   # 成交量 MA
            'roc_12',         # 價格變化率
            'close_ma_5',     # 價格 MA
            'close_std_5'     # 價格標準差
        ]
        return features
    
    def prepare_data(self, df: pd.DataFrame, sequence_length: int = 60):
        """準備數據 - 支持多個特徵"""
        try:
            # 獲取特徵列
            features = self.get_feature_columns()
            
            # 過濾存在的列
            available_features = [f for f in features if f in df.columns]
            
            # 如果缺少技術指標，至少用收盤價
            if len(available_features) == 0:
                available_features = ['close']
            
            self.feature_names = available_features
            logger.info(f"Using features: {available_features}")
            
            # 提取特徵數據
            data = df[available_features].values
            
            if data.size == 0:
                logger.error("No data available for training")
                return None, None, None, None
            
            # 標準化數據
            scaled_data = self.scaler.fit_transform(data)
            
            # 創建序列
            X, y = [], []
            for i in range(len(scaled_data) - sequence_length):
                X.append(scaled_data[i:i + sequence_length])
                # 目標是收盤價的下一個值（第一個特徵）
                y.append(scaled_data[i + sequence_length, 0])
            
            X = np.array(X)
            y = np.array(y)
            
            if len(X) == 0:
                logger.error("Not enough data to create sequences")
                return None, None, None, None
            
            # 分割數據 (80% 訓練, 20% 測試)
            split_index = int(len(X) * 0.8)
            X_train = X[:split_index]
            y_train = y[:split_index]
            X_test = X[split_index:]
            y_test = y[split_index:]
            
            logger.info(f"Data prepared: X_train {X_train.shape}, X_test {X_test.shape}")
            logger.info(f"Number of features: {X_train.shape[2]}")
            
            return X_train, y_train, X_test, y_test
        
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            return None, None, None, None
    
    def build_model(self, input_shape: tuple) -> Sequential:
        """構建 LSTM 模型"""
        try:
            model = Sequential([
                # 第一層 LSTM
                LSTM(
                    units=128,
                    return_sequences=True,
                    input_shape=input_shape,
                    activation='relu'
                ),
                Dropout(0.2),
                
                # 第二層 LSTM
                LSTM(
                    units=128,
                    return_sequences=True,
                    activation='relu'
                ),
                Dropout(0.2),
                
                # 第三層 LSTM
                LSTM(
                    units=64,
                    activation='relu'
                ),
                Dropout(0.2),
                
                # 全連接層
                Dense(units=64, activation='relu'),
                Dropout(0.1),
                
                Dense(units=32, activation='relu'),
                
                # 輸出層
                Dense(units=1)
            ])
            
            # 使用 Adam 優化器
            optimizer = keras.optimizers.Adam(learning_rate=0.001)
            model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
            
            logger.info("Model built successfully")
            logger.info(f"Model parameters: {model.count_params():,}")
            
            return model
        
        except Exception as e:
            logger.error(f"Error building model: {str(e)}")
            return None
    
    def train(self, df: pd.DataFrame, sequence_length: int = 60) -> dict:
        """訓練模型"""
        try:
            # 準備數據
            X_train, y_train, X_test, y_test = self.prepare_data(df, sequence_length)
            
            if X_train is None:
                logger.error("Failed to prepare data")
                return None
            
            # 構建模型
            self.model = self.build_model((X_train.shape[1], X_train.shape[2]))
            
            if self.model is None:
                return None
            
            # 早停
            early_stop = EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            )
            
            # 訓練
            logger.info(f"Training model for {self.model_name}...")
            logger.info(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")
            
            history = self.model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=32,
                validation_split=0.1,
                callbacks=[early_stop],
                verbose=1
            )
            
            # 評估
            y_pred = self.model.predict(X_test, verbose=0)
            
            # 反標準化用於計算誤差
            y_test_full = np.zeros((len(y_test), len(self.feature_names)))
            y_test_full[:, 0] = y_test
            y_pred_full = np.zeros((len(y_pred), len(self.feature_names)))
            y_pred_full[:, 0] = y_pred.flatten()
            
            y_test_original = self.scaler.inverse_transform(y_test_full)[:, 0]
            y_pred_original = self.scaler.inverse_transform(y_pred_full)[:, 0]
            
            # 計算指標
            self.rmse = np.sqrt(mean_squared_error(y_test_original, y_pred_original))
            self.mae = mean_absolute_error(y_test_original, y_pred_original)
            
            logger.info(f"✅ Model trained. RMSE: {self.rmse:.4f}, MAE: {self.mae:.4f}")
            
            # 保存模型
            self.save_model()
            
            return {
                'rmse': float(self.rmse),
                'mae': float(self.mae),
                'epochs': len(history.history['loss'])
            }
        
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return None
    
    def predict(self, recent_data: np.ndarray, steps_ahead: int = 1) -> list:
        """進行預測 - 修復數據格式問題"""
        try:
            if self.model is None:
                if not self.load_model():
                    logger.error("Model not found")
                    return None
            
            # 確保 recent_data 是二維的 (時間步, 特徵)
            if recent_data.ndim == 1:
                # 一維數組，需要轉換
                if len(self.feature_names) == 1:
                    # 只有一個特徵（收盤價）
                    recent_data_2d = recent_data.reshape(-1, 1)
                else:
                    # 多個特徵，無法從一維轉換，返回錯誤
                    logger.error(f"Input data dimension mismatch. Expected {len(self.feature_names)} features")
                    return None
            else:
                recent_data_2d = recent_data
            
            # 驗證特徵數量
            if recent_data_2d.shape[1] != len(self.feature_names):
                logger.error(f"Feature mismatch: expected {len(self.feature_names)}, got {recent_data_2d.shape[1]}")
                return None
            
            # 標準化
            recent_data_scaled = self.scaler.transform(recent_data_2d)
            
            # 確保有足夠的數據用於序列
            if len(recent_data_scaled) < 60:
                logger.warning(f"Data length {len(recent_data_scaled)} < 60, padding with zeros")
                padding = np.zeros((60 - len(recent_data_scaled), len(self.feature_names)))
                recent_data_scaled = np.vstack([padding, recent_data_scaled])
            
            # 預測
            predictions = []
            current_sequence = recent_data_scaled[-60:].reshape(1, 60, len(self.feature_names))
            
            for _ in range(steps_ahead):
                next_pred = self.model.predict(current_sequence, verbose=0)
                predictions.append(next_pred[0, 0])
                
                # 更新序列
                new_row = np.zeros((1, len(self.feature_names)))
                new_row[0, 0] = next_pred[0, 0]
                current_sequence = np.append(
                    current_sequence[0, 1:],
                    new_row,
                    axis=0
                ).reshape(1, 60, len(self.feature_names))
            
            # 反標準化
            predictions_array = np.zeros((len(predictions), len(self.feature_names)))
            predictions_array[:, 0] = predictions
            predictions_original = self.scaler.inverse_transform(predictions_array)[:, 0]
            
            return predictions_original.tolist()
        
        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}")
            return None
    
    def save_model(self):
        """保存模型和標準化器"""
        try:
            model_path = f"./backend/models/{self.model_name}_model.keras"
            scaler_path = f"./backend/models/{self.model_name}_scaler.pkl"
            
            self.model.save(model_path)
            
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            logger.info(f"✅ Model saved: {model_path}")
        
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
    
    def load_model(self) -> bool:
        """加載模型和標準化器"""
        try:
            model_path = f"./backend/models/{self.model_name}_model.keras"
            scaler_path = f"./backend/models/{self.model_name}_scaler.pkl"
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = keras.models.load_model(model_path)
                
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                # 重建特徵名稱
                self.feature_names = self.get_feature_columns()
                
                logger.info(f"Model loaded: {model_path}")
                return True
            else:
                logger.warning(f"Model files not found for {self.model_name}")
                return False
        
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False


class ModelManager:
    """管理多個模型"""
    
    def __init__(self):
        self.models = {}
    
    def get_or_create_model(self, coin: str, timeframe: str) -> LSTMPricePredictor:
        """獲取或創建模型"""
        key = f"{coin}_{timeframe}"
        if key not in self.models:
            self.models[key] = LSTMPricePredictor(coin, timeframe)
        return self.models[key]
    
    def train_all_models(self, data_dict: dict) -> dict:
        """
        訓練所有模型
        
        Args:
            data_dict: {'coin': {'timeframe': DataFrame, ...}, ...}
        
        Returns:
            {'total': int, 'success': int, 'failed': int, 'stats': {...}}
        """
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': time.time(),
            'models': {}
        }
        
        total_coins = len(data_dict)
        coin_idx = 0
        
        for coin, timeframes_data in data_dict.items():
            coin_idx += 1
            total_tfs = len(timeframes_data)
            tf_idx = 0
            
            for timeframe, df in timeframes_data.items():
                tf_idx += 1
                stats['total'] += 1
                
                model_name = f"{coin}_{timeframe}"
                pair_num = (coin_idx - 1) * total_tfs + tf_idx
                total_pairs = total_coins * total_tfs
                
                logger.info(f"\n[{pair_num}/{total_pairs}] Training {model_name}...")
                
                try:
                    if df is None or len(df) <= 100:
                        logger.warning(f"  ⚠️ Insufficient data for {model_name} ({len(df) if df is not None else 0} rows)")
                        stats['skipped'] += 1
                        continue
                    
                    # 訓練模型
                    model = self.get_or_create_model(coin, timeframe)
                    result = model.train(df)
                    
                    if result is not None:
                        stats['success'] += 1
                        stats['models'][model_name] = {
                            'rmse': result['rmse'],
                            'mae': result['mae'],
                            'epochs': result['epochs']
                        }
                        logger.info(f"  ✅ {model_name} trained successfully")
                    else:
                        stats['failed'] += 1
                        logger.error(f"  ❌ Failed to train {model_name}")
                
                except Exception as e:
                    logger.error(f"Error training {model_name}: {str(e)}")
                    stats['failed'] += 1
        
        stats['end_time'] = time.time()
        stats['duration_seconds'] = stats['end_time'] - stats['start_time']
        stats['duration_minutes'] = stats['duration_seconds'] / 60
        
        return stats


def main():
    """主函數 - 訓練所有模型"""
    from backend.data_fetcher import BinanceDataFetcher
    from backend.config import BINANCE_API_KEY, BINANCE_API_SECRET, COINS, TIMEFRAMES
    
    logger.info("="*80)
    logger.info("🚀 LSTM 模型訓練系統")
    logger.info("="*80)
    logger.info(f"配置: {len(COINS)} 幣種 × {len(TIMEFRAMES)} 時間框架 = {len(COINS) * len(TIMEFRAMES)} 個模型")
    logger.info("="*80 + "\n")
    
    # 初始化數據獲取
    fetcher = BinanceDataFetcher(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_API_SECRET,
        testnet=True
    )
    
    # 獲取數據
    logger.info("📌 步驟 1: 獲取數據...")
    all_data = fetcher.fetch_all_data()
    
    # 初始化模型管理器
    manager = ModelManager()
    
    # 訓練所有模型
    logger.info("\n📌 步驟 2: 訓練模型...")
    stats = manager.train_all_models(all_data)
    
    # 輸出統計
    logger.info("\n" + "="*80)
    logger.info("📊 訓練統計")
    logger.info("="*80)
    logger.info(f"總數: {stats['total']}")
    logger.info(f"✅ 成功: {stats['success']}")
    logger.info(f"❌ 失敗: {stats['failed']}")
    logger.info(f"⏭️  跳過: {stats['skipped']}")
    logger.info(f"⏱️  耗時: {stats['duration_minutes']:.2f} 分鐘")
    logger.info("="*80)
    
    logger.info("\n✅ 所有訓練完成！")
    logger.info("下一步: python run-backtest.py")


if __name__ == "__main__":
    main()
