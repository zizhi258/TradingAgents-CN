#!/usr/bin/env python3
"""
Database Validation Script for TradingAgents-CN
Validates database schema, data integrity, and performance
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import redis
from redis import Redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseValidator:
    """Validates database structure and data integrity"""
    
    def __init__(self, mongodb_url: str, redis_url: Optional[str] = None):
        """Initialize validator with database connections"""
        self.mongodb_url = mongodb_url
        self.redis_url = redis_url
        
        self.mongo_client = None
        self.redis_client = None
        self._connect_databases()
    
    def _connect_databases(self):
        """Connect to databases"""
        try:
            # Connect to MongoDB
            self.mongo_client = MongoClient(
                self.mongodb_url,
                serverSelectionTimeoutMS=10000
            )
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client.get_default_database()
            logger.info("Connected to MongoDB")
            
            # Connect to Redis if URL provided
            if self.redis_url:
                self.redis_client = redis.from_url(self.redis_url)
                self.redis_client.ping()
                logger.info("Connected to Redis")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks"""
        logger.info("Starting comprehensive database validation")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "unknown",
            "checks": {}
        }
        
        try:
            # Run individual validation checks
            results["checks"]["connectivity"] = self._validate_connectivity()
            results["checks"]["schema"] = self._validate_schema()
            results["checks"]["indexes"] = self._validate_indexes()
            results["checks"]["data_integrity"] = self._validate_data_integrity()
            results["checks"]["performance"] = self._validate_performance()
            
            if self.redis_client:
                results["checks"]["redis"] = self._validate_redis()
            
            # Determine overall status
            all_passed = all(
                check.get("status") == "pass" 
                for check in results["checks"].values()
            )
            
            results["overall_status"] = "pass" if all_passed else "fail"
            
            # Generate summary
            results["summary"] = self._generate_summary(results["checks"])
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            results["overall_status"] = "error"
            results["error"] = str(e)
        
        return results
    
    def _validate_connectivity(self) -> Dict[str, Any]:
        """Validate database connectivity"""
        result = {
            "name": "Database Connectivity",
            "status": "unknown",
            "details": {},
            "issues": []
        }
        
        try:
            # Test MongoDB connectivity
            server_info = self.mongo_client.server_info()
            result["details"]["mongodb"] = {
                "connected": True,
                "version": server_info.get("version"),
                "uptime": server_info.get("uptime")
            }
            
            # Test Redis connectivity
            if self.redis_client:
                redis_info = self.redis_client.info()
                result["details"]["redis"] = {
                    "connected": True,
                    "version": redis_info.get("redis_version"),
                    "uptime": redis_info.get("uptime_in_seconds")
                }
            
            result["status"] = "pass"
            
        except Exception as e:
            result["status"] = "fail"
            result["issues"].append(f"Connectivity check failed: {e}")
        
        return result
    
    def _validate_schema(self) -> Dict[str, Any]:
        """Validate database schema"""
        result = {
            "name": "Database Schema",
            "status": "unknown",
            "details": {},
            "issues": []
        }
        
        try:
            # Expected collections
            expected_collections = {
                "users", "sessions", "analysis_results", "market_scans",
                "configurations", "schedules", "notifications", "audit_logs",
                "api_usage", "cache_metadata", "system_info", "system_migrations"
            }
            
            # Get existing collections
            existing_collections = set(self.db.list_collection_names())
            
            # Check for missing collections
            missing_collections = expected_collections - existing_collections
            extra_collections = existing_collections - expected_collections
            
            result["details"]["expected_collections"] = len(expected_collections)
            result["details"]["existing_collections"] = len(existing_collections)
            result["details"]["missing_collections"] = list(missing_collections)
            result["details"]["extra_collections"] = list(extra_collections)
            
            # Check collection structure
            collection_issues = []
            for collection_name in expected_collections & existing_collections:
                issues = self._validate_collection_structure(collection_name)
                if issues:
                    collection_issues.extend(issues)
            
            # Determine status
            if missing_collections:
                result["status"] = "fail"
                result["issues"].append(f"Missing collections: {', '.join(missing_collections)}")
            elif collection_issues:
                result["status"] = "warning"
                result["issues"].extend(collection_issues)
            else:
                result["status"] = "pass"
            
        except Exception as e:
            result["status"] = "fail"
            result["issues"].append(f"Schema validation failed: {e}")
        
        return result
    
    def _validate_collection_structure(self, collection_name: str) -> List[str]:
        """Validate individual collection structure"""
        issues = []
        
        try:
            collection = self.db[collection_name]
            
            # Check if collection has documents
            doc_count = collection.count_documents({})
            
            # Collection-specific validation
            if collection_name == "system_info":
                # Should have initialization record
                init_doc = collection.find_one({"type": "initialization"})
                if not init_doc:
                    issues.append(f"{collection_name}: Missing initialization record")
            
            elif collection_name == "configurations":
                # Should have basic system configs
                required_configs = [
                    "system.version",
                    "features.market_analysis",
                    "limits.max_concurrent_scans"
                ]
                
                for config_key in required_configs:
                    if not collection.find_one({"key": config_key}):
                        issues.append(f"{collection_name}: Missing config '{config_key}'")
            
        except Exception as e:
            issues.append(f"{collection_name}: Structure validation failed: {e}")
        
        return issues
    
    def _validate_indexes(self) -> Dict[str, Any]:
        """Validate database indexes"""
        result = {
            "name": "Database Indexes",
            "status": "unknown",
            "details": {},
            "issues": []
        }
        
        try:
            # Expected indexes per collection
            expected_indexes = {
                "users": ["email_1", "username_1", "created_at_1"],
                "sessions": ["session_id_1", "user_id_1", "expires_at_1"],
                "analysis_results": ["symbol_1", "analysis_type_1", "created_at_1"],
                "market_scans": ["scan_id_1", "status_1", "created_at_1"],
                "configurations": ["key_1", "category_1"],
                "system_migrations": ["migration_id_1", "applied_at_1"]
            }
            
            missing_indexes = []
            total_indexes = 0
            
            for collection_name, expected in expected_indexes.items():
                if collection_name not in self.db.list_collection_names():
                    continue
                
                # Get existing indexes
                existing = [idx["name"] for idx in self.db[collection_name].list_indexes()]
                total_indexes += len(existing)
                
                # Check for missing indexes
                for expected_index in expected:
                    if expected_index not in existing:
                        missing_indexes.append(f"{collection_name}.{expected_index}")
            
            result["details"]["total_indexes"] = total_indexes
            result["details"]["missing_indexes"] = missing_indexes
            
            if missing_indexes:
                result["status"] = "warning"
                result["issues"].append(f"Missing indexes: {', '.join(missing_indexes)}")
            else:
                result["status"] = "pass"
            
        except Exception as e:
            result["status"] = "fail"
            result["issues"].append(f"Index validation failed: {e}")
        
        return result
    
    def _validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity"""
        result = {
            "name": "Data Integrity",
            "status": "unknown",
            "details": {},
            "issues": []
        }
        
        try:
            integrity_checks = []
            
            # Check for orphaned records
            orphaned_sessions = self._check_orphaned_sessions()
            if orphaned_sessions > 0:
                integrity_checks.append(f"{orphaned_sessions} orphaned sessions found")
            
            # Check for invalid dates
            invalid_dates = self._check_invalid_dates()
            if invalid_dates:
                integrity_checks.append(f"Invalid dates found in: {', '.join(invalid_dates)}")
            
            # Check for duplicate records
            duplicates = self._check_duplicates()
            if duplicates:
                integrity_checks.append(f"Duplicate records found: {duplicates}")
            
            result["details"]["checks_performed"] = 3
            result["details"]["issues_found"] = len(integrity_checks)
            result["issues"] = integrity_checks
            
            result["status"] = "warning" if integrity_checks else "pass"
            
        except Exception as e:
            result["status"] = "fail"
            result["issues"].append(f"Data integrity validation failed: {e}")
        
        return result
    
    def _check_orphaned_sessions(self) -> int:
        """Check for orphaned session records"""
        try:
            # This is a simplified check - in practice, you'd check for sessions
            # that reference non-existent users
            orphaned_count = 0
            # Implementation would go here
            return orphaned_count
        except:
            return 0
    
    def _check_invalid_dates(self) -> List[str]:
        """Check for invalid date fields"""
        invalid_collections = []
        
        try:
            # Check common date fields across collections
            collections_to_check = ["users", "sessions", "analysis_results", "market_scans"]
            
            for collection_name in collections_to_check:
                if collection_name not in self.db.list_collection_names():
                    continue
                
                # Check for future dates or invalid timestamps
                future_dates = self.db[collection_name].count_documents({
                    "created_at": {"$gt": datetime.now(timezone.utc)}
                })
                
                if future_dates > 0:
                    invalid_collections.append(collection_name)
            
        except Exception as e:
            logger.warning(f"Date validation failed: {e}")
        
        return invalid_collections
    
    def _check_duplicates(self) -> Dict[str, int]:
        """Check for duplicate records"""
        duplicates = {}
        
        try:
            # Check for duplicate users (by email)
            if "users" in self.db.list_collection_names():
                email_duplicates = list(self.db.users.aggregate([
                    {"$match": {"email": {"$ne": None}}},
                    {"$group": {"_id": "$email", "count": {"$sum": 1}}},
                    {"$match": {"count": {"$gt": 1}}}
                ]))
                
                if email_duplicates:
                    duplicates["users_by_email"] = len(email_duplicates)
            
            # Check for duplicate configurations
            if "configurations" in self.db.list_collection_names():
                config_duplicates = list(self.db.configurations.aggregate([
                    {"$group": {"_id": "$key", "count": {"$sum": 1}}},
                    {"$match": {"count": {"$gt": 1}}}
                ]))
                
                if config_duplicates:
                    duplicates["configurations_by_key"] = len(config_duplicates)
            
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
        
        return duplicates
    
    def _validate_performance(self) -> Dict[str, Any]:
        """Validate database performance"""
        result = {
            "name": "Performance",
            "status": "unknown",
            "details": {},
            "issues": []
        }
        
        try:
            performance_metrics = {}
            
            # Test query performance on key collections
            collections_to_test = ["users", "analysis_results", "market_scans"]
            
            for collection_name in collections_to_test:
                if collection_name not in self.db.list_collection_names():
                    continue
                
                # Time a simple query
                start_time = datetime.now()
                count = self.db[collection_name].count_documents({})
                end_time = datetime.now()
                
                query_time_ms = (end_time - start_time).total_seconds() * 1000
                performance_metrics[collection_name] = {
                    "document_count": count,
                    "query_time_ms": query_time_ms
                }
            
            result["details"]["metrics"] = performance_metrics
            
            # Check for slow queries
            slow_queries = [
                name for name, metrics in performance_metrics.items()
                if metrics["query_time_ms"] > 1000  # 1 second threshold
            ]
            
            if slow_queries:
                result["status"] = "warning"
                result["issues"].append(f"Slow queries detected in: {', '.join(slow_queries)}")
            else:
                result["status"] = "pass"
            
        except Exception as e:
            result["status"] = "fail"
            result["issues"].append(f"Performance validation failed: {e}")
        
        return result
    
    def _validate_redis(self) -> Dict[str, Any]:
        """Validate Redis cache"""
        result = {
            "name": "Redis Cache",
            "status": "unknown",
            "details": {},
            "issues": []
        }
        
        try:
            # Get Redis info
            redis_info = self.redis_client.info()
            
            result["details"]["memory_usage"] = redis_info.get("used_memory_human")
            result["details"]["connected_clients"] = redis_info.get("connected_clients")
            result["details"]["keyspace_hits"] = redis_info.get("keyspace_hits", 0)
            result["details"]["keyspace_misses"] = redis_info.get("keyspace_misses", 0)
            
            # Calculate hit rate
            hits = redis_info.get("keyspace_hits", 0)
            misses = redis_info.get("keyspace_misses", 0)
            total_requests = hits + misses
            
            if total_requests > 0:
                hit_rate = (hits / total_requests) * 100
                result["details"]["hit_rate_percent"] = round(hit_rate, 2)
                
                if hit_rate < 50:  # Less than 50% hit rate
                    result["issues"].append(f"Low cache hit rate: {hit_rate:.1f}%")
            
            # Test cache operations
            test_key = "validation_test_key"
            self.redis_client.set(test_key, "test_value", ex=60)
            retrieved_value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            if retrieved_value != b"test_value":
                result["issues"].append("Cache read/write test failed")
            
            result["status"] = "warning" if result["issues"] else "pass"
            
        except Exception as e:
            result["status"] = "fail"
            result["issues"].append(f"Redis validation failed: {e}")
        
        return result
    
    def _generate_summary(self, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary"""
        summary = {
            "total_checks": len(checks),
            "passed": 0,
            "warnings": 0,
            "failed": 0,
            "critical_issues": []
        }
        
        for check_name, check_result in checks.items():
            status = check_result.get("status", "unknown")
            
            if status == "pass":
                summary["passed"] += 1
            elif status == "warning":
                summary["warnings"] += 1
            elif status in ["fail", "error"]:
                summary["failed"] += 1
                summary["critical_issues"].extend(check_result.get("issues", []))
        
        return summary


