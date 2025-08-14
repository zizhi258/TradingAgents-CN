# TradingAgents-CN Database Migration Strategy

## Overview

This document outlines the comprehensive migration strategy from the current MongoDB-only setup to the optimized hybrid architecture (PostgreSQL + TimescaleDB + MongoDB + Redis). The migration is designed to be zero-downtime with robust rollback capabilities.

## 1. Current State Analysis

### 1.1 Existing MongoDB Collections

Based on the current TradingAgents-CN codebase, the following MongoDB collections are currently in use:

```javascript
// Current MongoDB Collections (tradingagents database)
existing_collections = {
    // Token usage and API tracking
    "token_usage": {
        structure: "flat documents",
        size_estimate: "~1GB",
        growth_rate: "~10MB/day",
        migration_target: "PostgreSQL api_usage table"
    },
    
    // User configurations and subscriptions  
    "subscription_users": {
        structure: "user documents with nested configs",
        size_estimate: "~100MB", 
        growth_rate: "~1MB/day",
        migration_target: "PostgreSQL users + user_configs tables"
    },
    
    // Market analysis results (inferred from codebase)
    "analysis_results": {
        structure: "nested analysis documents",
        size_estimate: "~2GB",
        growth_rate: "~50MB/day", 
        migration_target: "MongoDB (optimized schema)"
    },
    
    // Session data and temporary results
    "sessions": {
        structure: "session documents", 
        size_estimate: "~500MB",
        growth_rate: "~20MB/day",
        migration_target: "Redis + PostgreSQL"
    },
    
    // Configuration and metadata
    "metadata": {
        structure: "configuration documents",
        size_estimate: "~10MB",
        growth_rate: "~1MB/month",
        migration_target: "PostgreSQL + file config"
    }
};
```

### 1.2 Data Volume Assessment

```python
class DataVolumeAssessment:
    def __init__(self):
        self.current_mongo_db = MongoClient()['tradingagents']
        
    def analyze_current_data(self):
        """Analyze current MongoDB data volume and patterns"""
        analysis = {}
        
        for collection_name in self.current_mongo_db.list_collection_names():
            collection = self.current_mongo_db[collection_name]
            
            analysis[collection_name] = {
                'document_count': collection.count_documents({}),
                'avg_document_size': self.get_avg_document_size(collection),
                'total_size_mb': self.get_collection_size_mb(collection),
                'indexes': collection.list_indexes(),
                'growth_pattern': self.analyze_growth_pattern(collection),
                'access_patterns': self.analyze_access_patterns(collection)
            }
        
        return analysis
    
    def estimate_migration_time(self, analysis):
        """Estimate migration time based on data volume"""
        total_documents = sum(col['document_count'] for col in analysis.values())
        total_size_gb = sum(col['total_size_mb'] for col in analysis.values()) / 1024
        
        # Migration speed estimates (conservative)
        migration_speed = {
            'documents_per_second': 1000,  # Conservative estimate
            'gb_per_hour': 10,             # Including transformation time
            'parallel_workers': 4
        }
        
        time_by_documents = total_documents / migration_speed['documents_per_second'] / 3600
        time_by_size = total_size_gb / migration_speed['gb_per_hour']
        
        estimated_hours = max(time_by_documents, time_by_size)
        
        return {
            'total_documents': total_documents,
            'total_size_gb': total_size_gb,
            'estimated_migration_hours': estimated_hours,
            'parallel_workers': migration_speed['parallel_workers'],
            'recommended_window': f"{estimated_hours * 1.5:.1f} hours"  # 50% buffer
        }
```

## 2. Migration Architecture

### 2.1 Migration Components

