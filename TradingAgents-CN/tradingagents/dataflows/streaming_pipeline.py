"""
Production Real-time Streaming Data Pipeline for TradingAgents-CN

This module implements a comprehensive real-time streaming data pipeline that handles:
- Market data streaming from multiple sources
- News feed processing with sentiment analysis
- Real-time feature engineering for ML models
- Event-driven architecture for multi-agent system
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import websocket
from urllib.parse import urlencode
import aioredis
import aiohttp
import numpy as np
import pandas as pd


class StreamingDataType(Enum):
    MARKET_TICK = "market_tick"
    MARKET_OHLC = "market_ohlc"
    NEWS_ARTICLE = "news_article"
    SOCIAL_SENTIMENT = "social_sentiment"
    ORDER_BOOK = "order_book"
    TRADE_EXECUTION = "trade_execution"
    ECONOMIC_INDICATOR = "economic_indicator"


@dataclass
class StreamMessage:
    """Standard format for streaming messages"""
    message_id: str
    timestamp: datetime
    data_type: StreamingDataType
    symbol: str
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['data_type'] = self.data_type.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamMessage':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['data_type'] = StreamingDataType(data['data_type'])
        return cls(**data)


class StreamingDataManager:
    """Core streaming data management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("streaming_pipeline")
        
        # Initialize Redis connection pool
        self.redis_pool = None
        self.redis_url = config.get('redis_url', 'redis://localhost:6379')
        
        # WebSocket connections
        self.websocket_connections = {}
        self.active_streams = {}
        
        # Message handlers
        self.message_handlers = {}
        self.processing_stats = {
            'messages_processed': 0,
            'messages_failed': 0,
            'last_message_time': None,
            'processing_rate': 0.0
        }
        
        # Real-time feature store
        self.feature_cache = {}
        
        # Initialize components
        asyncio.create_task(self._initialize_redis())
    
    async def _initialize_redis(self):
        """Initialize Redis connection pool"""
        try:
            self.redis_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True
            )
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            await redis_client.ping()
            self.logger.info("Redis connection pool initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    def register_message_handler(self, data_type: StreamingDataType, handler: Callable):
        """Register a message handler for specific data type"""
        if data_type not in self.message_handlers:
            self.message_handlers[data_type] = []
        self.message_handlers[data_type].append(handler)
        self.logger.info(f"Registered handler for {data_type.value}")
    
    async def start_market_data_stream(self, symbols: List[str], sources: List[str] = None):
        """Start real-time market data streaming"""
        if sources is None:
            sources = ['finnhub', 'tushare_realtime', 'akshare_realtime']
        
        for source in sources:
            if source == 'finnhub':
                await self._start_finnhub_stream(symbols)
            elif source == 'tushare_realtime':
                await self._start_tushare_stream(symbols)
            elif source == 'akshare_realtime':
                await self._start_akshare_stream(symbols)
    
    async def _start_finnhub_stream(self, symbols: List[str]):
        """Start FinnHub WebSocket stream"""
        try:
            api_key = self.config.get('finnhub_api_key')
            if not api_key:
                self.logger.warning("FinnHub API key not configured")
                return
            
            ws_url = f"wss://ws.finnhub.io?token={api_key}"
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get('type') == 'trade':
                        for trade in data.get('data', []):
                            asyncio.create_task(self._process_finnhub_trade(trade))
                except Exception as e:
                    self.logger.error(f"FinnHub message processing error: {e}")
            
            def on_error(ws, error):
                self.logger.error(f"FinnHub WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                self.logger.warning(f"FinnHub WebSocket closed: {close_status_code}")
                # Implement reconnection logic
                threading.Timer(5.0, lambda: self._start_finnhub_stream(symbols)).start()
            
            def on_open(ws):
                self.logger.info("FinnHub WebSocket connection opened")
                # Subscribe to symbols
                for symbol in symbols:
                    subscribe_message = {"type": "subscribe", "symbol": symbol}
                    ws.send(json.dumps(subscribe_message))
            
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Run WebSocket in separate thread
            def run_websocket():
                ws.run_forever(reconnect=5)
            
            thread = threading.Thread(target=run_websocket, daemon=True)
            thread.start()
            
            self.websocket_connections['finnhub'] = {
                'ws': ws,
                'thread': thread,
                'symbols': symbols,
                'status': 'connected'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start FinnHub stream: {e}")
    
    async def _process_finnhub_trade(self, trade_data: Dict[str, Any]):
        """Process FinnHub trade data"""
        try:
            message = StreamMessage(
                message_id=f"finnhub_trade_{int(time.time() * 1000)}",
                timestamp=datetime.fromtimestamp(trade_data.get('t', 0) / 1000),
                data_type=StreamingDataType.MARKET_TICK,
                symbol=trade_data.get('s', ''),
                source='finnhub',
                data={
                    'price': trade_data.get('p'),
                    'volume': trade_data.get('v'),
                    'conditions': trade_data.get('c', [])
                },
                metadata={'raw_data': trade_data}
            )
            
            await self._route_message(message)
            
        except Exception as e:
            self.logger.error(f"Failed to process FinnHub trade: {e}")
    
    async def start_news_stream(self, sources: List[str] = None, keywords: List[str] = None):
        """Start real-time news streaming"""
        if sources is None:
            sources = ['finnhub_news', 'reddit', 'google_news']
        
        if keywords is None:
            keywords = ['stock', 'market', 'trading', '股票', '股市', '交易']
        
        for source in sources:
            if source == 'finnhub_news':
                await self._start_finnhub_news_stream()
            elif source == 'reddit':
                await self._start_reddit_stream(keywords)
            elif source == 'google_news':
                await self._start_google_news_stream(keywords)
    
    async def _start_finnhub_news_stream(self):
        """Start FinnHub news stream"""
        try:
            async def fetch_news():
                while True:
                    try:
                        api_key = self.config.get('finnhub_api_key')
                        if not api_key:
                            await asyncio.sleep(60)
                            continue
                        
                        async with aiohttp.ClientSession() as session:
                            url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
                            async with session.get(url) as response:
                                if response.status == 200:
                                    news_data = await response.json()
                                    for article in news_data:
                                        await self._process_news_article(article, 'finnhub_news')
                        
                        await asyncio.sleep(300)  # 5 minutes interval
                        
                    except Exception as e:
                        self.logger.error(f"FinnHub news fetch error: {e}")
                        await asyncio.sleep(60)
            
            asyncio.create_task(fetch_news())
            self.active_streams['finnhub_news'] = {'status': 'active', 'type': 'news'}
            
        except Exception as e:
            self.logger.error(f"Failed to start FinnHub news stream: {e}")
    
    async def _process_news_article(self, article_data: Dict[str, Any], source: str):
        """Process news article data"""
        try:
            # Extract relevant symbols from article
            symbols = self._extract_symbols_from_text(
                article_data.get('headline', '') + ' ' + article_data.get('summary', '')
            )
            
            for symbol in symbols:
                message = StreamMessage(
                    message_id=f"{source}_news_{article_data.get('id', int(time.time()))}",
                    timestamp=datetime.fromtimestamp(article_data.get('datetime', time.time())),
                    data_type=StreamingDataType.NEWS_ARTICLE,
                    symbol=symbol,
                    source=source,
                    data={
                        'headline': article_data.get('headline'),
                        'summary': article_data.get('summary'),
                        'url': article_data.get('url'),
                        'category': article_data.get('category'),
                        'sentiment_score': None  # Will be calculated by handlers
                    },
                    metadata={'raw_data': article_data, 'extracted_symbols': symbols}
                )
                
                await self._route_message(message)
                
        except Exception as e:
            self.logger.error(f"Failed to process news article: {e}")
    
    def _extract_symbols_from_text(self, text: str) -> List[str]:
        """Extract stock symbols from text using pattern matching"""
        import re
        
        symbols = set()
        
        # US stock patterns
        us_patterns = [
            r'\$([A-Z]{1,5})',  # $AAPL format
            r'\b([A-Z]{2,5})\s+(?:stock|shares?|equity)',  # AAPL stock
            r'(?:NYSE|NASDAQ):\s*([A-Z]{1,5})',  # Exchange:SYMBOL
        ]
        
        # Chinese stock patterns
        cn_patterns = [
            r'\b(\d{6}\.S[HZ])\b',  # 000001.SZ format
            r'\b(\d{6})\b(?=\s*(?:股票|股份|上市))',  # 6-digit codes followed by stock terms
        ]
        
        all_patterns = us_patterns + cn_patterns
        
        for pattern in all_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            symbols.update(matches)
        
        # Filter and validate symbols
        validated_symbols = []
        for symbol in symbols:
            if self._validate_symbol(symbol):
                validated_symbols.append(symbol)
        
        return validated_symbols[:5]  # Limit to 5 symbols per article
    
    def _validate_symbol(self, symbol: str) -> bool:
        """Validate if a symbol is legitimate"""
        # Basic validation rules
        if len(symbol) < 1 or len(symbol) > 10:
            return False
        
        # Check against known invalid patterns
        invalid_patterns = ['HTTP', 'HTTPS', 'WWW', 'COM', 'ORG']
        if symbol.upper() in invalid_patterns:
            return False
        
        return True
    
    async def _route_message(self, message: StreamMessage):
        """Route message to appropriate handlers"""
        try:
            # Update processing statistics
            self.processing_stats['messages_processed'] += 1
            self.processing_stats['last_message_time'] = datetime.now()
            
            # Store in Redis streams
            await self._store_in_redis_stream(message)
            
            # Update real-time cache
            await self._update_real_time_cache(message)
            
            # Call registered handlers
            handlers = self.message_handlers.get(message.data_type, [])
            for handler in handlers:
                try:
                    await handler(message)
                except Exception as e:
                    self.logger.error(f"Handler error for {message.data_type}: {e}")
            
            # Update processing rate
            self._update_processing_rate()
            
        except Exception as e:
            self.logger.error(f"Message routing failed: {e}")
            self.processing_stats['messages_failed'] += 1
    
    async def _store_in_redis_stream(self, message: StreamMessage):
        """Store message in Redis stream for persistence and replay"""
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            
            # Create stream key
            stream_key = f"stream:{message.data_type.value}:{message.symbol}"
            
            # Convert message to dictionary
            message_dict = message.to_dict()
            
            # Store in Redis stream with automatic trimming
            await redis_client.xadd(
                stream_key,
                message_dict,
                maxlen=10000  # Keep last 10k messages per stream
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store message in Redis stream: {e}")
    
    async def _update_real_time_cache(self, message: StreamMessage):
        """Update real-time cache with latest data"""
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            
            if message.data_type == StreamingDataType.MARKET_TICK:
                # Update latest price cache
                cache_key = f"latest_price:{message.symbol}"
                price_data = {
                    'price': message.data.get('price'),
                    'volume': message.data.get('volume'),
                    'timestamp': message.timestamp.isoformat(),
                    'source': message.source
                }
                
                await redis_client.hset(cache_key, mapping=price_data)
                await redis_client.expire(cache_key, 300)  # 5 minutes TTL
                
                # Update price history for technical indicators
                await self._update_technical_indicators(message)
            
            elif message.data_type == StreamingDataType.NEWS_ARTICLE:
                # Update news cache
                news_key = f"latest_news:{message.symbol}"
                news_data = {
                    'headline': message.data.get('headline', ''),
                    'summary': message.data.get('summary', ''),
                    'timestamp': message.timestamp.isoformat(),
                    'source': message.source,
                    'sentiment': message.data.get('sentiment_score', 0.0)
                }
                
                await redis_client.lpush(news_key, json.dumps(news_data))
                await redis_client.ltrim(news_key, 0, 99)  # Keep latest 100 news items
                await redis_client.expire(news_key, 86400)  # 24 hours TTL
            
        except Exception as e:
            self.logger.error(f"Failed to update real-time cache: {e}")
    
    async def _update_technical_indicators(self, message: StreamMessage):
        """Update real-time technical indicators"""
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            
            symbol = message.symbol
            price = float(message.data.get('price', 0))
            timestamp = message.timestamp
            
            # Store price in time series
            price_series_key = f"price_series:{symbol}"
            price_point = {
                'timestamp': timestamp.isoformat(),
                'price': price,
                'volume': message.data.get('volume', 0)
            }
            
            await redis_client.zadd(
                price_series_key,
                {json.dumps(price_point): timestamp.timestamp()}
            )
            
            # Trim old data (keep last 1000 points)
            await redis_client.zremrangebyrank(price_series_key, 0, -1001)
            await redis_client.expire(price_series_key, 3600)  # 1 hour TTL
            
            # Calculate real-time indicators
            indicators = await self._calculate_real_time_indicators(symbol, price)
            
            # Store indicators
            indicators_key = f"indicators:{symbol}"
            await redis_client.hset(indicators_key, mapping=indicators)
            await redis_client.expire(indicators_key, 300)  # 5 minutes TTL
            
        except Exception as e:
            self.logger.error(f"Failed to update technical indicators: {e}")
    
    async def _calculate_real_time_indicators(self, symbol: str, current_price: float) -> Dict[str, float]:
        """Calculate real-time technical indicators"""
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            
            # Get recent price data
            price_series_key = f"price_series:{symbol}"
            recent_data = await redis_client.zrevrange(price_series_key, 0, 49, withscores=True)
            
            if len(recent_data) < 2:
                return {'sma_5': current_price, 'sma_20': current_price, 'rsi': 50.0}
            
            # Extract prices
            prices = []
            for data_json, timestamp in recent_data:
                try:
                    data = json.loads(data_json)
                    prices.append(float(data['price']))
                except:
                    continue
            
            prices = np.array(prices[::-1])  # Reverse to get chronological order
            
            indicators = {}
            
            # Simple Moving Averages
            if len(prices) >= 5:
                indicators['sma_5'] = float(np.mean(prices[-5:]))
            else:
                indicators['sma_5'] = float(np.mean(prices))
            
            if len(prices) >= 20:
                indicators['sma_20'] = float(np.mean(prices[-20:]))
            else:
                indicators['sma_20'] = float(np.mean(prices))
            
            # RSI calculation
            if len(prices) >= 14:
                indicators['rsi'] = self._calculate_rsi(prices, 14)
            else:
                indicators['rsi'] = 50.0
            
            # Price change percentage
            if len(prices) >= 2:
                indicators['change_pct'] = ((prices[-1] - prices[-2]) / prices[-2]) * 100
            else:
                indicators['change_pct'] = 0.0
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Failed to calculate indicators: {e}")
            return {'sma_5': current_price, 'sma_20': current_price, 'rsi': 50.0}
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi)
            
        except Exception as e:
            self.logger.error(f"RSI calculation error: {e}")
            return 50.0
    
    def _update_processing_rate(self):
        """Update processing rate statistics"""
        try:
            current_time = time.time()
            
            if not hasattr(self, '_rate_window_start'):
                self._rate_window_start = current_time
                self._rate_window_count = 0
            
            self._rate_window_count += 1
            
            # Update rate every 60 seconds
            if current_time - self._rate_window_start >= 60:
                self.processing_stats['processing_rate'] = self._rate_window_count / 60
                self._rate_window_start = current_time
                self._rate_window_count = 0
                
        except Exception as e:
            self.logger.error(f"Failed to update processing rate: {e}")
    
    async def get_stream_status(self) -> Dict[str, Any]:
        """Get current streaming status"""
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            
            # Get Redis info
            redis_info = await redis_client.info()
            
            status = {
                'active_connections': len(self.websocket_connections),
                'active_streams': len(self.active_streams),
                'processing_stats': self.processing_stats,
                'redis_status': {
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'used_memory_mb': redis_info.get('used_memory', 0) / (1024 * 1024),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0)
                },
                'websocket_status': {
                    name: conn.get('status', 'unknown') 
                    for name, conn in self.websocket_connections.items()
                }
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get stream status: {e}")
            return {'error': str(e)}
    
    async def stop_all_streams(self):
        """Stop all active streams"""
        try:
            # Close WebSocket connections
            for name, conn in self.websocket_connections.items():
                try:
                    if 'ws' in conn:
                        conn['ws'].close()
                    self.logger.info(f"Stopped {name} stream")
                except Exception as e:
                    self.logger.error(f"Error stopping {name} stream: {e}")
            
            self.websocket_connections.clear()
            self.active_streams.clear()
            
            # Close Redis connection pool
            if self.redis_pool:
                await self.redis_pool.disconnect()
            
            self.logger.info("All streams stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping streams: {e}")


# Event-driven message handlers
class MessageHandlers:
    """Collection of message handlers for different data types"""
    
    @staticmethod
    async def handle_market_tick(message: StreamMessage):
        """Handle market tick data"""
        try:
            # Update agent memory with latest price
            from tradingagents.agents.utils.memory import AgentMemoryManager
            
            memory_manager = AgentMemoryManager()
            await memory_manager.store_real_time_data(
                symbol=message.symbol,
                data_type='price_tick',
                data=message.data,
                timestamp=message.timestamp
            )
            
            # Trigger price alert checks
            await MessageHandlers._check_price_alerts(message)
            
        except Exception as e:
            logging.getLogger("message_handlers").error(f"Market tick handler error: {e}")
    
    @staticmethod
    async def handle_news_article(message: StreamMessage):
        """Handle news article data"""
        try:
            # Perform sentiment analysis
            sentiment_score = await MessageHandlers._analyze_sentiment(message.data.get('headline', ''))
            message.data['sentiment_score'] = sentiment_score
            
            # Store in news database
            from tradingagents.dataflows.mongodb_integration import EnhancedMongoDBManager
            
            mongo_manager = EnhancedMongoDBManager("mongodb://localhost:27017")
            await mongo_manager.store_news_articles([{
                'title': message.data.get('headline'),
                'content': message.data.get('summary'),
                'source': message.source,
                'published_at': message.timestamp,
                'symbols': [message.symbol],
                'sentiment_score': sentiment_score,
                'url': message.data.get('url')
            }])
            
        except Exception as e:
            logging.getLogger("message_handlers").error(f"News handler error: {e}")
    
    @staticmethod
    async def _analyze_sentiment(text: str) -> float:
        """Analyze sentiment of text (-1.0 to 1.0)"""
        try:
            # Simple keyword-based sentiment analysis
            # In production, use a proper NLP model
            positive_words = ['good', 'great', 'excellent', 'positive', 'up', 'gain', 'profit', 'success']
            negative_words = ['bad', 'terrible', 'negative', 'down', 'loss', 'decline', 'fall', 'crisis']
            
            text_lower = text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count + negative_count == 0:
                return 0.0
            
            return (positive_count - negative_count) / (positive_count + negative_count)
            
        except Exception as e:
            logging.getLogger("message_handlers").error(f"Sentiment analysis error: {e}")
            return 0.0
    
    @staticmethod
    async def _check_price_alerts(message: StreamMessage):
        """Check for price alerts and trigger notifications"""
        try:
            # Implementation for price alert checking
            # This would check user-defined alerts and send notifications
            pass
            
        except Exception as e:
            logging.getLogger("message_handlers").error(f"Price alert check error: {e}")


# Factory function for creating streaming pipeline
def create_streaming_pipeline(config: Dict[str, Any]) -> StreamingDataManager:
    """Create and configure streaming pipeline"""
    pipeline = StreamingDataManager(config)
    
    # Register default handlers
    pipeline.register_message_handler(StreamingDataType.MARKET_TICK, MessageHandlers.handle_market_tick)
    pipeline.register_message_handler(StreamingDataType.NEWS_ARTICLE, MessageHandlers.handle_news_article)
    
    return pipeline


# Example usage and testing
if __name__ == "__main__":
    async def main():
        config = {
            'redis_url': 'redis://localhost:6379',
            'finnhub_api_key': 'your_api_key_here',
            'symbols': ['AAPL', 'GOOGL', 'MSFT', '000001.SZ'],
        }
        
        pipeline = create_streaming_pipeline(config)
        
        # Start streams
        await pipeline.start_market_data_stream(config['symbols'])
        await pipeline.start_news_stream()
        
        # Run for a while
        try:
            while True:
                status = await pipeline.get_stream_status()
                print(f"Processing rate: {status['processing_stats']['processing_rate']:.2f} msg/s")
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            print("Stopping streams...")
            await pipeline.stop_all_streams()
    
    # Run the example
    asyncio.run(main())