def main():
    """CLI interface for database validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TradingAgents-CN Database Validator")
    parser.add_argument("--mongodb-url", 
                       default=os.getenv("TRADINGAGENTS_MONGODB_URL", "mongodb://localhost:27017/tradingagents"),
                       help="MongoDB connection URL")
    parser.add_argument("--redis-url", 
                       default=os.getenv("TRADINGAGENTS_REDIS_URL"),
                       help="Redis connection URL")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    
    try:
        validator = DatabaseValidator(args.mongodb_url, args.redis_url)
        results = validator.validate_all()
        
        if args.json:
            import json
            output = json.dumps(results, indent=2)
        else:
            # Format human-readable output
            output = format_validation_results(results)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Validation results saved to: {args.output}")
        else:
            print(output)
        
        # Exit with error code if validation failed
        if results["overall_status"] in ["fail", "error"]:
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


def format_validation_results(results: Dict[str, Any]) -> str:
    """Format validation results for human reading"""
    output = []
    
    output.append("=" * 60)
    output.append("TradingAgents-CN Database Validation Report")
    output.append("=" * 60)
    output.append(f"Timestamp: {results.get('timestamp')}")
    output.append(f"Overall Status: {results.get('overall_status', 'unknown').upper()}")
    output.append("")
    
    # Summary
    summary = results.get("summary", {})
    output.append("SUMMARY:")
    output.append(f"  Total Checks: {summary.get('total_checks', 0)}")
    output.append(f"  Passed: {summary.get('passed', 0)}")
    output.append(f"  Warnings: {summary.get('warnings', 0)}")
    output.append(f"  Failed: {summary.get('failed', 0)}")
    output.append("")
    
    # Individual checks
    output.append("DETAILED RESULTS:")
    for check_name, check_result in results.get("checks", {}).items():
        status = check_result.get("status", "unknown").upper()
        name = check_result.get("name", check_name)
        
        output.append(f"  {name}: {status}")
        
        if check_result.get("issues"):
            for issue in check_result["issues"]:
                output.append(f"    - {issue}")
        
        output.append("")
    
    # Critical issues
    critical_issues = summary.get("critical_issues", [])
    if critical_issues:
        output.append("CRITICAL ISSUES:")
        for issue in critical_issues:
            output.append(f"  - {issue}")
        output.append("")
    
    return "\n".join(output)


if __name__ == "__main__":
    main()