```yaml
# Migration Infrastructure
migration_architecture:
  # Data Processing Pipeline
  extraction_service:
    type: "Python service"
    purpose: "Extract data from MongoDB"
    parallelism: 4
    batch_size: 1000
    
  transformation_service:
    type: "Python service with Pandas"
    purpose: "Transform and validate data"
    memory_allocation: "8GB per worker"
    validation_rules: "strict"
    
  loading_service:
    type: "Multi-target loader"
    targets: ["PostgreSQL", "MongoDB_new", "Redis"]
    transaction_mode: "batch_transactions"
    
  # Monitoring and Control
  migration_coordinator:
    type: "Orchestration service"
    features: ["progress_tracking", "error_handling", "rollback"]
    monitoring_interval: "10s"
    
  # Data Validation
  validation_service:
    type: "Data quality checker"
    checks: ["count_validation", "sample_comparison", "business_rules"]
    sampling_rate: 0.1  # 10% sample validation

# Migration Database
migration_tracking:
  database: "migration_control"
  tables:
    - "migration_batches"      # Track batch processing
    - "migration_errors"       # Error logging
    - "validation_results"     # Data quality results
    - "rollback_checkpoints"   # Rollback points
```

### 2.2 Migration Phases

```python
class MigrationOrchestrator:
    def __init__(self):
        self.migration_phases = {
            'phase_1_preparation': {
                'duration': '1 week',
                'activities': [
                    'setup_new_infrastructure',
                    'create_migration_database',
                    'implement_migration_tools',
                    'create_rollback_procedures'
                ]
            },
            'phase_2_schema_migration': {
                'duration': '1 week', 
                'activities': [
                    'create_postgresql_schemas',
                    'create_optimized_mongodb_schemas',
                    'setup_redis_cluster',
                    'configure_indexes'
                ]
            },
            'phase_3_data_migration': {
                'duration': '2-3 weeks',
                'activities': [
                    'migrate_static_data',      # Reference data first
                    'migrate_historical_data',   # Historical data
                    'migrate_active_data',      # Current operational data
                    'validate_migration'
                ]
            },
            'phase_4_cutover': {
                'duration': '1 week',
                'activities': [
                    'final_data_sync',
                    'application_cutover',
                    'monitor_new_system',
                    'decommission_old_system'
                ]
            }
        }
    
    async def execute_migration(self):
        """Execute the complete migration process"""
        for phase_name, phase_config in self.migration_phases.items():
            logger.info(f"Starting {phase_name}")
            
            try:
                await self.execute_phase(phase_name, phase_config)
                await self.create_checkpoint(phase_name)
                logger.info(f"Completed {phase_name}")
                
            except Exception as e:
                logger.error(f"Phase {phase_name} failed: {e}")
                await self.initiate_rollback(phase_name)
                raise
```

## 3. Data Migration Mappings

### 3.1 MongoDB to PostgreSQL Migration

