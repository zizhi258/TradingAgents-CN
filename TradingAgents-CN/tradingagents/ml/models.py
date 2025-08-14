"""Model Training Pipeline for Stock Market Analysis

This module provides comprehensive model training capabilities for
stock market prediction tasks including price prediction, signal
classification, volatility modeling, and risk assessment.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import pickle
import joblib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    
try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.svm import SVR, SVC
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split, TimeSeriesSplit
    from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

# Import logging system
from tradingagents.utils.logging_init import get_logger
logger = get_logger("model_training")


@dataclass
class ModelConfig:
    """Configuration for model training"""
    model_type: str = "random_forest"  # "lstm", "transformer", "xgboost", "random_forest"
    task_type: str = "regression"  # "regression", "classification"
    target_variable: str = "future_return_5d"
    lookback_window: int = 60
    prediction_horizon: int = 5
    train_test_split: float = 0.8
    validation_split: float = 0.2
    random_state: int = 42
    
    # Model-specific parameters
    lstm_hidden_size: int = 128
    lstm_num_layers: int = 2
    lstm_dropout: float = 0.2
    
    transformer_d_model: int = 128
    transformer_nhead: int = 8
    transformer_num_layers: int = 4
    
    rf_n_estimators: int = 100
    rf_max_depth: int = 10
    
    xgb_n_estimators: int = 100
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.01
    
    # Training parameters
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    

class BaseModel(ABC):
    """Base class for all models"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.training_history = {}
        
    @abstractmethod
    def build_model(self, input_shape: Tuple) -> Any:
        """Build the model architecture"""
        pass
        
    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the model"""
        pass
        
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        pass
        
    def save_model(self, filepath: str) -> None:
        """Save the trained model"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'config': self.config,
            'training_history': self.training_history,
            'is_trained': self.is_trained
        }
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
        
    def load_model(self, filepath: str) -> None:
        """Load a trained model"""
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.config = model_data.get('config', self.config)
        self.training_history = model_data.get('training_history', {})
        self.is_trained = model_data.get('is_trained', True)
        logger.info(f"Model loaded from {filepath}")
        
    def prepare_data(self, X: np.ndarray, y: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training/prediction"""
        # Scale features
        if y is not None:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = self.scaler.transform(X)
            
        return X_scaled, y


class LSTMModel(BaseModel):
    """LSTM model for time series prediction"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch is required for LSTM model")
            
    def build_model(self, input_shape: Tuple) -> nn.Module:
        """Build LSTM model architecture"""
        
        class LSTMNet(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, output_size, dropout=0.2):
                super(LSTMNet, self).__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers
                
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                                  batch_first=True, dropout=dropout)
                self.fc = nn.Linear(hidden_size, output_size)
                self.dropout = nn.Dropout(dropout)
                
            def forward(self, x):
                h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
                c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
                
                lstm_out, _ = self.lstm(x, (h0, c0))
                lstm_out = self.dropout(lstm_out[:, -1, :])  # Take last output
                output = self.fc(lstm_out)
                return output
                
        input_size = input_shape[1]  # Number of features
        output_size = 1 if self.config.task_type == "regression" else len(np.unique([0, 1, 2]))  # Placeholder
        
        model = LSTMNet(
            input_size=input_size,
            hidden_size=self.config.lstm_hidden_size,
            num_layers=self.config.lstm_num_layers,
            output_size=output_size,
            dropout=self.config.lstm_dropout
        )
        
        return model
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the LSTM model"""
        logger.info("Training LSTM model")
        
        # Prepare data
        X_scaled, y = self.prepare_data(X, y)
        
        # Reshape for LSTM (samples, sequence_length, features)
        X_reshaped = self._reshape_for_lstm(X_scaled)
        
        # Split data
        split_idx = int(len(X_reshaped) * self.config.train_test_split)
        X_train, X_val = X_reshaped[:split_idx], X_reshaped[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Build model
        input_shape = (X_reshaped.shape[1], X_reshaped.shape[2])
        self.model = self.build_model(input_shape)
        
        # Prepare for training
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        
        criterion = nn.MSELoss() if self.config.task_type == "regression" else nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train).to(device)
        y_train_tensor = torch.FloatTensor(y_train).to(device)
        X_val_tensor = torch.FloatTensor(X_val).to(device)
        y_val_tensor = torch.FloatTensor(y_val).to(device)
        
        # Training loop
        train_losses = []
        val_losses = []
        
        for epoch in range(self.config.epochs):
            self.model.train()
            
            # Training
            optimizer.zero_grad()
            outputs = self.model(X_train_tensor)
            
            if self.config.task_type == "regression":
                outputs = outputs.squeeze()
            
            loss = criterion(outputs, y_train_tensor)
            loss.backward()
            optimizer.step()
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val_tensor)
                if self.config.task_type == "regression":
                    val_outputs = val_outputs.squeeze()
                val_loss = criterion(val_outputs, y_val_tensor)
            
            train_losses.append(loss.item())
            val_losses.append(val_loss.item())
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}/{self.config.epochs}, Train Loss: {loss.item():.4f}, Val Loss: {val_loss.item():.4f}")
        
        self.is_trained = True
        self.training_history = {
            'train_losses': train_losses,
            'val_losses': val_losses
        }
        
        return self.training_history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with LSTM model"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        X_scaled, _ = self.prepare_data(X)
        X_reshaped = self._reshape_for_lstm(X_scaled)
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        X_tensor = torch.FloatTensor(X_reshaped).to(device)
        
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(X_tensor)
            
        return predictions.cpu().numpy()
    
    def _reshape_for_lstm(self, X: np.ndarray) -> np.ndarray:
        """Reshape data for LSTM input"""
        samples = X.shape[0] - self.config.lookback_window + 1
        features = X.shape[1]
        
        X_reshaped = np.zeros((samples, self.config.lookback_window, features))
        
        for i in range(samples):
            X_reshaped[i] = X[i:i + self.config.lookback_window]
            
        return X_reshaped


class TransformerModel(BaseModel):
    """Transformer model for time series prediction"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch is required for Transformer model")
            
    def build_model(self, input_shape: Tuple) -> nn.Module:
        """Build Transformer model architecture"""
        
        class TransformerNet(nn.Module):
            def __init__(self, input_size, d_model, nhead, num_layers, output_size, dropout=0.1):
                super(TransformerNet, self).__init__()
                self.d_model = d_model
                self.input_projection = nn.Linear(input_size, d_model)
                
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model, nhead=nhead, dropout=dropout, batch_first=True
                )
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
                
                self.fc = nn.Linear(d_model, output_size)
                self.dropout = nn.Dropout(dropout)
                
            def forward(self, x):
                x = self.input_projection(x)
                x = x * np.sqrt(self.d_model)  # Scale
                
                transformer_out = self.transformer(x)
                
                # Global average pooling
                pooled = transformer_out.mean(dim=1)
                pooled = self.dropout(pooled)
                
                output = self.fc(pooled)
                return output
                
        input_size = input_shape[1]  # Number of features
        output_size = 1 if self.config.task_type == "regression" else len(np.unique([0, 1, 2]))  # Placeholder
        
        model = TransformerNet(
            input_size=input_size,
            d_model=self.config.transformer_d_model,
            nhead=self.config.transformer_nhead,
            num_layers=self.config.transformer_num_layers,
            output_size=output_size
        )
        
        return model
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the Transformer model"""
        logger.info("Training Transformer model")
        
        # Similar to LSTM training but with different architecture
        # Implementation follows similar pattern as LSTM
        
        # Prepare data
        X_scaled, y = self.prepare_data(X, y)
        X_reshaped = self._reshape_for_transformer(X_scaled)
        
        # Split data
        split_idx = int(len(X_reshaped) * self.config.train_test_split)
        X_train, X_val = X_reshaped[:split_idx], X_reshaped[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Build model
        input_shape = (X_reshaped.shape[1], X_reshaped.shape[2])
        self.model = self.build_model(input_shape)
        
        # Training setup
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        
        criterion = nn.MSELoss() if self.config.task_type == "regression" else nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train).to(device)
        y_train_tensor = torch.FloatTensor(y_train).to(device)
        X_val_tensor = torch.FloatTensor(X_val).to(device)
        y_val_tensor = torch.FloatTensor(y_val).to(device)
        
        # Training loop (similar to LSTM)
        train_losses = []
        val_losses = []
        
        for epoch in range(self.config.epochs):
            self.model.train()
            
            optimizer.zero_grad()
            outputs = self.model(X_train_tensor)
            
            if self.config.task_type == "regression":
                outputs = outputs.squeeze()
            
            loss = criterion(outputs, y_train_tensor)
            loss.backward()
            optimizer.step()
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val_tensor)
                if self.config.task_type == "regression":
                    val_outputs = val_outputs.squeeze()
                val_loss = criterion(val_outputs, y_val_tensor)
            
            train_losses.append(loss.item())
            val_losses.append(val_loss.item())
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}/{self.config.epochs}, Train Loss: {loss.item():.4f}, Val Loss: {val_loss.item():.4f}")
        
        self.is_trained = True
        self.training_history = {
            'train_losses': train_losses,
            'val_losses': val_losses
        }
        
        return self.training_history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with Transformer model"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        X_scaled, _ = self.prepare_data(X)
        X_reshaped = self._reshape_for_transformer(X_scaled)
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        X_tensor = torch.FloatTensor(X_reshaped).to(device)
        
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(X_tensor)
            
        return predictions.cpu().numpy()
    
    def _reshape_for_transformer(self, X: np.ndarray) -> np.ndarray:
        """Reshape data for Transformer input"""
        # Same as LSTM reshape
        return self._reshape_for_lstm(X)
    
    def _reshape_for_lstm(self, X: np.ndarray) -> np.ndarray:
        """Reshape data for sequence input"""
        samples = X.shape[0] - self.config.lookback_window + 1
        features = X.shape[1]
        
        X_reshaped = np.zeros((samples, self.config.lookback_window, features))
        
        for i in range(samples):
            X_reshaped[i] = X[i:i + self.config.lookback_window]
            
        return X_reshaped


class XGBoostModel(BaseModel):
    """XGBoost model for stock prediction"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost is required for XGBoost model")
            
    def build_model(self, input_shape: Tuple) -> Any:
        """Build XGBoost model"""
        if self.config.task_type == "regression":
            model = xgb.XGBRegressor(
                n_estimators=self.config.xgb_n_estimators,
                max_depth=self.config.xgb_max_depth,
                learning_rate=self.config.xgb_learning_rate,
                random_state=self.config.random_state,
                n_jobs=-1
            )
        else:
            model = xgb.XGBClassifier(
                n_estimators=self.config.xgb_n_estimators,
                max_depth=self.config.xgb_max_depth,
                learning_rate=self.config.xgb_learning_rate,
                random_state=self.config.random_state,
                n_jobs=-1
            )
        return model
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the XGBoost model"""
        logger.info("Training XGBoost model")
        
        # Prepare data
        X_scaled, y = self.prepare_data(X, y)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=1-self.config.train_test_split, 
            random_state=self.config.random_state, shuffle=False
        )
        
        # Build and train model
        self.model = self.build_model(X_scaled.shape)
        
        # Train with validation
        eval_set = [(X_train, y_train), (X_val, y_val)]
        
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            early_stopping_rounds=self.config.early_stopping_patience,
            verbose=False
        )
        
        self.is_trained = True
        
        # Get training history
        train_score = self.model.score(X_train, y_train)
        val_score = self.model.score(X_val, y_val)
        
        self.training_history = {
            'train_score': train_score,
            'val_score': val_score,
            'feature_importance': self.model.feature_importances_
        }
        
        logger.info(f"XGBoost training completed. Train score: {train_score:.4f}, Val score: {val_score:.4f}")
        
        return self.training_history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with XGBoost model"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        X_scaled, _ = self.prepare_data(X)
        predictions = self.model.predict(X_scaled)
        
        return predictions


class RandomForestModel(BaseModel):
    """Random Forest model for stock prediction"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for Random Forest model")
            
    def build_model(self, input_shape: Tuple) -> Any:
        """Build Random Forest model"""
        if self.config.task_type == "regression":
            model = RandomForestRegressor(
                n_estimators=self.config.rf_n_estimators,
                max_depth=self.config.rf_max_depth,
                random_state=self.config.random_state,
                n_jobs=-1
            )
        else:
            model = RandomForestClassifier(
                n_estimators=self.config.rf_n_estimators,
                max_depth=self.config.rf_max_depth,
                random_state=self.config.random_state,
                n_jobs=-1
            )
        return model
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the Random Forest model"""
        logger.info("Training Random Forest model")
        
        # Prepare data
        X_scaled, y = self.prepare_data(X, y)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=1-self.config.train_test_split, 
            random_state=self.config.random_state, shuffle=False
        )
        
        # Build and train model
        self.model = self.build_model(X_scaled.shape)
        self.model.fit(X_train, y_train)
        
        self.is_trained = True
        
        # Get training history
        train_score = self.model.score(X_train, y_train)
        val_score = self.model.score(X_val, y_val)
        
        self.training_history = {
            'train_score': train_score,
            'val_score': val_score,
            'feature_importance': self.model.feature_importances_
        }
        
        logger.info(f"Random Forest training completed. Train score: {train_score:.4f}, Val score: {val_score:.4f}")
        
        return self.training_history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with Random Forest model"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        X_scaled, _ = self.prepare_data(X)
        predictions = self.model.predict(X_scaled)
        
        return predictions


# Specialized Models for Different Tasks

class PricePredictionModel:
    """Specialized model for stock price prediction"""
    
    def __init__(self, model_type: str = "xgboost", **kwargs):
        config = ModelConfig(
            model_type=model_type,
            task_type="regression",
            target_variable="future_return_5d",
            **kwargs
        )
        
        self.model = self._create_model(config)
        
    def _create_model(self, config: ModelConfig) -> BaseModel:
        """Create the appropriate model based on config"""
        if config.model_type == "lstm":
            return LSTMModel(config)
        elif config.model_type == "transformer":
            return TransformerModel(config)
        elif config.model_type == "xgboost":
            return XGBoostModel(config)
        elif config.model_type == "random_forest":
            return RandomForestModel(config)
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
    
    def train(self, features: pd.DataFrame, target: pd.Series) -> Dict:
        """Train the price prediction model"""
        return self.model.train(features.values, target.values)
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Predict future price movements"""
        return self.model.predict(features.values)
    
    def save(self, filepath: str) -> None:
        """Save the model"""
        self.model.save_model(filepath)
    
    def load(self, filepath: str) -> None:
        """Load the model"""
        self.model.load_model(filepath)


