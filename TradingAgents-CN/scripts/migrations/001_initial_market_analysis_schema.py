#!/usr/bin/env python3
"""
Migration: 001_initial_market_analysis_schema
Type: schema
Description: Create initial schema for market analysis features
"""

# META: {"name": "001_initial_market_analysis_schema", "type": "schema", "version": "1.0.0", "created_at": "2025-08-08T00:00:00Z", "dependencies": []}

def up():
    """Apply migration - Create market analysis schema"""
    
    # Create market_scans collection with proper structure
    if "market_scans" not in db.list_collection_names():
        db.create_collection("market_scans")
    
    # Add sample document structure for reference
    sample_market_scan = {
        "_schema_version": "1.0.0",
        "scan_id": "sample_scan_structure",
        "user_id": None,
        "config": {
            "market_type": "A股",
            "preset_type": "大盘蓝筹",
            "scan_depth": 3,
            "budget_limit": 10.0,
            "stock_limit": 100,
            "time_range": "1月",
            "custom_filters": {},
            "analysis_focus": {},
            "ai_model_config": {}
        },
        "status": "pending",  # pending, running, paused, completed, failed, cancelled
        "progress": {
            "overall_progress": 0,
            "current_stage": "初始化",
            "stages": [
                {"name": "数据准备", "completed": False, "current": False},
                {"name": "股票筛选", "completed": False, "current": False},
                {"name": "技术分析", "completed": False, "current": False},
                {"name": "基本面分析", "completed": False, "current": False},
                {"name": "生成报告", "completed": False, "current": False}
            ],
            "stats": {
                "processed_stocks": 0,
                "total_stocks": 0,
                "cost_used": 0.0,
                "scan_duration": None,
                "actual_cost": None,
                "recommended_stocks": 0
            },
            "latest_message": "",
            "preview_results": None,
            "error_message": None,
            "estimated_completion": None
        },
        "results": {
            "rankings": [],
            "sectors": {},
            "breadth": {},
            "summary": {}
        },
        "created_at": None,
        "started_at": None,
        "completed_at": None,
        "updated_at": None
    }
    
    # Insert schema reference (will be removed later)
    db.market_scans.insert_one(sample_market_scan)
    
    # Create proper indexes for market_scans
    db.market_scans.create_index("scan_id", unique=True)
    db.market_scans.create_index("user_id")
    db.market_scans.create_index("status")
    db.market_scans.create_index("created_at")
    db.market_scans.create_index([("user_id", 1), ("created_at", -1)])
    db.market_scans.create_index([("status", 1), ("created_at", -1)])
    
    # Create analysis_results collection enhancements for market analysis
    if "analysis_results" in db.list_collection_names():
        # Add indexes for market analysis queries
        db.analysis_results.create_index([("symbol", 1), ("analysis_type", 1), ("created_at", -1)])
        db.analysis_results.create_index("market_scan_id")  # Link to market scans
        db.analysis_results.create_index([("recommendations.action", 1), ("created_at", -1)])
        db.analysis_results.create_index("sector")
        db.analysis_results.create_index("market_cap_category")
    
    # Create market_sessions collection for session management
    if "market_sessions" not in db.list_collection_names():
        db.create_collection("market_sessions")
    
    # Market sessions schema
    sample_market_session = {
        "_schema_version": "1.0.0",
        "session_id": "sample_session_structure",
        "scan_id": None,  # Reference to market_scans
        "user_id": None,
        "session_data": {},
        "progress_data": {},
        "results_cache": {},
        "export_history": [],
        "created_at": None,
        "updated_at": None,
        "expires_at": None
    }
    
    db.market_sessions.insert_one(sample_market_session)
    
    # Create indexes for market_sessions
    db.market_sessions.create_index("session_id", unique=True)
    db.market_sessions.create_index("scan_id")
    db.market_sessions.create_index("user_id")
    db.market_sessions.create_index("expires_at")
    db.market_sessions.create_index([("user_id", 1), ("created_at", -1)])
    
    # Create market_exports collection for export tracking
    if "market_exports" not in db.list_collection_names():
        db.create_collection("market_exports")
    
    sample_market_export = {
        "_schema_version": "1.0.0",
        "export_id": "sample_export_structure",
        "scan_id": None,
        "user_id": None,
        "export_format": "excel",  # excel, pdf, html, csv
        "export_options": {},
        "file_path": None,
        "file_size": 0,
        "status": "pending",  # pending, processing, completed, failed
        "created_at": None,
        "completed_at": None,
        "expires_at": None,
        "download_count": 0,
        "last_downloaded": None
    }
    
    db.market_exports.insert_one(sample_market_export)
    
    # Create indexes for market_exports
    db.market_exports.create_index("export_id", unique=True)
    db.market_exports.create_index("scan_id")
    db.market_exports.create_index("user_id")
    db.market_exports.create_index("status")
    db.market_exports.create_index("expires_at")  # For cleanup
    db.market_exports.create_index([("user_id", 1), ("created_at", -1)])
    
    # Add market analysis configurations
    market_configs = [
        {
            "key": "market_analysis.max_concurrent_scans",
            "value": 5,
            "category": "market_analysis",
            "description": "Maximum concurrent market scans per user",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "key": "market_analysis.default_scan_depth",
            "value": 3,
            "category": "market_analysis",
            "description": "Default market scan depth",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "key": "market_analysis.session_timeout_hours",
            "value": 24,
            "category": "market_analysis",
            "description": "Market session timeout in hours",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "key": "market_analysis.export_retention_days",
            "value": 7,
            "category": "market_analysis",
            "description": "Export file retention period in days",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "key": "market_analysis.max_export_file_size_mb",
            "value": 100,
            "category": "market_analysis",
            "description": "Maximum export file size in MB",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ]
    
    for config in market_configs:
        db.configurations.update_one(
            {"key": config["key"]},
            {"$set": config},
            upsert=True
        )
    
    print("✅ Market analysis schema created successfully")
    print("   - market_scans collection with indexes")
    print("   - market_sessions collection with indexes") 
    print("   - market_exports collection with indexes")
    print("   - Enhanced analysis_results indexes")
    print("   - Market analysis configuration settings")


def down():
    """Rollback migration - Remove market analysis schema"""
    
    # Remove sample structure documents
    db.market_scans.delete_one({"scan_id": "sample_scan_structure"})
    db.market_sessions.delete_one({"session_id": "sample_session_structure"})
    db.market_exports.delete_one({"export_id": "sample_export_structure"})
    
    # Remove market analysis configurations
    db.configurations.delete_many({"category": "market_analysis"})
    
    # Note: We don't drop collections or indexes in rollback to preserve any real data
    # In a real rollback scenario, you might want to be more careful about what to remove
    
    print("✅ Market analysis schema rollback completed")
    print("   - Sample documents removed")
    print("   - Configuration settings removed")
    print("   - Collections and indexes preserved for safety")


if __name__ == "__main__":
    from datetime import datetime
    print("Migration: 001_initial_market_analysis_schema")
    print("This migration should be run via the migration manager")