```python
# Migration mappings for relational data
MONGODB_TO_POSTGRESQL_MAPPINGS = {
    'token_usage': {
        'target_table': 'api_usage',
        'transformation': {
            '_id': 'SKIP',  # Use PostgreSQL auto-increment
            'timestamp': 'timestamp',
            'provider': 'provider', 
            'model_name': 'model_name',
            'input_tokens': 'input_tokens',
            'output_tokens': 'output_tokens',
            'cost': 'cost',
            'session_id': 'session_id',
            'user_id': 'user_id',
            'analysis_type': 'analysis_type',
            'metadata': 'metadata::jsonb'  # Store as JSONB
        },
        'data_type_conversions': {
            'timestamp': 'datetime_to_timestamptz',
            'cost': 'decimal_conversion',
            'metadata': 'json_conversion'
        },
        'validation_rules': [
            'timestamp_not_null',
            'cost_non_negative', 
            'provider_in_allowed_list'
        ]
    },
    
    'subscription_users': {
        'target_tables': ['users', 'user_configs'],
        'transformation': {
            # Users table
            '_id': 'SKIP',
            'username': 'users.username',
            'email': 'users.email', 
            'full_name': 'users.full_name',
            'created_at': 'users.created_at',
            'is_active': 'users.is_active',
            
            # User configs table (nested data)
            'preferences': 'user_configs.config_data',
            'watchlist': 'user_configs.config_data',
            'alert_settings': 'user_configs.config_data'
        },
        'nested_handling': {
            'preferences': {
                'target': 'user_configs',
                'config_type': 'preferences'
            },
            'watchlist': {
                'target': 'user_configs',
                'config_type': 'watchlist'
            }
        }
    }
}

class MongoToPostgreSQLMigrator:
    def __init__(self, mapping_config):
        self.mapping = mapping_config
        self.postgres_conn = self.create_postgres_connection()
        self.mongo_conn = self.create_mongo_connection()
    
    async def migrate_collection(self, collection_name, batch_size=1000):
        """Migrate a MongoDB collection to PostgreSQL"""
        mapping = self.mapping[collection_name]
        source_collection = self.mongo_conn[collection_name]
        
        # Get total document count for progress tracking
        total_docs = source_collection.count_documents({})
        processed_docs = 0
        
        # Process in batches
        async for batch in self.get_batches(source_collection, batch_size):
            try:
                transformed_batch = await self.transform_batch(batch, mapping)
                await self.load_batch_to_postgres(transformed_batch, mapping)
                
                processed_docs += len(batch)
                progress = (processed_docs / total_docs) * 100
                
                logger.info(f"Migrated {collection_name}: {progress:.1f}% complete")
                
                # Create checkpoint for rollback
                await self.create_batch_checkpoint(collection_name, processed_docs)
                
            except Exception as e:
                logger.error(f"Batch migration failed: {e}")
                await self.handle_migration_error(collection_name, batch, e)
                raise
    
    async def transform_batch(self, batch, mapping):
        """Transform MongoDB documents to PostgreSQL format"""
        transformed_records = []
        
        for doc in batch:
            try:
                if 'target_tables' in mapping:
                    # Handle one-to-many relationships
                    records = await self.transform_to_multiple_tables(doc, mapping)
                    transformed_records.extend(records)
                else:
                    # Handle simple one-to-one mapping
                    record = await self.transform_document(doc, mapping)
                    transformed_records.append(record)
                    
            except Exception as e:
                logger.error(f"Document transformation failed: {e}")
                await self.log_transformation_error(doc, e)
                continue  # Skip problematic documents
        
        return transformed_records
    
    async def validate_migration(self, collection_name):
        """Validate migrated data integrity"""
        mapping = self.mapping[collection_name]
        
        # Count validation
        mongo_count = self.mongo_conn[collection_name].count_documents({})
        postgres_count = await self.get_postgres_count(mapping['target_table'])
        
        if mongo_count != postgres_count:
            raise ValueError(f"Count mismatch: MongoDB {mongo_count} vs PostgreSQL {postgres_count}")
        
        # Sample validation
        await self.validate_sample_data(collection_name, sample_size=1000)
        
        # Business rule validation
        await self.validate_business_rules(collection_name)
        
        logger.info(f"Validation completed for {collection_name}")
```

### 3.2 MongoDB Schema Optimization Migration