class TradingSignalClassifier:
    """Specialized model for trading signal classification (Buy/Hold/Sell)"""
    
    def __init__(self, model_type: str = "xgboost", **kwargs):
        config = ModelConfig(
            model_type=model_type,
            task_type="classification",
            target_variable="trading_signal",
            **kwargs
        )
        
        self.model = self._create_model(config)
        self.label_encoder = LabelEncoder()
        
    def _create_model(self, config: ModelConfig) -> BaseModel:
        """Create the appropriate model based on config"""
        if config.model_type == "lstm":
            return LSTMModel(config)
        elif config.model_type == "transformer":
            return TransformerModel(config)
        elif config.model_type == "xgboost":
            return XGBoostModel(config)
        elif config.model_type == "random_forest":
            return RandomForestModel(config)
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
    
    def create_trading_signals(self, returns: pd.Series, buy_threshold: float = 0.02, 
                             sell_threshold: float = -0.02) -> pd.Series:
        """Create trading signals from returns"""
        signals = pd.Series(index=returns.index, dtype=str)
        signals[returns > buy_threshold] = 'BUY'
        signals[returns < sell_threshold] = 'SELL'
        signals[(returns >= sell_threshold) & (returns <= buy_threshold)] = 'HOLD'
        
        return signals
    
    def train(self, features: pd.DataFrame, signals: pd.Series) -> Dict:
        """Train the trading signal classifier"""
        # Encode signals
        encoded_signals = self.label_encoder.fit_transform(signals)
        
        return self.model.train(features.values, encoded_signals)
    
    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict trading signals"""
        predictions = self.model.predict(features.values)
        
        # Decode predictions
        if hasattr(predictions, 'argmax'):  # For neural networks
            predictions = predictions.argmax(axis=1)
            
        decoded_predictions = self.label_encoder.inverse_transform(predictions.astype(int))
        
        return pd.Series(decoded_predictions, index=features.index)
    
    def save(self, filepath: str) -> None:
        """Save the model"""
        model_data = {
            'model': self.model,
            'label_encoder': self.label_encoder
        }
        joblib.dump(model_data, filepath)
    
    def load(self, filepath: str) -> None:
        """Load the model"""
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.label_encoder = model_data['label_encoder']


class VolatilityModel:
    """Specialized model for volatility prediction"""
    
    def __init__(self, model_type: str = "xgboost", **kwargs):
        config = ModelConfig(
            model_type=model_type,
            task_type="regression",
            target_variable="future_volatility",
            **kwargs
        )
        
        self.model = self._create_model(config)
        
    def _create_model(self, config: ModelConfig) -> BaseModel:
        """Create the appropriate model based on config"""
        if config.model_type == "lstm":
            return LSTMModel(config)
        elif config.model_type == "transformer":
            return TransformerModel(config)
        elif config.model_type == "xgboost":
            return XGBoostModel(config)
        elif config.model_type == "random_forest":
            return RandomForestModel(config)
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
    
    def calculate_volatility(self, returns: pd.Series, window: int = 20) -> pd.Series:
        """Calculate rolling volatility"""
        return returns.rolling(window=window).std() * np.sqrt(252)  # Annualized
    
    def train(self, features: pd.DataFrame, returns: pd.Series) -> Dict:
        """Train the volatility model"""
        # Calculate target volatility
        volatility = self.calculate_volatility(returns)
        
        # Align features and target
        aligned_features, aligned_volatility = features.align(volatility, join='inner')
        
        return self.model.train(aligned_features.values, aligned_volatility.values)
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Predict future volatility"""
        return self.model.predict(features.values)
    
    def save(self, filepath: str) -> None:
        """Save the model"""
        self.model.save_model(filepath)
    
    def load(self, filepath: str) -> None:
        """Load the model"""
        self.model.load_model(filepath)


