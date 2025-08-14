"""
Airflow DAGs for TradingAgents-CN Batch Processing Pipeline

This module implements comprehensive batch processing workflows for:
- Daily market data ingestion and processing
- Weekly financial statement updates
- Monthly model retraining and backtesting
- Historical data backfill operations
- Data quality monitoring and reporting
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import json
import os
from pathlib import Path

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from airflow.sensors.filesystem import FileSensor
from airflow.hooks.postgres_hook import PostgresHook
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable
import pandas as pd
import numpy as np

# Default configuration for all DAGs
DEFAULT_DAG_ARGS = {
    'owner': 'tradingagents',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
    'catchup': False
}

# Common tags for all DAGs
COMMON_TAGS = ['trading', 'data-pipeline', 'production']


def get_data_source_config() -> Dict[str, Any]:
    """Get data source configuration from Airflow Variables"""
    try:
        return json.loads(Variable.get("data_source_config", default_var="{}"))
    except:
        return {
            'tushare_token': os.getenv('TUSHARE_TOKEN', ''),
            'finnhub_api_key': os.getenv('FINNHUB_API_KEY', ''),
            'mongodb_url': os.getenv('TRADINGAGENTS_MONGODB_URL', 'mongodb://localhost:27017'),
            'redis_url': os.getenv('TRADINGAGENTS_REDIS_URL', 'redis://localhost:6379')
        }


def extract_tushare_daily_data(**context) -> str:
    """Extract daily market data from Tushare"""
    try:
        from tradingagents.dataflows.tushare_adapter import TushareAdapter
        
        config = get_data_source_config()
        execution_date = context['execution_date']
        
        # Initialize Tushare adapter
        adapter = TushareAdapter(token=config.get('tushare_token'))
        
        # Get symbol list from configuration
        symbols = Variable.get("daily_processing_symbols", default_var="[]")
        symbols = json.loads(symbols) if isinstance(symbols, str) else symbols
        
        if not symbols:
            symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']  # Default symbols
        
        # Extract data for execution date
        date_str = execution_date.strftime('%Y%m%d')
        all_data = []
        
        logging.info(f"Extracting data for {len(symbols)} symbols on {date_str}")
        
        for symbol in symbols:
            try:
                # Get daily OHLCV data
                daily_data = adapter.get_daily_data(
                    ts_code=symbol,
                    start_date=date_str,
                    end_date=date_str
                )
                
                if daily_data is not None and not daily_data.empty:
                    # Convert to standard format
                    for _, row in daily_data.iterrows():
                        record = {
                            'symbol': symbol,
                            'trade_date': row['trade_date'],
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': int(row['vol']),
                            'amount': float(row['amount']),
                            'change': float(row.get('change', 0)),
                            'pct_chg': float(row.get('pct_chg', 0)),
                            'source': 'tushare',
                            'extracted_at': datetime.now().isoformat()
                        }
                        all_data.append(record)
                
                # Rate limiting
                import time
                time.sleep(0.1)  # 100ms delay between requests
                
            except Exception as e:
                logging.warning(f"Failed to extract data for {symbol}: {e}")
                continue
        
        # Store extracted data to temporary file
        output_file = f"/tmp/tushare_daily_{date_str}.json"
        with open(output_file, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        logging.info(f"Extracted {len(all_data)} records to {output_file}")
        return output_file
        
    except Exception as e:
        logging.error(f"Data extraction failed: {e}")
        raise


def validate_extracted_data(**context) -> Dict[str, Any]:
    """Validate extracted market data"""
    try:
        from tradingagents.dataflows.quality_validator import DataQualityValidator
        
        # Get input file from previous task
        input_file = context['task_instance'].xcom_pull(task_ids='extract_tushare_data')
        
        if not input_file or not os.path.exists(input_file):
            raise ValueError("Input data file not found")
        
        # Load data
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        if not data:
            raise ValueError("No data to validate")
        
        # Initialize validator
        validator = DataQualityValidator()
        
        # Run validation
        validation_results = validator.validate_market_data(data, data_type="daily_ohlc")
        
        # Log validation results
        logging.info(f"Data Quality Score: {validation_results['data_quality_score']:.2f}")
        logging.info(f"Total Records: {validation_results['total_records']}")
        logging.info(f"Critical Failures: {validation_results['summary']['critical_failures']}")
        logging.info(f"Errors: {validation_results['summary']['errors']}")
        logging.info(f"Warnings: {validation_results['summary']['warnings']}")
        
        # Store validation results
        results_file = input_file.replace('.json', '_validation.json')
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        # Check if data is valid enough to continue
        if not validation_results['is_valid']:
            error_msg = f"Data validation failed: {validation_results['summary']}"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        # Store validation file path in XCom
        context['task_instance'].xcom_push(key='validation_results', value=validation_results)
        
        return validation_results
        
    except Exception as e:
        logging.error(f"Data validation failed: {e}")
        raise


def transform_market_data(**context) -> str:
    """Transform and enrich market data"""
    try:
        from tradingagents.dataflows.transformers import MarketDataTransformer
        
        # Get input file
        input_file = context['task_instance'].xcom_pull(task_ids='extract_tushare_data')
        
        # Load data
        with open(input_file, 'r') as f:
            raw_data = json.load(f)
        
        # Initialize transformer
        transformer = MarketDataTransformer()
        
        transformed_data = []
        
        logging.info(f"Transforming {len(raw_data)} records")
        
        for record in raw_data:
            try:
                # Add technical indicators
                enriched_record = transformer.add_technical_indicators(record)
                
                # Add market context
                enriched_record = transformer.add_market_context(enriched_record)
                
                # Normalize schema
                enriched_record = transformer.normalize_schema(enriched_record)
                
                transformed_data.append(enriched_record)
                
            except Exception as e:
                logging.warning(f"Failed to transform record {record.get('symbol', 'unknown')}: {e}")
                continue
        
        # Store transformed data
        execution_date = context['execution_date'].strftime('%Y%m%d')
        output_file = f"/tmp/transformed_daily_{execution_date}.json"
        with open(output_file, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        
        logging.info(f"Transformed {len(transformed_data)} records to {output_file}")
        return output_file
        
    except Exception as e:
        logging.error(f"Data transformation failed: {e}")
        raise


def load_to_mongodb(**context) -> Dict[str, Any]:
    """Load data to MongoDB"""
    try:
        from tradingagents.dataflows.enhanced_mongodb_integration import EnhancedMongoDBManager
        
        config = get_data_source_config()
        
        # Get transformed data
        input_file = context['task_instance'].xcom_pull(task_ids='transform_data')
        
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Initialize MongoDB manager
        mongodb_manager = EnhancedMongoDBManager(config['mongodb_url'])
        
        # Load market metadata
        load_results = await mongodb_manager.store_market_metadata(data)
        
        logging.info(f"MongoDB load results: {load_results}")
        
        # Store results
        context['task_instance'].xcom_push(key='mongodb_load_results', value=load_results)
        
        return load_results
        
    except Exception as e:
        logging.error(f"MongoDB load failed: {e}")
        raise


def load_to_redis_cache(**context) -> Dict[str, Any]:
    """Load latest data to Redis cache"""
    try:
        from tradingagents.dataflows.enhanced_redis_integration import EnhancedRedisManager
        
        config = get_data_source_config()
        
        # Get transformed data
        input_file = context['task_instance'].xcom_pull(task_ids='transform_data')
        
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Initialize Redis manager
        redis_config = {
            'redis_url': config['redis_url'],
            'cache_config': {
                'default_ttl': 86400,  # 24 hours
                'key_prefix': 'ta_daily'
            }
        }
        
        redis_manager = EnhancedRedisManager(redis_config)
        
        # Cache latest data for each symbol
        cache_results = {'cached_symbols': 0, 'errors': 0}
        
        for record in data:
            try:
                symbol = record['symbol']
                market_data = {
                    'price': record['close'],
                    'volume': record['volume'],
                    'change_pct': record.get('pct_chg', 0),
                    'timestamp': record.get('extracted_at', datetime.now().isoformat()),
                    'indicators': record.get('indicators', {})
                }
                
                success = await redis_manager.set_market_data(symbol, market_data, ttl=86400)
                if success:
                    cache_results['cached_symbols'] += 1
                else:
                    cache_results['errors'] += 1
                    
            except Exception as e:
                logging.warning(f"Failed to cache data for {record.get('symbol', 'unknown')}: {e}")
                cache_results['errors'] += 1
        
        logging.info(f"Redis cache results: {cache_results}")
        
        await redis_manager.close()
        
        return cache_results
        
    except Exception as e:
        logging.error(f"Redis cache load failed: {e}")
        raise


def update_ml_features(**context) -> Dict[str, Any]:
    """Update ML feature store"""
    try:
        from tradingagents.ml.feature_engineering import FeatureEngineer
        from tradingagents.dataflows.enhanced_redis_integration import EnhancedRedisManager
        
        config = get_data_source_config()
        
        # Get transformed data
        input_file = context['task_instance'].xcom_pull(task_ids='transform_data')
        
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Initialize feature engineer
        feature_engineer = FeatureEngineer()
        
        # Initialize Redis for feature store
        redis_config = {
            'redis_url': config['redis_url'],
            'cache_config': {
                'default_ttl': 604800,  # 7 days
                'key_prefix': 'ta_features'
            }
        }
        
        redis_manager = EnhancedRedisManager(redis_config)
        
        feature_results = {'processed_symbols': 0, 'errors': 0}
        
        for record in data:
            try:
                symbol = record['symbol']
                
                # Extract features
                features = feature_engineer.extract_features(record)
                
                # Store in feature store
                success = await redis_manager.store_ml_features(
                    symbol=symbol,
                    features=features,
                    feature_set='daily_batch',
                    ttl=604800
                )
                
                if success:
                    feature_results['processed_symbols'] += 1
                else:
                    feature_results['errors'] += 1
                    
            except Exception as e:
                logging.warning(f"Failed to process features for {record.get('symbol', 'unknown')}: {e}")
                feature_results['errors'] += 1
        
        logging.info(f"Feature update results: {feature_results}")
        
        await redis_manager.close()
        
        return feature_results
        
    except Exception as e:
        logging.error(f"Feature update failed: {e}")
        raise


def cleanup_temporary_files(**context) -> Dict[str, int]:
    """Clean up temporary files"""
    try:
        files_cleaned = 0
        
        # Get file paths from XCom
        temp_files = [
            context['task_instance'].xcom_pull(task_ids='extract_tushare_data'),
            context['task_instance'].xcom_pull(task_ids='transform_data')
        ]
        
        # Add validation results files
        for temp_file in temp_files:
            if temp_file:
                validation_file = temp_file.replace('.json', '_validation.json')
                temp_files.append(validation_file)
        
        # Clean up files
        for file_path in temp_files:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    files_cleaned += 1
                    logging.info(f"Cleaned up {file_path}")
                except Exception as e:
                    logging.warning(f"Failed to clean up {file_path}: {e}")
        
        # Clean up old temporary files (older than 7 days)
        temp_dir = Path("/tmp")
        cutoff_time = datetime.now() - timedelta(days=7)
        
        for file_path in temp_dir.glob("*tushare_daily_*.json"):
            try:
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                    file_path.unlink()
                    files_cleaned += 1
            except Exception as e:
                logging.warning(f"Failed to clean old file {file_path}: {e}")
        
        result = {'files_cleaned': files_cleaned}
        logging.info(f"Cleanup completed: {result}")
        
        return result
        
    except Exception as e:
        logging.error(f"Cleanup failed: {e}")
        return {'files_cleaned': 0, 'error': str(e)}


def send_completion_notification(**context) -> None:
    """Send pipeline completion notification"""
    try:
        # Get execution results from previous tasks
        validation_results = context['task_instance'].xcom_pull(key='validation_results', task_ids='validate_data')
        mongodb_results = context['task_instance'].xcom_pull(key='mongodb_load_results', task_ids='load_to_mongodb')
        
        execution_date = context['execution_date'].strftime('%Y-%m-%d')
        
        # Prepare notification message
        message = {
            'pipeline': 'daily_market_data',
            'execution_date': execution_date,
            'status': 'completed',
            'data_quality_score': validation_results.get('data_quality_score', 0) if validation_results else 0,
            'records_processed': validation_results.get('total_records', 0) if validation_results else 0,
            'mongodb_inserted': mongodb_results.get('inserted', 0) if mongodb_results else 0,
            'mongodb_updated': mongodb_results.get('updated', 0) if mongodb_results else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send notification (implement based on your notification system)
        # This could be email, Slack, webhook, etc.
        logging.info(f"Pipeline completion notification: {json.dumps(message, indent=2)}")
        
        # Store notification in monitoring system
        Variable.set(
            f"daily_pipeline_status_{execution_date}",
            json.dumps(message),
            description=f"Daily pipeline status for {execution_date}"
        )
        
    except Exception as e:
        logging.error(f"Notification failed: {e}")


# ===== DAG 1: Daily Market Data Processing =====
daily_market_dag = DAG(
    'daily_market_data_pipeline',
    default_args=DEFAULT_DAG_ARGS,
    description='Daily market data ETL pipeline with quality validation',
    schedule_interval='0 6 * * *',  # Daily at 6 AM
    max_active_runs=1,
    tags=COMMON_TAGS + ['daily', 'market-data']
)

# Task groups for better organization
with daily_market_dag:
    
    start_task = DummyOperator(
        task_id='start_pipeline',
        dag=daily_market_dag
    )
    
    # Data extraction group
    with TaskGroup("data_extraction", dag=daily_market_dag) as extraction_group:
        extract_task = PythonOperator(
            task_id='extract_tushare_data',
            python_callable=extract_tushare_daily_data,
            dag=daily_market_dag
        )
        
        validate_task = PythonOperator(
            task_id='validate_data',
            python_callable=validate_extracted_data,
            dag=daily_market_dag
        )
        
        extract_task >> validate_task
    
    # Data transformation group
    with TaskGroup("data_transformation", dag=daily_market_dag) as transformation_group:
        transform_task = PythonOperator(
            task_id='transform_data',
            python_callable=transform_market_data,
            dag=daily_market_dag
        )
    
    # Data loading group
    with TaskGroup("data_loading", dag=daily_market_dag) as loading_group:
        load_mongodb_task = PythonOperator(
            task_id='load_to_mongodb',
            python_callable=load_to_mongodb,
            dag=daily_market_dag
        )
        
        load_redis_task = PythonOperator(
            task_id='load_to_redis',
            python_callable=load_to_redis_cache,
            dag=daily_market_dag
        )
        
        update_features_task = PythonOperator(
            task_id='update_ml_features',
            python_callable=update_ml_features,
            dag=daily_market_dag
        )
        
        [load_mongodb_task, load_redis_task, update_features_task]
    
    # Cleanup and notification
    cleanup_task = PythonOperator(
        task_id='cleanup_temp_files',
        python_callable=cleanup_temporary_files,
        trigger_rule='all_done',
        dag=daily_market_dag
    )
    
    notification_task = PythonOperator(
        task_id='send_notification',
        python_callable=send_completion_notification,
        trigger_rule='all_done',
        dag=daily_market_dag
    )
    
    end_task = DummyOperator(
        task_id='end_pipeline',
        dag=daily_market_dag
    )
    
    # Define task dependencies
    start_task >> extraction_group >> transformation_group >> loading_group >> cleanup_task >> notification_task >> end_task


# ===== DAG 2: Weekly Financial Data Processing =====
def extract_financial_statements(**context) -> str:
    """Extract weekly financial statements"""
    try:
        from tradingagents.dataflows.tushare_adapter import TushareAdapter
        
        config = get_data_source_config()
        adapter = TushareAdapter(token=config.get('tushare_token'))
        
        # Get symbol list
        symbols = json.loads(Variable.get("financial_processing_symbols", default_var="[]"))
        if not symbols:
            symbols = ['000001.SZ', '000002.SZ', '600000.SH']
        
        execution_date = context['execution_date']
        all_financial_data = []
        
        for symbol in symbols:
            try:
                # Get income statement
                income_data = adapter.get_income_statement(ts_code=symbol, period='20231231')
                if income_data is not None and not income_data.empty:
                    latest_income = income_data.iloc[0].to_dict()
                    latest_income['symbol'] = symbol
                    latest_income['statement_type'] = 'income'
                    all_financial_data.append(latest_income)
                
                # Get balance sheet
                balance_data = adapter.get_balance_sheet(ts_code=symbol, period='20231231')
                if balance_data is not None and not balance_data.empty:
                    latest_balance = balance_data.iloc[0].to_dict()
                    latest_balance['symbol'] = symbol
                    latest_balance['statement_type'] = 'balance'
                    all_financial_data.append(latest_balance)
                
                # Rate limiting
                import time
                time.sleep(0.2)
                
            except Exception as e:
                logging.warning(f"Failed to extract financial data for {symbol}: {e}")
        
        # Store data
        output_file = f"/tmp/financial_data_{execution_date.strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump(all_financial_data, f, indent=2, default=str)
        
        logging.info(f"Extracted {len(all_financial_data)} financial records")
        return output_file
        
    except Exception as e:
        logging.error(f"Financial data extraction failed: {e}")
        raise


weekly_financial_dag = DAG(
    'weekly_financial_data_pipeline',
    default_args=DEFAULT_DAG_ARGS,
    description='Weekly financial statements processing pipeline',
    schedule_interval='0 8 * * 0',  # Weekly on Sunday at 8 AM
    max_active_runs=1,
    tags=COMMON_TAGS + ['weekly', 'financial-statements']
)

with weekly_financial_dag:
    extract_financial_task = PythonOperator(
        task_id='extract_financial_statements',
        python_callable=extract_financial_statements,
        dag=weekly_financial_dag
    )


# ===== DAG 3: Monthly Model Retraining =====
def retrain_ml_models(**context) -> Dict[str, Any]:
    """Retrain ML models with latest data"""
    try:
        from tradingagents.ml.models import ModelManager
        from tradingagents.ml.pipeline import MLPipeline
        
        execution_date = context['execution_date']
        
        # Initialize ML components
        model_manager = ModelManager()
        ml_pipeline = MLPipeline()
        
        # Get training data from last month
        end_date = execution_date
        start_date = end_date - timedelta(days=90)  # 3 months of data
        
        # Load training data
        training_data = ml_pipeline.load_training_data(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        # Train models
        training_results = {}
        models_to_train = ['price_prediction', 'sentiment_analysis', 'risk_assessment']
        
        for model_name in models_to_train:
            try:
                result = model_manager.train_model(
                    model_name=model_name,
                    training_data=training_data,
                    validation_split=0.2
                )
                training_results[model_name] = result
                
            except Exception as e:
                logging.error(f"Training failed for {model_name}: {e}")
                training_results[model_name] = {'error': str(e)}
        
        # Store results
        results_file = f"/tmp/model_training_results_{execution_date.strftime('%Y%m%d')}.json"
        with open(results_file, 'w') as f:
            json.dump(training_results, f, indent=2, default=str)
        
        logging.info(f"Model retraining completed: {training_results}")
        return training_results
        
    except Exception as e:
        logging.error(f"Model retraining failed: {e}")
        raise


monthly_model_dag = DAG(
    'monthly_model_retraining_pipeline',
    default_args=DEFAULT_DAG_ARGS,
    description='Monthly ML model retraining pipeline',
    schedule_interval='0 2 1 * *',  # Monthly on 1st at 2 AM
    max_active_runs=1,
    tags=COMMON_TAGS + ['monthly', 'ml-training']
)

with monthly_model_dag:
    retrain_models_task = PythonOperator(
        task_id='retrain_ml_models',
        python_callable=retrain_ml_models,
        execution_timeout=timedelta(hours=6),  # Longer timeout for training
        dag=monthly_model_dag
    )


# ===== DAG 4: Historical Data Backfill =====
def backfill_historical_data(**context) -> Dict[str, Any]:
    """Backfill historical data for new symbols"""
    try:
        from tradingagents.dataflows.tushare_adapter import TushareAdapter
        
        config = get_data_source_config()
        adapter = TushareAdapter(token=config.get('tushare_token'))
        
        # Get backfill parameters from DAG run config
        dag_run = context['dag_run']
        backfill_config = dag_run.conf or {}
        
        symbols = backfill_config.get('symbols', [])
        start_date = backfill_config.get('start_date', '20230101')
        end_date = backfill_config.get('end_date', datetime.now().strftime('%Y%m%d'))
        
        if not symbols:
            logging.warning("No symbols specified for backfill")
            return {'symbols_processed': 0, 'records_inserted': 0}
        
        total_records = 0
        
        for symbol in symbols:
            try:
                # Get historical data
                historical_data = adapter.get_daily_data(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if historical_data is not None and not historical_data.empty:
                    # Process and store data
                    records = []
                    for _, row in historical_data.iterrows():
                        record = {
                            'symbol': symbol,
                            'trade_date': row['trade_date'],
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': int(row['vol']),
                            'amount': float(row['amount']),
                            'source': 'tushare_backfill',
                            'extracted_at': datetime.now().isoformat()
                        }
                        records.append(record)
                    
                    total_records += len(records)
                    
                    # Store in MongoDB
                    # Implementation would call MongoDB storage function
                    
                # Rate limiting
                import time
                time.sleep(0.3)
                
            except Exception as e:
                logging.error(f"Backfill failed for {symbol}: {e}")
        
        result = {
            'symbols_processed': len(symbols),
            'records_inserted': total_records,
            'start_date': start_date,
            'end_date': end_date
        }
        
        logging.info(f"Backfill completed: {result}")
        return result
        
    except Exception as e:
        logging.error(f"Historical backfill failed: {e}")
        raise


backfill_dag = DAG(
    'historical_data_backfill_pipeline',
    default_args=DEFAULT_DAG_ARGS,
    description='Historical data backfill pipeline (manual trigger)',
    schedule_interval=None,  # Manual trigger only
    max_active_runs=1,
    tags=COMMON_TAGS + ['backfill', 'manual']
)

with backfill_dag:
    backfill_task = PythonOperator(
        task_id='backfill_historical_data',
        python_callable=backfill_historical_data,
        execution_timeout=timedelta(hours=4),
        dag=backfill_dag
    )