```python
class MongoSchemaOptimizer:
    def __init__(self):
        self.schema_optimizations = {
            'analysis_results': {
                'current_issues': [
                    'inconsistent_field_names',
                    'nested_arrays_too_deep',
                    'missing_indexes',
                    'no_schema_validation'
                ],
                'optimizations': [
                    'normalize_field_names',
                    'flatten_nested_structures', 
                    'add_compound_indexes',
                    'implement_schema_validation'
                ]
            }
        }
    
    async def optimize_mongodb_schema(self, collection_name):
        """Migrate to optimized MongoDB schema"""
        old_collection = self.mongo_conn[collection_name]
        new_collection = self.mongo_conn[f"{collection_name}_optimized"]
        
        # Create new collection with schema validation
        await self.create_optimized_collection(new_collection, collection_name)
        
        # Migrate data with transformations
        async for batch in self.get_batches(old_collection, 1000):
            optimized_batch = []
            
            for doc in batch:
                try:
                    optimized_doc = await self.optimize_document(doc, collection_name)
                    optimized_batch.append(optimized_doc)
                except Exception as e:
                    logger.error(f"Document optimization failed: {e}")
                    await self.log_optimization_error(doc, e)
            
            if optimized_batch:
                await new_collection.insert_many(optimized_batch)
        
        # Validate optimization
        await self.validate_optimization(collection_name)
        
        # Create indexes on optimized collection
        await self.create_optimized_indexes(new_collection, collection_name)
    
    async def optimize_document(self, doc, collection_name):
        """Optimize individual document structure"""
        optimizations = self.schema_optimizations[collection_name]['optimizations']
        optimized_doc = doc.copy()
        
        for optimization in optimizations:
            if optimization == 'normalize_field_names':
                optimized_doc = await self.normalize_field_names(optimized_doc)
            elif optimization == 'flatten_nested_structures':
                optimized_doc = await self.flatten_nested_structures(optimized_doc)
            # Add more optimization methods as needed
        
        return optimized_doc
```

## 4. Zero-Downtime Migration Strategy

### 4.1 Dual-Write Approach

```python
class DualWriteManager:
    def __init__(self):
        self.old_mongo_client = MongoClient("mongodb://old-cluster")
        self.new_infrastructure = {
            'postgres': self.create_postgres_pool(),
            'mongo_new': MongoClient("mongodb://new-cluster"), 
            'redis': redis.RedisCluster(...)
        }
        self.dual_write_enabled = False
        self.write_validation_enabled = True
    
    async def enable_dual_write(self):
        """Enable dual writes to old and new systems"""
        self.dual_write_enabled = True
        logger.info("Dual write mode enabled")
    
    async def write_data(self, operation_type, data, collection_name):
        """Write data to both old and new systems"""
        results = {}
        
        # Write to old system (primary)
        try:
            results['old'] = await self.write_to_old_system(
                operation_type, data, collection_name
            )
        except Exception as e:
            logger.error(f"Old system write failed: {e}")
            raise  # Fail the operation if old system fails
        
        # Write to new system (if dual write enabled)
        if self.dual_write_enabled:
            try:
                results['new'] = await self.write_to_new_system(
                    operation_type, data, collection_name
                )
                
                # Validate consistency if enabled
                if self.write_validation_enabled:
                    await self.validate_write_consistency(results)
                    
            except Exception as e:
                logger.error(f"New system write failed: {e}")
                # Don't fail the operation, but log for investigation
                await self.log_dual_write_error(operation_type, data, e)
        
        return results['old']  # Return old system result during transition
    
    async def validate_write_consistency(self, results):
        """Validate that writes to both systems are consistent"""
        # Implement consistency checks based on operation type
        pass
```

### 4.2 Gradual Cutover Process