class RiskAssessmentModel:
    """Specialized model for risk assessment"""
    
    def __init__(self, model_type: str = "random_forest", **kwargs):
        config = ModelConfig(
            model_type=model_type,
            task_type="classification",
            target_variable="risk_level",
            **kwargs
        )
        
        self.model = self._create_model(config)
        self.label_encoder = LabelEncoder()
        
    def _create_model(self, config: ModelConfig) -> BaseModel:
        """Create the appropriate model based on config"""
        if config.model_type == "lstm":
            return LSTMModel(config)
        elif config.model_type == "transformer":
            return TransformerModel(config)
        elif config.model_type == "xgboost":
            return XGBoostModel(config)
        elif config.model_type == "random_forest":
            return RandomForestModel(config)
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
    
    def create_risk_labels(self, returns: pd.Series, volatility: pd.Series) -> pd.Series:
        """Create risk level labels based on returns and volatility"""
        # Simple risk categorization
        risk_labels = pd.Series(index=returns.index, dtype=str)
        
        # High volatility = High risk
        high_vol_threshold = volatility.quantile(0.75)
        low_vol_threshold = volatility.quantile(0.25)
        
        risk_labels[volatility > high_vol_threshold] = 'HIGH'
        risk_labels[volatility < low_vol_threshold] = 'LOW'
        risk_labels[(volatility >= low_vol_threshold) & (volatility <= high_vol_threshold)] = 'MEDIUM'
        
        return risk_labels
    
    def train(self, features: pd.DataFrame, returns: pd.Series, volatility: pd.Series) -> Dict:
        """Train the risk assessment model"""
        # Create risk labels
        risk_labels = self.create_risk_labels(returns, volatility)
        
        # Encode labels
        encoded_labels = self.label_encoder.fit_transform(risk_labels)
        
        return self.model.train(features.values, encoded_labels)
    
    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict risk levels"""
        predictions = self.model.predict(features.values)
        
        # Decode predictions
        if hasattr(predictions, 'argmax'):  # For neural networks
            predictions = predictions.argmax(axis=1)
            
        decoded_predictions = self.label_encoder.inverse_transform(predictions.astype(int))
        
        return pd.Series(decoded_predictions, index=features.index)
    
    def save(self, filepath: str) -> None:
        """Save the model"""
        model_data = {
            'model': self.model,
            'label_encoder': self.label_encoder
        }
        joblib.dump(model_data, filepath)
    
    def load(self, filepath: str) -> None:
        """Load the model"""
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.label_encoder = model_data['label_encoder']


class MarketRegimeModel:
    """Specialized model for market regime detection"""
    
    def __init__(self, model_type: str = "random_forest", **kwargs):
        config = ModelConfig(
            model_type=model_type,
            task_type="classification",
            target_variable="market_regime",
            **kwargs
        )
        
        self.model = self._create_model(config)
        self.label_encoder = LabelEncoder()
        
    def _create_model(self, config: ModelConfig) -> BaseModel:
        """Create the appropriate model based on config"""
        if config.model_type == "lstm":
            return LSTMModel(config)
        elif config.model_type == "transformer":
            return TransformerModel(config)
        elif config.model_type == "xgboost":
            return XGBoostModel(config)
        elif config.model_type == "random_forest":
            return RandomForestModel(config)
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
    
    def detect_regimes(self, returns: pd.Series, volatility: pd.Series, window: int = 60) -> pd.Series:
        """Detect market regimes based on returns and volatility patterns"""
        regimes = pd.Series(index=returns.index, dtype=str)
        
        # Rolling statistics
        rolling_mean = returns.rolling(window=window).mean()
        rolling_vol = volatility.rolling(window=window).mean()
        
        # Define regime thresholds
        mean_threshold = 0.001  # Daily return threshold
        vol_threshold = volatility.quantile(0.6)
        
        # Categorize regimes
        bull_mask = (rolling_mean > mean_threshold) & (rolling_vol < vol_threshold)
        bear_mask = (rolling_mean < -mean_threshold) & (rolling_vol < vol_threshold)
        volatile_mask = rolling_vol >= vol_threshold
        
        regimes[bull_mask] = 'BULL'
        regimes[bear_mask] = 'BEAR'
        regimes[volatile_mask] = 'VOLATILE'
        regimes[~(bull_mask | bear_mask | volatile_mask)] = 'SIDEWAYS'
        
        return regimes
    
    def train(self, features: pd.DataFrame, returns: pd.Series, volatility: pd.Series) -> Dict:
        """Train the market regime model"""
        # Detect regimes
        regimes = self.detect_regimes(returns, volatility)
        
        # Align features and regimes
        aligned_features, aligned_regimes = features.align(regimes, join='inner')
        
        # Encode regimes
        encoded_regimes = self.label_encoder.fit_transform(aligned_regimes)
        
        return self.model.train(aligned_features.values, encoded_regimes)
    
    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict market regimes"""
        predictions = self.model.predict(features.values)
        
        # Decode predictions
        if hasattr(predictions, 'argmax'):  # For neural networks
            predictions = predictions.argmax(axis=1)
            
        decoded_predictions = self.label_encoder.inverse_transform(predictions.astype(int))
        
        return pd.Series(decoded_predictions, index=features.index)
    
    def save(self, filepath: str) -> None:
        """Save the model"""
        model_data = {
            'model': self.model,
            'label_encoder': self.label_encoder
        }
        joblib.dump(model_data, filepath)
    
    def load(self, filepath: str) -> None:
        """Load the model"""
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.label_encoder = model_data['label_encoder']


def create_model(model_type: str, task: str, **kwargs) -> Union[PricePredictionModel, TradingSignalClassifier, VolatilityModel, RiskAssessmentModel, MarketRegimeModel]:
    """Factory function to create specialized models"""
    
    if task == "price_prediction":
        return PricePredictionModel(model_type=model_type, **kwargs)
    elif task == "signal_classification":
        return TradingSignalClassifier(model_type=model_type, **kwargs)
    elif task == "volatility_prediction":
        return VolatilityModel(model_type=model_type, **kwargs)
    elif task == "risk_assessment":
        return RiskAssessmentModel(model_type=model_type, **kwargs)
    elif task == "regime_detection":
        return MarketRegimeModel(model_type=model_type, **kwargs)
    else:
        raise ValueError(f"Unsupported task: {task}")