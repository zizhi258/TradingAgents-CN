#!/usr/bin/env python3
"""
Database Migration System for TradingAgents-CN
Handles schema updates, data migrations, and database initialization
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import redis
from redis import Redis
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Migration types"""
    SCHEMA = "schema"
    DATA = "data"
    INDEX = "index"
    CLEANUP = "cleanup"


@dataclass
class Migration:
    """Migration definition"""
    id: str
    name: str
    description: str
    type: MigrationType
    version: str
    created_at: str
    dependencies: List[str]
    rollback_available: bool = False


class DatabaseMigrationManager:
    """Manages database migrations and initialization"""
    
    def __init__(self, mongodb_url: str, redis_url: Optional[str] = None):
        """
        Initialize migration manager
        
        Args:
            mongodb_url: MongoDB connection URL
            redis_url: Optional Redis connection URL
        """
        self.mongodb_url = mongodb_url
        self.redis_url = redis_url
        
        # Initialize database connections
        self.mongo_client = None
        self.redis_client = None
        self._connect_databases()
        
        # Migration tracking
        self.migration_collection = "system_migrations"
        self.migrations_dir = Path("scripts/migrations")
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
    
    def _connect_databases(self):
        """Connect to databases"""
        try:
            # Connect to MongoDB
            self.mongo_client = MongoClient(
                self.mongodb_url,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=20000,
                socketTimeoutMS=20000
            )
            
            # Test MongoDB connection
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
    
    def initialize_database(self, force: bool = False):
        """
        Initialize database with base schema and indexes
        
        Args:
            force: Force initialization even if already initialized
        """
        logger.info("Initializing TradingAgents-CN database")
        
        # Check if already initialized
        if not force and self._is_initialized():
            logger.info("Database already initialized")
            return
        
        try:
            # Create collections and indexes
            self._create_base_collections()
            self._create_indexes()
            self._create_migration_tracking()
            self._insert_initial_data()
            
            # Mark as initialized
            self._mark_initialized()
            
            logger.info("Database initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _is_initialized(self) -> bool:
        """Check if database is initialized"""
        try:
            init_doc = self.db.system_info.find_one({"type": "initialization"})
            return init_doc is not None
        except:
            return False
    
    def _mark_initialized(self):
        """Mark database as initialized"""
        self.db.system_info.update_one(
            {"type": "initialization"},
            {
                "$set": {
                    "type": "initialization",
                    "initialized_at": datetime.now(timezone.utc),
                    "version": "1.0.0"
                }
            },
            upsert=True
        )
    
    def _create_base_collections(self):
        """Create base collections"""
        collections = {
            "users": "User accounts and profiles",
            "sessions": "User sessions and authentication",
            "analysis_results": "Stock analysis results",
            "market_scans": "Market-wide analysis scans",
            "configurations": "Application configurations",
            "schedules": "Scheduled tasks and jobs",
            "notifications": "User notifications",
            "audit_logs": "System audit logs",
            "api_usage": "API usage tracking",
            "cache_metadata": "Cache metadata and statistics",
            "system_info": "System information and status",
            "system_migrations": "Migration tracking"
        }
        
        for collection_name, description in collections.items():
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")
                
                # Add collection metadata
                self.db[collection_name].insert_one({
                    "_collection_meta": {
                        "description": description,
                        "created_at": datetime.now(timezone.utc),
                        "version": "1.0.0"
                    }
                })
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        indexes = {
            "users": [
                {"key": [("email", 1)], "unique": True, "sparse": True},
                {"key": [("username", 1)], "unique": True, "sparse": True},
                {"key": [("created_at", 1)]},
                {"key": [("last_login", 1)]}
            ],
            "sessions": [
                {"key": [("session_id", 1)], "unique": True},
                {"key": [("user_id", 1)]},
                {"key": [("expires_at", 1)]},
                {"key": [("created_at", 1)]}
            ],
            "analysis_results": [
                {"key": [("symbol", 1)]},
                {"key": [("analysis_type", 1)]},
                {"key": [("created_at", 1)]},
                {"key": [("user_id", 1)]},
                {"key": [("symbol", 1), ("analysis_type", 1), ("created_at", -1)]}
            ],
            "market_scans": [
                {"key": [("scan_id", 1)], "unique": True},
                {"key": [("status", 1)]},
                {"key": [("created_at", 1)]},
                {"key": [("user_id", 1)]},
                {"key": [("market_type", 1)]},
                {"key": [("created_at", -1), ("status", 1)]}
            ],
            "configurations": [
                {"key": [("key", 1)], "unique": True},
                {"key": [("category", 1)]},
                {"key": [("updated_at", 1)]}
            ],
            "schedules": [
                {"key": [("job_id", 1)], "unique": True},
                {"key": [("status", 1)]},
                {"key": [("next_run", 1)]},
                {"key": [("job_type", 1)]},
                {"key": [("created_at", 1)]}
            ],
            "notifications": [
                {"key": [("user_id", 1)]},
                {"key": [("read", 1)]},
                {"key": [("created_at", 1)]},
                {"key": [("type", 1)]},
                {"key": [("user_id", 1), ("created_at", -1)]}
            ],
            "audit_logs": [
                {"key": [("user_id", 1)]},
                {"key": [("action", 1)]},
                {"key": [("timestamp", 1)]},
                {"key": [("resource_type", 1)]},
                {"key": [("timestamp", -1)]}  # For log rotation
            ],
            "api_usage": [
                {"key": [("api_key", 1)]},
                {"key": [("endpoint", 1)]},
                {"key": [("timestamp", 1)]},
                {"key": [("user_id", 1)]},
                {"key": [("timestamp", -1)]}  # For usage analytics
            ],
            "system_migrations": [
                {"key": [("migration_id", 1)], "unique": True},
                {"key": [("applied_at", 1)]},
                {"key": [("status", 1)]}
            ]
        }
        
        for collection_name, collection_indexes in indexes.items():
            for index_spec in collection_indexes:
                try:
                    self.db[collection_name].create_index(
                        index_spec["key"],
                        unique=index_spec.get("unique", False),
                        sparse=index_spec.get("sparse", False),
                        background=True
                    )
                    logger.info(f"Created index on {collection_name}: {index_spec['key']}")
                except Exception as e:
                    logger.warning(f"Failed to create index on {collection_name}: {e}")
    
    def _create_migration_tracking(self):
        """Create migration tracking system"""
        # Ensure migration collection has proper indexes
        self.db[self.migration_collection].create_index("migration_id", unique=True)
        self.db[self.migration_collection].create_index("applied_at")
        
        logger.info("Migration tracking system initialized")
    
    def _insert_initial_data(self):
        """Insert initial system data"""
        
        # System configurations
        initial_configs = [
            {
                "key": "system.version",
                "value": "1.0.0",
                "category": "system",
                "description": "System version",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "key": "features.market_analysis",
                "value": True,
                "category": "features",
                "description": "Enable market analysis features",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "key": "limits.max_concurrent_scans",
                "value": 5,
                "category": "limits",
                "description": "Maximum concurrent market scans",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "key": "cache.default_ttl",
                "value": 3600,
                "category": "cache",
                "description": "Default cache TTL in seconds",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]
        
        for config in initial_configs:
            self.db.configurations.update_one(
                {"key": config["key"]},
                {"$set": config},
                upsert=True
            )
        
        logger.info("Initial configuration data inserted")
    
    def apply_migrations(self, dry_run: bool = False, target_version: Optional[str] = None) -> bool:
        """
        Apply pending migrations
        
        Args:
            dry_run: Show what would be done without applying
            target_version: Apply migrations up to this version
            
        Returns:
            bool: Success status
        """
        logger.info("Checking for pending migrations")
        
        try:
            # Get all available migrations
            available_migrations = self._discover_migrations()
            applied_migrations = self._get_applied_migrations()
            
            # Filter pending migrations
            pending_migrations = [
                m for m in available_migrations
                if m.id not in applied_migrations
            ]
            
            if target_version:
                pending_migrations = [
                    m for m in pending_migrations
                    if self._version_compare(m.version, target_version) <= 0
                ]
            
            if not pending_migrations:
                logger.info("No pending migrations found")
                return True
            
            logger.info(f"Found {len(pending_migrations)} pending migrations")
            
            if dry_run:
                logger.info("DRY RUN - Would apply the following migrations:")
                for migration in pending_migrations:
                    logger.info(f"  - {migration.id}: {migration.name}")
                return True
            
            # Apply migrations in order
            for migration in pending_migrations:
                success = self._apply_migration(migration)
                if not success:
                    logger.error(f"Migration failed: {migration.id}")
                    return False
            
            logger.info("All migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False
    
    def _discover_migrations(self) -> List[Migration]:
        """Discover available migration files"""
        migrations = []
        
        for migration_file in sorted(self.migrations_dir.glob("*.py")):
            if migration_file.name.startswith("__"):
                continue
            
            try:
                # Load migration metadata
                migration_id = migration_file.stem
                metadata = self._load_migration_metadata(migration_file)
                
                if metadata:
                    migrations.append(Migration(
                        id=migration_id,
                        name=metadata.get("name", migration_id),
                        description=metadata.get("description", ""),
                        type=MigrationType(metadata.get("type", "schema")),
                        version=metadata.get("version", "1.0.0"),
                        created_at=metadata.get("created_at", ""),
                        dependencies=metadata.get("dependencies", []),
                        rollback_available=metadata.get("rollback_available", False)
                    ))
                
            except Exception as e:
                logger.warning(f"Failed to load migration {migration_file}: {e}")
        
        return migrations
    
    def _load_migration_metadata(self, migration_file: Path) -> Optional[Dict]:
        """Load migration metadata from file"""
        try:
            with open(migration_file, 'r') as f:
                content = f.read()
                
                # Extract metadata from docstring or comments
                metadata = {}
                
                # Look for metadata in comments
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('# META:'):
                        meta_json = line[7:].strip()
                        metadata = json.loads(meta_json)
                        break
                
                return metadata if metadata else {
                    "name": migration_file.stem,
                    "type": "schema",
                    "version": "1.0.0"
                }
                
        except Exception as e:
            logger.error(f"Failed to load metadata from {migration_file}: {e}")
            return None
    
    def _get_applied_migrations(self) -> List[str]:
        """Get list of applied migration IDs"""
        try:
            applied = self.db[self.migration_collection].find(
                {"status": "applied"},
                {"migration_id": 1}
            )
            return [doc["migration_id"] for doc in applied]
        except:
            return []
    
    def _apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration"""
        logger.info(f"Applying migration: {migration.id} - {migration.name}")
        
        try:
            # Record migration start
            migration_doc = {
                "migration_id": migration.id,
                "name": migration.name,
                "description": migration.description,
                "type": migration.type.value,
                "version": migration.version,
                "status": "applying",
                "started_at": datetime.now(timezone.utc)
            }
            
            self.db[self.migration_collection].insert_one(migration_doc)
            
            # Execute migration
            migration_file = self.migrations_dir / f"{migration.id}.py"
            success = self._execute_migration_file(migration_file)
            
            # Update migration status
            update_doc = {
                "status": "applied" if success else "failed",
                "applied_at": datetime.now(timezone.utc)
            }
            
            if not success:
                update_doc["error"] = "Migration execution failed"
            
            self.db[self.migration_collection].update_one(
                {"migration_id": migration.id},
                {"$set": update_doc}
            )
            
            if success:
                logger.info(f"Migration applied successfully: {migration.id}")
            else:
                logger.error(f"Migration failed: {migration.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying migration {migration.id}: {e}")
            
            # Mark as failed
            self.db[self.migration_collection].update_one(
                {"migration_id": migration.id},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "applied_at": datetime.now(timezone.utc)
                }}
            )
            
            return False
    
    def _execute_migration_file(self, migration_file: Path) -> bool:
        """Execute migration Python file"""
        try:
            # Import and execute migration
            spec = importlib.util.spec_from_file_location("migration", migration_file)
            migration_module = importlib.util.module_from_spec(spec)
            
            # Provide database connections to migration
            migration_module.db = self.db
            migration_module.mongo_client = self.mongo_client
            if self.redis_client:
                migration_module.redis_client = self.redis_client
            
            spec.loader.exec_module(migration_module)
            
            # Execute migration function
            if hasattr(migration_module, 'up'):
                migration_module.up()
                return True
            else:
                logger.error(f"Migration file {migration_file} missing 'up' function")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute migration {migration_file}: {e}")
            return False
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare version strings"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad to same length
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        
        return 0
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get migration status summary"""
        try:
            total_migrations = len(list(self.migrations_dir.glob("*.py")))
            applied_count = self.db[self.migration_collection].count_documents(
                {"status": "applied"}
            )
            failed_count = self.db[self.migration_collection].count_documents(
                {"status": "failed"}
            )
            
            return {
                "database_initialized": self._is_initialized(),
                "total_migrations": total_migrations,
                "applied_migrations": applied_count,
                "failed_migrations": failed_count,
                "pending_migrations": total_migrations - applied_count,
                "last_migration": self._get_last_applied_migration()
            }
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {"error": str(e)}
    
    def _get_last_applied_migration(self) -> Optional[str]:
        """Get last applied migration ID"""
        try:
            last_migration = self.db[self.migration_collection].find_one(
                {"status": "applied"},
                sort=[("applied_at", -1)]
            )
            return last_migration["migration_id"] if last_migration else None
        except:
            return None
    
    def create_migration_template(self, migration_id: str, migration_type: str = "schema") -> bool:
        """Create a new migration template file"""
        try:
            migration_file = self.migrations_dir / f"{migration_id}.py"
            
            if migration_file.exists():
                logger.error(f"Migration file already exists: {migration_file}")
                return False
            
            template = f'''#!/usr/bin/env python3
"""
Migration: {migration_id}
Type: {migration_type}
Description: TODO - Add migration description
"""

# META: {{"name": "{migration_id}", "type": "{migration_type}", "version": "1.0.0", "created_at": "{datetime.now(timezone.utc).isoformat()}", "dependencies": []}}

def up():
    """Apply migration"""
    # TODO: Implement migration logic
    # Available variables:
    # - db: MongoDB database connection
    # - mongo_client: MongoDB client
    # - redis_client: Redis client (if available)
    
    pass


def down():
    """Rollback migration (optional)"""
    # TODO: Implement rollback logic if needed
    pass


if __name__ == "__main__":
    print("Migration: {migration_id}")
    print("This migration should be run via the migration manager")
'''
            
            with open(migration_file, 'w') as f:
                f.write(template)
            
            logger.info(f"Created migration template: {migration_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create migration template: {e}")
            return False


def main():
    """CLI interface for database migration"""
    parser = argparse.ArgumentParser(description="TradingAgents-CN Database Migration Manager")
    parser.add_argument("--mongodb-url", 
                       default=os.getenv("TRADINGAGENTS_MONGODB_URL", "mongodb://localhost:27017/tradingagents"),
                       help="MongoDB connection URL")
    parser.add_argument("--redis-url", 
                       default=os.getenv("TRADINGAGENTS_REDIS_URL"),
                       help="Redis connection URL")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Initialize command
    init_parser = subparsers.add_parser("init", help="Initialize database")
    init_parser.add_argument("--force", action="store_true", help="Force initialization")
    
    # Apply migrations command
    apply_parser = subparsers.add_parser("apply", help="Apply migrations")
    apply_parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    apply_parser.add_argument("--target-version", help="Target version to migrate to")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show migration status")
    
    # Create migration command
    create_parser = subparsers.add_parser("create", help="Create new migration")
    create_parser.add_argument("migration_id", help="Migration ID")
    create_parser.add_argument("--type", choices=["schema", "data", "index", "cleanup"], 
                              default="schema", help="Migration type")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Initialize migration manager
        migration_manager = DatabaseMigrationManager(args.mongodb_url, args.redis_url)
        
        if args.command == "init":
            migration_manager.initialize_database(force=args.force)
        
        elif args.command == "apply":
            success = migration_manager.apply_migrations(
                dry_run=args.dry_run,
                target_version=args.target_version
            )
            if not success:
                sys.exit(1)
        
        elif args.command == "status":
            status = migration_manager.get_migration_status()
            print("Database Migration Status:")
            print(f"  Database Initialized: {status.get('database_initialized', 'Unknown')}")
            print(f"  Total Migrations: {status.get('total_migrations', 0)}")
            print(f"  Applied Migrations: {status.get('applied_migrations', 0)}")
            print(f"  Failed Migrations: {status.get('failed_migrations', 0)}")
            print(f"  Pending Migrations: {status.get('pending_migrations', 0)}")
            print(f"  Last Applied: {status.get('last_migration', 'None')}")
        
        elif args.command == "create":
            success = migration_manager.create_migration_template(args.migration_id, args.type)
            if not success:
                sys.exit(1)
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import importlib.util
    main()