```python
class GradualCutoverManager:
    def __init__(self):
        self.cutover_strategy = {
            'phase_1_reads': {
                'percentage': 10,  # 10% of reads from new system
                'duration': '1 week',
                'monitoring_intensive': True
            },
            'phase_2_reads': {
                'percentage': 50,  # 50% of reads from new system
                'duration': '1 week', 
                'performance_comparison': True
            },
            'phase_3_reads': {
                'percentage': 90,  # 90% of reads from new system
                'duration': '1 week',
                'final_validation': True
            },
            'phase_4_writes': {
                'cutover': 'complete',  # Switch writes to new system
                'monitoring': '24/7 for 1 week',
                'rollback_ready': True
            }
        }
    
    async def execute_gradual_cutover(self):
        """Execute gradual cutover with monitoring"""
        for phase_name, phase_config in self.cutover_strategy.items():
            logger.info(f"Starting cutover {phase_name}")
            
            try:
                await self.execute_cutover_phase(phase_name, phase_config)
                await self.monitor_phase_performance(phase_name, phase_config)
                
                # Validate phase success before proceeding
                if not await self.validate_phase_success(phase_name):
                    raise Exception(f"Phase {phase_name} validation failed")
                    
                logger.info(f"Cutover {phase_name} completed successfully")
                
            except Exception as e:
                logger.error(f"Cutover phase {phase_name} failed: {e}")
                await self.rollback_cutover_phase(phase_name)
                raise
    
    async def smart_traffic_routing(self, request_type, user_id=None):
        """Intelligently route traffic based on cutover phase"""
        current_phase = await self.get_current_cutover_phase()
        
        if request_type == 'read':
            percentage = self.cutover_strategy[current_phase].get('percentage', 0)
            
            # Use consistent hashing for user-specific routing
            if user_id:
                hash_value = hash(str(user_id)) % 100
                return 'new_system' if hash_value < percentage else 'old_system'
            else:
                # Random routing for non-user-specific requests
                return 'new_system' if random.randint(0, 99) < percentage else 'old_system'
        
        elif request_type == 'write':
            if current_phase == 'phase_4_writes':
                return 'new_system'
            else:
                return 'dual_write'  # Write to both systems
```

## 5. Data Validation & Quality Assurance

### 5.1 Comprehensive Validation Framework

```python
class MigrationValidationFramework:
    def __init__(self):
        self.validation_rules = {
            'count_validation': self.validate_record_counts,
            'sample_validation': self.validate_sample_data,
            'business_rule_validation': self.validate_business_rules,
            'referential_integrity': self.validate_referential_integrity,
            'data_type_validation': self.validate_data_types,
            'performance_validation': self.validate_performance
        }
    
    async def comprehensive_validation(self, migration_batch):
        """Run all validation checks"""
        validation_results = {}
        
        for validation_name, validation_func in self.validation_rules.items():
            try:
                result = await validation_func(migration_batch)
                validation_results[validation_name] = {
                    'status': 'passed' if result else 'failed',
                    'details': result
                }
            except Exception as e:
                validation_results[validation_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Overall validation status
        overall_status = 'passed' if all(
            r['status'] == 'passed' for r in validation_results.values()
        ) else 'failed'
        
        return {
            'overall_status': overall_status,
            'individual_results': validation_results,
            'timestamp': datetime.utcnow(),
            'batch_id': migration_batch['batch_id']
        }
    
    async def validate_sample_data(self, migration_batch, sample_size=100):
        """Validate a sample of migrated data"""
        sample_results = []
        
        # Get random sample from old and new systems
        old_sample = await self.get_sample_from_old_system(
            migration_batch['collection'], sample_size
        )
        
        for old_record in old_sample:
            try:
                # Find corresponding record in new system
                new_record = await self.find_corresponding_record(
                    old_record, migration_batch['target_system']
                )
                
                if new_record:
                    # Compare records
                    comparison_result = await self.compare_records(old_record, new_record)
                    sample_results.append(comparison_result)
                else:
                    sample_results.append({
                        'record_id': old_record.get('_id'),
                        'status': 'missing_in_new_system'
                    })
                    
            except Exception as e:
                sample_results.append({
                    'record_id': old_record.get('_id'),
                    'status': 'validation_error',
                    'error': str(e)
                })
        
        # Calculate validation statistics
        total_samples = len(sample_results)
        successful_validations = len([r for r in sample_results if r['status'] == 'match'])
        
        return {
            'total_samples': total_samples,
            'successful_validations': successful_validations,
            'success_rate': successful_validations / total_samples if total_samples > 0 else 0,
            'sample_details': sample_results[:10]  # Include first 10 for debugging
        }
```

### 5.2 Performance Regression Testing

