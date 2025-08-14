"""
Enhanced MongoDB Integration for TradingAgents-CN Production Pipeline

This module provides optimized MongoDB integration with:
- Advanced indexing strategies for financial time-series data
- Sharding and replication setup for scalability
- Optimized document schemas for different data types
- Efficient aggregation pipelines for analytics
- Data lifecycle management and archival
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT, GEO2D
from pymongo.errors import (
    BulkWriteError, DuplicateKeyError, ConnectionFailure, 
    ServerSelectionTimeoutError, OperationFailure
)
from pymongo.operations import IndexModel, InsertOne, UpdateOne, ReplaceOne
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId
import gridfs
import pandas as pd
import numpy as np
from pathlib import Path


class DataCategory(Enum):
    """Data categories for different storage strategies"""
    MARKET_DATA = "market_data"
    NEWS_DATA = "news_data"  
    FINANCIAL_STATEMENTS = "financial_statements"
    ANALYSIS_RESULTS = "analysis_results"
    USER_DATA = "user_data"
    SYSTEM_LOGS = "system_logs"
    ML_FEATURES = "ml_features"
    CONFIGURATIONS = "configurations"


@dataclass
class MongoDBConfig:
    """MongoDB configuration settings"""
    connection_string: str
    database_name: str = "tradingagents"
    max_pool_size: int = 100
    min_pool_size: int = 10
    max_idle_time_ms: int = 30000
    server_selection_timeout_ms: int = 30000
    socket_timeout_ms: int = 20000
    connect_timeout_ms: int = 20000
    heartbeat_frequency_ms: int = 10000
    retry_writes: bool = True
    read_preference: str = "primaryPreferred"
    write_concern_w: Union[int, str] = "majority"
    write_concern_timeout: int = 10000


class CollectionManager:
    """Manages MongoDB collections with optimized schemas and indexes"""
    
    def __init__(self, database, config: MongoDBConfig):
        self.db = database
        self.config = config
        self.logger = logging.getLogger("mongodb_collection_manager")
        
        # Collection configurations
        self.collection_configs = {
            DataCategory.MARKET_DATA: {
                'name': 'market_data',
                'indexes': [
                    # Compound indexes for common queries
                    IndexModel([
                        ("symbol", ASCENDING),
                        ("timestamp", DESCENDING),
                        ("data_source", ASCENDING)
                    ], name="symbol_timestamp_source"),
                    
                    IndexModel([
                        ("timestamp", DESCENDING),
                        ("symbol", ASCENDING)
                    ], name="timestamp_symbol"),
                    
                    IndexModel([
                        ("symbol", ASCENDING),
                        ("data_type", ASCENDING),
                        ("timestamp", DESCENDING)
                    ], name="symbol_datatype_timestamp"),
                    
                    # Time-series optimization
                    IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
                    IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
                    
                    # Market-specific indexes
                    IndexModel([("market", ASCENDING), ("symbol", ASCENDING)], name="market_symbol"),
                    
                    # Partial indexes for better performance
                    IndexModel([("volume", DESCENDING)], 
                              partialFilterExpression={"volume": {"$gt": 0}},
                              name="volume_nonzero"),
                ],
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['symbol', 'timestamp', 'data_source'],
                        'properties': {
                            'symbol': {'bsonType': 'string', 'minLength': 1},
                            'timestamp': {'bsonType': 'date'},
                            'data_source': {'bsonType': 'string'},
                            'data_type': {'bsonType': 'string'},
                            'market': {'bsonType': 'string'},
                            'ohlcv': {
                                'bsonType': 'object',
                                'properties': {
                                    'open': {'bsonType': 'number'},
                                    'high': {'bsonType': 'number'},
                                    'low': {'bsonType': 'number'},
                                    'close': {'bsonType': 'number'},
                                    'volume': {'bsonType': 'number', 'minimum': 0}
                                }
                            }
                        }
                    }
                },
                'time_series': {
                    'timeField': 'timestamp',
                    'metaField': 'symbol',
                    'granularity': 'minutes'
                }
            },
            
            DataCategory.NEWS_DATA: {
                'name': 'news_articles',
                'indexes': [
                    IndexModel([
                        ("published_at", DESCENDING),
                        ("symbols", ASCENDING)
                    ], name="published_symbols"),
                    
                    IndexModel([
                        ("source", ASCENDING),
                        ("published_at", DESCENDING)
                    ], name="source_published"),
                    
                    # Full-text search index
                    IndexModel([("title", TEXT), ("content", TEXT)], name="text_search"),
                    
                    # Unique constraint on content hash
                    IndexModel([("content_hash", ASCENDING)], unique=True, name="content_hash_unique"),
                    
                    # Geospatial index if location data is available
                    IndexModel([("location", GEO2D)], name="location_geo", sparse=True),
                    
                    # Multi-key index for symbols array
                    IndexModel([("symbols", ASCENDING)], name="symbols_array"),
                    
                    # Sentiment analysis index
                    IndexModel([
                        ("sentiment.score", DESCENDING),
                        ("published_at", DESCENDING)
                    ], name="sentiment_published", sparse=True)
                ],
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['title', 'content_hash', 'source', 'published_at'],
                        'properties': {
                            'title': {'bsonType': 'string', 'minLength': 1},
                            'content': {'bsonType': 'string'},
                            'content_hash': {'bsonType': 'string'},
                            'source': {'bsonType': 'string'},
                            'published_at': {'bsonType': 'date'},
                            'symbols': {
                                'bsonType': 'array',
                                'items': {'bsonType': 'string'}
                            },
                            'sentiment': {
                                'bsonType': 'object',
                                'properties': {
                                    'score': {'bsonType': 'number', 'minimum': -1, 'maximum': 1},
                                    'confidence': {'bsonType': 'number', 'minimum': 0, 'maximum': 1}
                                }
                            }
                        }
                    }
                }
            },
            
            DataCategory.ANALYSIS_RESULTS: {
                'name': 'analysis_results',
                'indexes': [
                    IndexModel([
                        ("session_id", ASCENDING),
                        ("created_at", DESCENDING)
                    ], name="session_created"),
                    
                    IndexModel([
                        ("symbol", ASCENDING),
                        ("analysis_type", ASCENDING),
                        ("created_at", DESCENDING)
                    ], name="symbol_analysis_created"),
                    
                    IndexModel([
                        ("agent_name", ASCENDING),
                        ("created_at", DESCENDING)
                    ], name="agent_created"),
                    
                    # Performance tracking indexes
                    IndexModel([("execution_time_ms", DESCENDING)], name="execution_time"),
                    IndexModel([("confidence_score", DESCENDING)], name="confidence", sparse=True),
                    
                    # Cost tracking
                    IndexModel([("cost", DESCENDING)], name="cost_desc", sparse=True)
                ],
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['session_id', 'symbol', 'analysis_type', 'agent_name', 'result'],
                        'properties': {
                            'session_id': {'bsonType': 'string'},
                            'symbol': {'bsonType': 'string'},
                            'analysis_type': {'bsonType': 'string'},
                            'agent_name': {'bsonType': 'string'},
                            'result': {'bsonType': 'object'},
                            'confidence_score': {'bsonType': 'number', 'minimum': 0, 'maximum': 1},
                            'execution_time_ms': {'bsonType': 'number', 'minimum': 0}
                        }
                    }
                }
            },
            
            DataCategory.FINANCIAL_STATEMENTS: {
                'name': 'financial_statements',
                'indexes': [
                    IndexModel([
                        ("symbol", ASCENDING),
                        ("statement_type", ASCENDING),
                        ("period", DESCENDING)
                    ], name="symbol_type_period"),
                    
                    IndexModel([
                        ("period", DESCENDING),
                        ("statement_type", ASCENDING)
                    ], name="period_type"),
                    
                    IndexModel([("fiscal_year", DESCENDING)], name="fiscal_year"),
                    IndexModel([("quarter", ASCENDING)], name="quarter", sparse=True)
                ],
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['symbol', 'statement_type', 'period'],
                        'properties': {
                            'symbol': {'bsonType': 'string'},
                            'statement_type': {'enum': ['income', 'balance', 'cashflow']},
                            'period': {'bsonType': 'string'},
                            'fiscal_year': {'bsonType': 'number'},
                            'quarter': {'bsonType': 'number', 'minimum': 1, 'maximum': 4}
                        }
                    }
                }
            },
            
            DataCategory.ML_FEATURES: {
                'name': 'ml_features',
                'indexes': [
                    IndexModel([
                        ("symbol", ASCENDING),
                        ("feature_set", ASCENDING),
                        ("timestamp", DESCENDING)
                    ], name="symbol_featureset_timestamp"),
                    
                    IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
                    IndexModel([("feature_set", ASCENDING)], name="feature_set"),
                    
                    # Model-specific indexes
                    IndexModel([("model_version", ASCENDING)], name="model_version", sparse=True)
                ],
                'validator': {
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['symbol', 'feature_set', 'timestamp', 'features'],
                        'properties': {
                            'symbol': {'bsonType': 'string'},
                            'feature_set': {'bsonType': 'string'},
                            'timestamp': {'bsonType': 'date'},
                            'features': {'bsonType': 'object'},
                            'model_version': {'bsonType': 'string'}
                        }
                    }
                }
            }
        }
    
    async def initialize_collections(self):
        """Initialize all collections with proper schemas and indexes"""
        try:
            for category, config in self.collection_configs.items():
                collection_name = config['name']
                
                # Create collection with options
                collection_options = {}
                
                # Add validator if specified
                if 'validator' in config:
                    collection_options['validator'] = config['validator']
                
                # Add time-series configuration if specified
                if 'time_series' in config:
                    collection_options['timeseries'] = config['time_series']
                
                # Create collection
                try:
                    if collection_options:
                        await self.db.create_collection(collection_name, **collection_options)
                    else:
                        # Collection will be created on first insert if no options
                        pass
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        self.logger.warning(f"Collection {collection_name} creation warning: {e}")
                
                # Create indexes
                collection = self.db[collection_name]
                
                try:
                    if config.get('indexes'):
                        await collection.create_indexes(config['indexes'])
                        self.logger.info(f"Created {len(config['indexes'])} indexes for {collection_name}")
                except Exception as e:
                    self.logger.error(f"Index creation failed for {collection_name}: {e}")
            
            self.logger.info("All collections and indexes initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Collection initialization failed: {e}")
            raise


class EnhancedMongoDBManager:
    """Enhanced MongoDB manager with production-grade features"""
    
    def __init__(self, config: MongoDBConfig):
        self.config = config
        self.logger = logging.getLogger("enhanced_mongodb_manager")
        
        # Connection pools
        self.sync_client = None
        self.async_client = None
        self.db = None
        self.sync_db = None
        
        # GridFS for file storage
        self.gridfs = None
        
        # Collection manager
        self.collection_manager = None
        
        # Performance tracking
        self.operation_stats = {
            'inserts': 0,
            'updates': 0,
            'deletes': 0,
            'queries': 0,
            'errors': 0,
            'last_operation_time': None
        }
        
        # Initialize connections
        asyncio.create_task(self._initialize_connections())
    
    async def _initialize_connections(self):
        """Initialize MongoDB connections"""
        try:
            # Create async client
            self.async_client = AsyncIOMotorClient(
                self.config.connection_string,
                maxPoolSize=self.config.max_pool_size,
                minPoolSize=self.config.min_pool_size,
                maxIdleTimeMS=self.config.max_idle_time_ms,
                serverSelectionTimeoutMS=self.config.server_selection_timeout_ms,
                socketTimeoutMS=self.config.socket_timeout_ms,
                connectTimeoutMS=self.config.connect_timeout_ms,
                heartbeatFrequencyMS=self.config.heartbeat_frequency_ms,
                retryWrites=self.config.retry_writes,
                readPreference=self.config.read_preference,
                w=self.config.write_concern_w,
                wtimeout=self.config.write_concern_timeout
            )
            
            # Create sync client for GridFS and administrative operations
            self.sync_client = MongoClient(
                self.config.connection_string,
                maxPoolSize=self.config.max_pool_size,
                serverSelectionTimeoutMS=self.config.server_selection_timeout_ms
            )
            
            # Get databases
            self.db = self.async_client[self.config.database_name]
            self.sync_db = self.sync_client[self.config.database_name]
            
            # Initialize GridFS
            self.gridfs = gridfs.GridFS(self.sync_db)
            
            # Test connections
            await self.async_client.admin.command('ping')
            self.sync_client.admin.command('ping')
            
            # Initialize collection manager
            self.collection_manager = CollectionManager(self.db, self.config)
            await self.collection_manager.initialize_collections()
            
            self.logger.info("MongoDB connections initialized successfully")
            
        except Exception as e:
            self.logger.error(f"MongoDB initialization failed: {e}")
            raise
    
    async def store_market_data(self, data: List[Dict[str, Any]], 
                              batch_size: int = 1000) -> Dict[str, Any]:
        """Store market data with optimized batch operations"""
        try:
            collection = self.db[self.collection_manager.collection_configs[DataCategory.MARKET_DATA]['name']]
            
            results = {
                'inserted': 0,
                'updated': 0,
                'errors': []
            }
            
            # Process data in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                operations = []
                
                for record in batch:
                    try:
                        # Prepare document
                        document = self._prepare_market_data_document(record)
                        
                        # Create upsert operation
                        filter_doc = {
                            'symbol': document['symbol'],
                            'timestamp': document['timestamp'],
                            'data_source': document['data_source']
                        }
                        
                        update_doc = {
                            '$set': document,
                            '$setOnInsert': {'created_at': datetime.utcnow()}
                        }
                        
                        operations.append(
                            UpdateOne(filter_doc, update_doc, upsert=True)
                        )
                        
                    except Exception as e:
                        results['errors'].append({
                            'record': record,
                            'error': str(e)
                        })
                
                if operations:
                    try:
                        # Execute bulk operation
                        bulk_result = await collection.bulk_write(operations, ordered=False)
                        
                        results['inserted'] += bulk_result.upserted_count
                        results['updated'] += bulk_result.modified_count
                        
                    except BulkWriteError as e:
                        # Handle bulk write errors
                        for error in e.details.get('writeErrors', []):
                            results['errors'].append({
                                'error': error.get('errmsg', 'Unknown bulk write error'),
                                'code': error.get('code')
                            })
                        
                        # Still count successful operations
                        results['inserted'] += e.details.get('nUpserted', 0)
                        results['updated'] += e.details.get('nModified', 0)
            
            # Update statistics
            self.operation_stats['inserts'] += results['inserted']
            self.operation_stats['updates'] += results['updated']
            self.operation_stats['last_operation_time'] = datetime.utcnow()
            
            self.logger.info(f"Market data storage completed: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Market data storage failed: {e}")
            self.operation_stats['errors'] += 1
            raise
    
    def _prepare_market_data_document(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data document with optimized structure"""
        document = {
            'symbol': record['symbol'],
            'timestamp': record.get('timestamp') if isinstance(record.get('timestamp'), datetime) 
                        else datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')),
            'data_source': record.get('source', record.get('data_source', 'unknown')),
            'data_type': record.get('data_type', 'ohlcv'),
            'market': record.get('market', self._infer_market_from_symbol(record['symbol'])),
            'updated_at': datetime.utcnow()
        }
        
        # Optimize OHLCV data structure
        if any(field in record for field in ['open', 'high', 'low', 'close', 'volume']):
            document['ohlcv'] = {}
            
            for field in ['open', 'high', 'low', 'close']:
                if field in record and record[field] is not None:
                    document['ohlcv'][field] = float(record[field])
            
            if 'volume' in record and record['volume'] is not None:
                document['ohlcv']['volume'] = int(record['volume'])
            
            # Additional fields
            if 'amount' in record and record['amount'] is not None:
                document['ohlcv']['amount'] = float(record['amount'])
        
        # Technical indicators (if present)
        if 'indicators' in record:
            document['indicators'] = record['indicators']
        
        # Metadata
        if 'metadata' in record:
            document['metadata'] = record['metadata']
        
        # Quality score
        if 'quality_score' in record:
            document['quality_score'] = float(record['quality_score'])
        
        return document
    
    def _infer_market_from_symbol(self, symbol: str) -> str:
        """Infer market from symbol format"""
        if symbol.endswith('.SH'):
            return 'SSE'  # Shanghai Stock Exchange
        elif symbol.endswith('.SZ'):
            return 'SZSE'  # Shenzhen Stock Exchange
        elif symbol.endswith('.HK'):
            return 'HKEX'  # Hong Kong Exchange
        elif len(symbol) <= 5 and symbol.isupper():
            return 'US'  # US market (NASDAQ/NYSE)
        else:
            return 'OTHER'
    
    async def store_news_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store news articles with deduplication and full-text indexing"""
        try:
            collection = self.db[self.collection_manager.collection_configs[DataCategory.NEWS_DATA]['name']]
            
            results = {
                'inserted': 0,
                'duplicates': 0,
                'errors': []
            }
            
            operations = []
            
            for article in articles:
                try:
                    # Prepare document
                    document = self._prepare_news_document(article)
                    
                    # Create insert operation
                    operations.append(InsertOne(document))
                    
                except Exception as e:
                    results['errors'].append({
                        'article': article,
                        'error': str(e)
                    })
            
            if operations:
                try:
                    # Execute bulk insert
                    bulk_result = await collection.bulk_write(operations, ordered=False)
                    results['inserted'] = bulk_result.inserted_count
                    
                except BulkWriteError as e:
                    # Count successful inserts and duplicates
                    for error in e.details.get('writeErrors', []):
                        if error.get('code') == 11000:  # Duplicate key error
                            results['duplicates'] += 1
                        else:
                            results['errors'].append({
                                'error': error.get('errmsg', 'Unknown error'),
                                'code': error.get('code')
                            })
                    
                    results['inserted'] = e.details.get('nInserted', 0)
            
            self.operation_stats['inserts'] += results['inserted']
            self.operation_stats['last_operation_time'] = datetime.utcnow()
            
            self.logger.info(f"News articles storage completed: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"News articles storage failed: {e}")
            self.operation_stats['errors'] += 1
            raise
    
    def _prepare_news_document(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare news document with optimized structure"""
        import hashlib
        
        # Generate content hash for deduplication
        content_for_hash = (article.get('title', '') + article.get('content', '')).strip()
        content_hash = hashlib.md5(content_for_hash.encode('utf-8')).hexdigest()
        
        document = {
            'title': article['title'],
            'content': article.get('content', ''),
            'content_hash': content_hash,
            'source': article['source'],
            'author': article.get('author'),
            'published_at': article.get('published_at') if isinstance(article.get('published_at'), datetime)
                           else datetime.fromisoformat(article['published_at'].replace('Z', '+00:00')),
            'url': article.get('url'),
            'symbols': article.get('symbols', []),
            'categories': article.get('categories', []),
            'language': article.get('language', 'en'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Sentiment analysis results
        if 'sentiment' in article:
            document['sentiment'] = {
                'score': float(article['sentiment'].get('score', 0)),
                'confidence': float(article['sentiment'].get('confidence', 0)),
                'analyzer': article['sentiment'].get('analyzer', 'unknown')
            }
        
        # Entity extraction
        if 'entities' in article:
            document['entities'] = article['entities']
        
        # Location data
        if 'location' in article:
            document['location'] = article['location']
        
        return document
    
    async def store_analysis_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store analysis results from agents"""
        try:
            collection = self.db[self.collection_manager.collection_configs[DataCategory.ANALYSIS_RESULTS]['name']]
            
            storage_results = {
                'inserted': 0,
                'errors': []
            }
            
            operations = []
            
            for result in results:
                try:
                    document = self._prepare_analysis_document(result)
                    operations.append(InsertOne(document))
                    
                except Exception as e:
                    storage_results['errors'].append({
                        'result': result,
                        'error': str(e)
                    })
            
            if operations:
                bulk_result = await collection.bulk_write(operations, ordered=False)
                storage_results['inserted'] = bulk_result.inserted_count
            
            self.operation_stats['inserts'] += storage_results['inserted']
            self.operation_stats['last_operation_time'] = datetime.utcnow()
            
            return storage_results
            
        except Exception as e:
            self.logger.error(f"Analysis results storage failed: {e}")
            self.operation_stats['errors'] += 1
            raise
    
    def _prepare_analysis_document(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare analysis result document"""
        document = {
            'session_id': result['session_id'],
            'symbol': result['symbol'],
            'analysis_type': result['analysis_type'],
            'agent_name': result['agent_name'],
            'result': result['result'],
            'created_at': datetime.utcnow()
        }
        
        # Optional fields
        optional_fields = [
            'confidence_score', 'execution_time_ms', 'model_used', 
            'tokens_used', 'cost', 'supporting_data', 'metadata'
        ]
        
        for field in optional_fields:
            if field in result:
                if field in ['confidence_score', 'execution_time_ms', 'cost']:
                    document[field] = float(result[field]) if result[field] is not None else None
                elif field == 'tokens_used':
                    document[field] = int(result[field]) if result[field] is not None else None
                else:
                    document[field] = result[field]
        
        return document
    
    async def query_market_data(self, 
                              symbols: List[str] = None,
                              start_date: datetime = None,
                              end_date: datetime = None,
                              data_types: List[str] = None,
                              markets: List[str] = None,
                              limit: int = 1000,
                              sort_by: str = 'timestamp',
                              sort_order: int = -1) -> List[Dict[str, Any]]:
        """Query market data with optimized aggregation pipeline"""
        try:
            collection = self.db[self.collection_manager.collection_configs[DataCategory.MARKET_DATA]['name']]
            
            # Build aggregation pipeline
            pipeline = []
            
            # Match stage
            match_conditions = {}
            
            if symbols:
                match_conditions['symbol'] = {'$in': symbols}
            
            if start_date or end_date:
                date_condition = {}
                if start_date:
                    date_condition['$gte'] = start_date
                if end_date:
                    date_condition['$lte'] = end_date
                match_conditions['timestamp'] = date_condition
            
            if data_types:
                match_conditions['data_type'] = {'$in': data_types}
            
            if markets:
                match_conditions['market'] = {'$in': markets}
            
            if match_conditions:
                pipeline.append({'$match': match_conditions})
            
            # Sort stage
            sort_stage = {sort_by: sort_order}
            pipeline.append({'$sort': sort_stage})
            
            # Limit stage
            pipeline.append({'$limit': limit})
            
            # Project stage to optimize data transfer
            pipeline.append({
                '$project': {
                    'symbol': 1,
                    'timestamp': 1,
                    'data_source': 1,
                    'data_type': 1,
                    'market': 1,
                    'ohlcv': 1,
                    'indicators': 1,
                    'quality_score': 1
                }
            })
            
            # Execute aggregation
            cursor = collection.aggregate(pipeline, allowDiskUse=True)
            results = await cursor.to_list(length=None)
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                if '_id' in result:
                    result['_id'] = str(result['_id'])
            
            self.operation_stats['queries'] += 1
            self.operation_stats['last_operation_time'] = datetime.utcnow()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Market data query failed: {e}")
            self.operation_stats['errors'] += 1
            raise
    
    async def get_latest_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get latest prices for symbols using optimized query"""
        try:
            collection = self.db[self.collection_manager.collection_configs[DataCategory.MARKET_DATA]['name']]
            
            # Aggregation pipeline to get latest price for each symbol
            pipeline = [
                {
                    '$match': {
                        'symbol': {'$in': symbols},
                        'ohlcv.close': {'$exists': True}
                    }
                },
                {
                    '$sort': {'symbol': 1, 'timestamp': -1}
                },
                {
                    '$group': {
                        '_id': '$symbol',
                        'latest_data': {'$first': '$$ROOT'}
                    }
                },
                {
                    '$replaceRoot': {'newRoot': '$latest_data'}
                },
                {
                    '$project': {
                        'symbol': 1,
                        'timestamp': 1,
                        'ohlcv': 1,
                        'data_source': 1
                    }
                }
            ]
            
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            # Convert to dictionary format
            latest_prices = {}
            for result in results:
                symbol = result['symbol']
                ohlcv = result.get('ohlcv', {})
                
                latest_prices[symbol] = {
                    'price': ohlcv.get('close'),
                    'open': ohlcv.get('open'),
                    'high': ohlcv.get('high'),
                    'low': ohlcv.get('low'),
                    'volume': ohlcv.get('volume'),
                    'timestamp': result['timestamp'],
                    'data_source': result['data_source']
                }
            
            self.operation_stats['queries'] += 1
            return latest_prices
            
        except Exception as e:
            self.logger.error(f"Latest prices query failed: {e}")
            self.operation_stats['errors'] += 1
            raise
    
    async def get_analysis_history(self, 
                                 symbol: str, 
                                 analysis_type: str = None,
                                 agent_name: str = None,
                                 limit: int = 100,
                                 start_date: datetime = None) -> List[Dict[str, Any]]:
        """Get historical analysis results for a symbol"""
        try:
            collection = self.db[self.collection_manager.collection_configs[DataCategory.ANALYSIS_RESULTS]['name']]
            
            # Build query
            query = {'symbol': symbol}
            
            if analysis_type:
                query['analysis_type'] = analysis_type
            
            if agent_name:
                query['agent_name'] = agent_name
            
            if start_date:
                query['created_at'] = {'$gte': start_date}
            
            # Execute query with sorting
            cursor = collection.find(query).sort('created_at', -1).limit(limit)
            results = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for result in results:
                result['_id'] = str(result['_id'])
            
            self.operation_stats['queries'] += 1
            return results
            
        except Exception as e:
            self.logger.error(f"Analysis history query failed: {e}")
            self.operation_stats['errors'] += 1
            raise
    
    async def store_file(self, filename: str, data: bytes, 
                        metadata: Dict[str, Any] = None) -> str:
        """Store file in GridFS"""
        try:
            # Use sync GridFS for file operations
            file_id = self.gridfs.put(
                data,
                filename=filename,
                metadata=metadata or {},
                upload_date=datetime.utcnow()
            )
            
            self.logger.info(f"File stored in GridFS: {filename} (ID: {file_id})")
            return str(file_id)
            
        except Exception as e:
            self.logger.error(f"File storage failed: {e}")
            raise
    
    async def get_file(self, file_id: str) -> Tuple[bytes, Dict[str, Any]]:
        """Retrieve file from GridFS"""
        try:
            grid_out = self.gridfs.get(ObjectId(file_id))
            data = grid_out.read()
            metadata = grid_out.metadata or {}
            
            return data, metadata
            
        except Exception as e:
            self.logger.error(f"File retrieval failed: {e}")
            raise
    
    async def cleanup_old_data(self, retention_policies: Dict[str, timedelta]) -> Dict[str, int]:
        """Clean up old data based on retention policies"""
        cleanup_results = {}
        
        for category_name, retention_period in retention_policies.items():
            try:
                # Map category name to collection
                category_mapping = {
                    'market_data': DataCategory.MARKET_DATA,
                    'news_data': DataCategory.NEWS_DATA,
                    'analysis_results': DataCategory.ANALYSIS_RESULTS,
                    'ml_features': DataCategory.ML_FEATURES
                }
                
                if category_name not in category_mapping:
                    continue
                
                category = category_mapping[category_name]
                collection_name = self.collection_manager.collection_configs[category]['name']
                collection = self.db[collection_name]
                
                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - retention_period
                
                # Delete old documents
                result = await collection.delete_many({
                    'created_at': {'$lt': cutoff_date}
                })
                
                cleanup_results[category_name] = result.deleted_count
                
                self.logger.info(f"Cleaned up {result.deleted_count} documents from {collection_name}")
                
            except Exception as e:
                self.logger.error(f"Cleanup failed for {category_name}: {e}")
                cleanup_results[category_name] = 0
        
        self.operation_stats['deletes'] += sum(cleanup_results.values())
        return cleanup_results
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            # Database stats
            db_stats = await self.db.command('dbStats')
            
            # Collection stats
            collection_stats = {}
            for category, config in self.collection_manager.collection_configs.items():
                collection_name = config['name']
                try:
                    stats = await self.db.command('collStats', collection_name)
                    collection_stats[collection_name] = {
                        'count': stats.get('count', 0),
                        'size': stats.get('size', 0),
                        'avgObjSize': stats.get('avgObjSize', 0),
                        'totalIndexSize': stats.get('totalIndexSize', 0),
                        'indexCount': len(stats.get('indexSizes', {}))
                    }
                except Exception as e:
                    collection_stats[collection_name] = {'error': str(e)}
            
            # Server status
            server_status = await self.db.client.admin.command('serverStatus')
            
            stats = {
                'database': {
                    'name': self.config.database_name,
                    'collections': db_stats.get('collections', 0),
                    'objects': db_stats.get('objects', 0),
                    'avgObjSize': db_stats.get('avgObjSize', 0),
                    'dataSize': db_stats.get('dataSize', 0),
                    'storageSize': db_stats.get('storageSize', 0),
                    'indexes': db_stats.get('indexes', 0),
                    'indexSize': db_stats.get('indexSize', 0)
                },
                'collections': collection_stats,
                'server': {
                    'version': server_status.get('version'),
                    'uptime': server_status.get('uptime'),
                    'connections': server_status.get('connections', {}),
                    'opcounters': server_status.get('opcounters', {}),
                    'mem': server_status.get('mem', {})
                },
                'operation_stats': self.operation_stats.copy()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Database stats retrieval failed: {e}")
            return {'error': str(e)}
    
    async def create_backup(self, backup_path: str) -> Dict[str, Any]:
        """Create database backup (simplified version)"""
        try:
            from bson.json_util import dumps
            import os
            
            backup_info = {
                'timestamp': datetime.utcnow(),
                'database': self.config.database_name,
                'collections_backed_up': [],
                'total_documents': 0
            }
            
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup each collection
            for category, config in self.collection_manager.collection_configs.items():
                collection_name = config['name']
                collection = self.db[collection_name]
                
                # Get all documents
                cursor = collection.find({})
                documents = await cursor.to_list(length=None)
                
                if documents:
                    # Save to JSON file
                    backup_file = backup_dir / f"{collection_name}.json"
                    with open(backup_file, 'w') as f:
                        f.write(dumps(documents, indent=2))
                    
                    backup_info['collections_backed_up'].append(collection_name)
                    backup_info['total_documents'] += len(documents)
            
            # Save backup metadata
            metadata_file = backup_dir / 'backup_metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(backup_info, f, indent=2, default=str)
            
            self.logger.info(f"Database backup completed: {backup_info}")
            return backup_info
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            raise
    
    async def close_connections(self):
        """Close all database connections"""
        try:
            if self.async_client:
                self.async_client.close()
            
            if self.sync_client:
                self.sync_client.close()
            
            self.logger.info("MongoDB connections closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing MongoDB connections: {e}")


# Factory function
def create_mongodb_manager(connection_string: str, **kwargs) -> EnhancedMongoDBManager:
    """Create MongoDB manager with configuration"""
    config = MongoDBConfig(
        connection_string=connection_string,
        **kwargs
    )
    return EnhancedMongoDBManager(config)


# Example usage and testing
if __name__ == "__main__":
    async def test_mongodb_manager():
        # Configuration
        config = MongoDBConfig(
            connection_string="mongodb://localhost:27017",
            database_name="test_tradingagents"
        )
        
        manager = EnhancedMongoDBManager(config)
        
        # Test data
        market_data = [
            {
                'symbol': 'AAPL',
                'timestamp': datetime.utcnow(),
                'open': 150.0,
                'high': 155.0,
                'low': 148.0,
                'close': 152.0,
                'volume': 1000000,
                'source': 'test'
            }
        ]
        
        # Store market data
        result = await manager.store_market_data(market_data)
        print(f"Market data storage result: {result}")
        
        # Query data
        query_result = await manager.query_market_data(
            symbols=['AAPL'],
            limit=10
        )
        print(f"Query result: {len(query_result)} records")
        
        # Get stats
        stats = await manager.get_database_stats()
        print(f"Database stats: {json.dumps(stats, indent=2, default=str)}")
        
        # Close connections
        await manager.close_connections()
    
    # Run test
    asyncio.run(test_mongodb_manager())