```python
class PerformanceRegressionTester:
    def __init__(self):
        self.performance_benchmarks = {
            'query_response_time': {'baseline': 100, 'threshold': 150},  # ms
            'throughput': {'baseline': 1000, 'threshold': 800},         # req/sec
            'memory_usage': {'baseline': 2048, 'threshold': 3072},      # MB
            'cpu_utilization': {'baseline': 60, 'threshold': 80}        # percentage
        }
    
    async def run_performance_regression_tests(self):
        """Run comprehensive performance tests"""
        test_results = {}
        
        # Database query performance tests
        test_results['query_performance'] = await self.test_query_performance()
        
        # API endpoint performance tests
        test_results['api_performance'] = await self.test_api_performance()
        
        # System resource usage tests
        test_results['resource_usage'] = await self.test_resource_usage()
        
        # Load testing
        test_results['load_testing'] = await self.test_load_performance()
        
        return self.analyze_performance_results(test_results)
    
    async def test_query_performance(self):
        """Test key query performance"""
        query_tests = [
            {
                'name': 'recent_market_data',
                'query': "SELECT * FROM market_data WHERE symbol = 'AAPL' AND timestamp > NOW() - INTERVAL '1 day'",
                'expected_time_ms': 50
            },
            {
                'name': 'user_analysis_history', 
                'query': "SELECT * FROM agent_analysis_results WHERE user_id = ? ORDER BY analysis_timestamp DESC LIMIT 50",
                'expected_time_ms': 100
            }
            # Add more critical queries
        ]
        
        results = []
        for test in query_tests:
            execution_time = await self.measure_query_time(test['query'])
            results.append({
                'query': test['name'],
                'execution_time_ms': execution_time,
                'expected_time_ms': test['expected_time_ms'],
                'performance_ratio': execution_time / test['expected_time_ms']
            })
        
        return results
```

## 6. Rollback Strategy

### 6.1 Rollback Decision Framework

```python
class RollbackDecisionEngine:
    def __init__(self):
        self.rollback_triggers = {
            'critical_errors': {
                'data_corruption': True,
                'complete_system_failure': True,
                'security_breach': True
            },
            'performance_degradation': {
                'query_time_increase': 3.0,    # 3x slower
                'throughput_decrease': 0.5,     # 50% reduction
                'error_rate_increase': 0.05     # 5% error rate
            },
            'data_consistency_issues': {
                'validation_failure_rate': 0.01,  # 1% validation failures
                'missing_records': 100,            # Missing records threshold
                'corrupted_records': 10            # Corrupted records threshold
            }
        }
    
    async def should_trigger_rollback(self, monitoring_data):
        """Determine if rollback should be triggered"""
        rollback_reasons = []
        
        # Check for critical errors
        for error_type, should_trigger in self.rollback_triggers['critical_errors'].items():
            if monitoring_data.get(error_type) and should_trigger:
                rollback_reasons.append(f"Critical error: {error_type}")
        
        # Check performance degradation
        perf_data = monitoring_data.get('performance', {})
        if perf_data.get('query_time_ratio', 1) > self.rollback_triggers['performance_degradation']['query_time_increase']:
            rollback_reasons.append("Query performance degradation")
        
        # Check data consistency
        consistency_data = monitoring_data.get('data_consistency', {})
        if consistency_data.get('validation_failure_rate', 0) > self.rollback_triggers['data_consistency_issues']['validation_failure_rate']:
            rollback_reasons.append("Data validation failure rate exceeded")
        
        return {
            'should_rollback': len(rollback_reasons) > 0,
            'reasons': rollback_reasons,
            'severity': self.calculate_severity(rollback_reasons)
        }
    
    async def execute_rollback(self, rollback_decision):
        """Execute rollback procedure"""
        severity = rollback_decision['severity']
        
        if severity == 'critical':
            await self.immediate_rollback()
        elif severity == 'high':
            await self.expedited_rollback()
        else:
            await self.planned_rollback()
```

### 6.2 Point-in-Time Recovery

```python
class PointInTimeRecovery:
    def __init__(self):
        self.recovery_checkpoints = {}
        
    async def create_checkpoint(self, checkpoint_name, metadata=None):
        """Create recovery checkpoint"""
        checkpoint = {
            'name': checkpoint_name,
            'timestamp': datetime.utcnow(),
            'database_snapshots': await self.create_database_snapshots(),
            'application_state': await self.capture_application_state(),
            'configuration_backup': await self.backup_configurations(),
            'metadata': metadata or {}
        }
        
        self.recovery_checkpoints[checkpoint_name] = checkpoint
        await self.persist_checkpoint(checkpoint)
        
        logger.info(f"Recovery checkpoint '{checkpoint_name}' created")
        
    async def rollback_to_checkpoint(self, checkpoint_name):
        """Rollback to specific checkpoint"""
        if checkpoint_name not in self.recovery_checkpoints:
            raise ValueError(f"Checkpoint '{checkpoint_name}' not found")
        
        checkpoint = self.recovery_checkpoints[checkpoint_name]
        
        try:
            # Stop application services
            await self.stop_application_services()
            
            # Restore database snapshots
            await self.restore_database_snapshots(checkpoint['database_snapshots'])
            
            # Restore configurations
            await self.restore_configurations(checkpoint['configuration_backup'])
            
            # Restore application state
            await self.restore_application_state(checkpoint['application_state'])
            
            # Restart services
            await self.start_application_services()
            
            # Validate rollback
            await self.validate_rollback_success(checkpoint_name)
            
            logger.info(f"Successfully rolled back to checkpoint '{checkpoint_name}'")
            
        except Exception as e:
            logger.error(f"Rollback to checkpoint '{checkpoint_name}' failed: {e}")
            raise
```

## 7. Implementation Timeline

### 7.1 Detailed Migration Schedule

```yaml
migration_timeline:
  # Preparation Phase (Week 1-2)
  preparation:
    week_1:
      - day_1_2: "Infrastructure setup (PostgreSQL + TimescaleDB)"
      - day_3_4: "Redis cluster configuration"
      - day_5_7: "Migration tools development and testing"
    
    week_2:  
      - day_1_3: "Data analysis and mapping creation"
      - day_4_5: "Validation framework implementation"
      - day_6_7: "Rollback procedures development"
  
  # Schema Creation Phase (Week 3)
  schema_creation:
    - day_1_2: "PostgreSQL schema creation and optimization"
    - day_3_4: "MongoDB optimized schema creation"
    - day_5_7: "Index creation and performance testing"
  
  # Data Migration Phase (Week 4-6)
  data_migration:
    week_4:
      - "Static reference data migration"
      - "Historical data migration (>1 year old)"
    
    week_5:
      - "Recent data migration (last year)"
      - "User data and configurations migration"
    
    week_6:
      - "Active operational data migration"
      - "Final data synchronization"
  
  # Testing Phase (Week 7)
  testing:
    - day_1_3: "Data validation and integrity testing"
    - day_4_5: "Performance regression testing"
    - day_6_7: "End-to-end system testing"
  
  # Cutover Phase (Week 8)
  cutover:
    - day_1: "Enable dual-write mode"
    - day_2_3: "Gradual read traffic cutover (10% -> 50%)"
    - day_4_5: "Complete read traffic cutover (90% -> 100%)"
    - day_6: "Write traffic cutover"
    - day_7: "System monitoring and optimization"

# Resource Allocation
resources:
  personnel:
    - migration_lead: "1 senior engineer"
    - database_engineers: "2 engineers"
    - application_engineers: "2 engineers" 
    - qa_engineers: "1 engineer"
    - devops_engineers: "1 engineer"
  
  infrastructure:
    - staging_environment: "Full replica of production"
    - migration_tools: "Dedicated server cluster"
    - monitoring_tools: "Enhanced monitoring setup"
    - backup_storage: "Additional storage for checkpoints"
```

This comprehensive migration strategy ensures a smooth transition from the current MongoDB setup to the optimized hybrid architecture while maintaining zero downtime and providing robust rollback capabilities.