"""
Database Migration: ChartingArtist Configuration and Chart Management
Version: 002_charting_artist_schema
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING, TEXT, MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

class ChartingArtistMigration:
    """数据库迁移：ChartingArtist配置和图表管理"""
    
    def __init__(self, mongodb_url: str):
        """初始化迁移"""
        self.mongodb_url = mongodb_url
        self.client = None
        self.db = None
        self.migration_version = "002_charting_artist_schema"
        self.migration_date = datetime.now()
    
    def connect(self):
        """连接数据库"""
        try:
            self.client = MongoClient(self.mongodb_url)
            self.db = self.client.get_default_database()
            logger.info(f"Connected to MongoDB: {self.db.name}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def disconnect(self):
        """断开数据库连接"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def check_migration_status(self) -> bool:
        """检查迁移状态"""
        try:
            migrations_collection = self.db.migrations
            existing_migration = migrations_collection.find_one({
                "version": self.migration_version
            })
            return existing_migration is not None
        except Exception as e:
            logger.error(f"检查迁移状态失败: {e}")
            return False
    
    def run_migration(self):
        """执行迁移"""
        try:
            if self.check_migration_status():
                logger.info(f"Migration {self.migration_version} already applied")
                return True
            
            logger.info(f"Starting migration: {self.migration_version}")
            
            # 1. 创建ChartingArtist配置集合
            self._create_charting_artist_config()
            
            # 2. 创建图表元数据集合
            self._create_chart_metadata_collection()
            
            # 3. 创建图表任务队列集合
            self._create_chart_task_collection()
            
            # 4. 创建图表统计集合
            self._create_chart_statistics_collection()
            
            # 5. 更新agent_roles配置
            self._update_agent_roles_config()
            
            # 6. 创建索引
            self._create_indexes()
            
            # 7. 插入初始数据
            self._insert_initial_data()
            
            # 8. 记录迁移
            self._record_migration()
            
            logger.info(f"Migration {self.migration_version} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # 回滚操作
            self._rollback_migration()
            raise
    
    def _create_charting_artist_config(self):
        """创建ChartingArtist配置集合"""
        config_collection = self.db.charting_artist_config
        
        # 删除已存在的集合（如果有）
        config_collection.drop()
        
        # 创建配置文档
        config_doc = {
            "_id": "charting_artist_config",
            "enabled": True,
            "version": "1.0.0",
            "created_at": self.migration_date,
            "updated_at": self.migration_date,
            
            # 基础配置
            "basic_config": {
                "default_theme": "plotly_dark",
                "default_width": 800,
                "default_height": 600,
                "interactive": True,
                "export_format": "html"
            },
            
            # 支持的图表类型
            "chart_types": {
                "candlestick": {
                    "name": "K线图",
                    "description": "显示股票价格的开高低收数据",
                    "complexity": 3,
                    "avg_generation_time": 2.5
                },
                "line_chart": {
                    "name": "折线图",
                    "description": "显示数据趋势变化",
                    "complexity": 1,
                    "avg_generation_time": 1.0
                },
                "bar_chart": {
                    "name": "柱状图",
                    "description": "显示分类数据对比",
                    "complexity": 1,
                    "avg_generation_time": 1.2
                },
                "pie_chart": {
                    "name": "饼图",
                    "description": "显示占比分布",
                    "complexity": 1,
                    "avg_generation_time": 1.0
                },
                "heatmap": {
                    "name": "热力图",
                    "description": "显示相关性或分布数据",
                    "complexity": 2,
                    "avg_generation_time": 2.0
                },
                "radar_chart": {
                    "name": "雷达图",
                    "description": "多维度数据展示",
                    "complexity": 2,
                    "avg_generation_time": 1.8
                },
                "gauge_chart": {
                    "name": "仪表盘",
                    "description": "显示单一指标的等级",
                    "complexity": 2,
                    "avg_generation_time": 1.5
                },
                "waterfall": {
                    "name": "瀑布图",
                    "description": "显示数据累积变化",
                    "complexity": 2,
                    "avg_generation_time": 2.2
                },
                "scatter_plot": {
                    "name": "散点图",
                    "description": "显示两变量关系",
                    "complexity": 2,
                    "avg_generation_time": 1.6
                },
                "box_plot": {
                    "name": "箱线图",
                    "description": "显示数据分布统计",
                    "complexity": 2,
                    "avg_generation_time": 1.9
                }
            },
            
            # 性能配置
            "performance": {
                "max_concurrent_jobs": 3,
                "default_timeout": 60,
                "cache_enabled": True,
                "cache_size": 100,
                "cache_ttl": 3600
            },
            
            # 存储配置
            "storage": {
                "retention_days": 30,
                "max_file_size_mb": 50,
                "cleanup_enabled": True,
                "backup_enabled": False
            },
            
            # API配置
            "api": {
                "rate_limit": 100,
                "max_payload_size": "10MB",
                "cors_enabled": False
            }
        }
        
        config_collection.insert_one(config_doc)
        logger.info("Created charting_artist_config collection")
    
    def _create_chart_metadata_collection(self):
        """创建图表元数据集合"""
        charts_collection = self.db.chart_metadata
        
        # 删除已存在的集合
        charts_collection.drop()
        
        # 创建集合验证模式
        validation_schema = {
            "bsonType": "object",
            "required": ["chart_id", "chart_type", "analysis_id", "symbol", "created_at", "status"],
            "properties": {
                "chart_id": {
                    "bsonType": "string",
                    "description": "图表唯一标识符"
                },
                "chart_type": {
                    "bsonType": "string",
                    "enum": ["candlestick", "line_chart", "bar_chart", "pie_chart", 
                            "heatmap", "radar_chart", "gauge_chart", "waterfall", 
                            "scatter_plot", "box_plot"],
                    "description": "图表类型"
                },
                "analysis_id": {
                    "bsonType": "string",
                    "description": "关联的分析会话ID"
                },
                "symbol": {
                    "bsonType": "string",
                    "description": "股票代码或资产标识"
                },
                "title": {
                    "bsonType": "string",
                    "description": "图表标题"
                },
                "description": {
                    "bsonType": "string",
                    "description": "图表描述"
                },
                "file_path": {
                    "bsonType": "string",
                    "description": "图表文件路径"
                },
                "file_size": {
                    "bsonType": ["int", "long"],
                    "minimum": 0,
                    "description": "文件大小（字节）"
                },
                "export_format": {
                    "bsonType": "string",
                    "enum": ["html", "json", "png", "svg"],
                    "description": "导出格式"
                },
                "config": {
                    "bsonType": "object",
                    "description": "图表生成配置"
                },
                "metadata": {
                    "bsonType": "object",
                    "description": "额外元数据"
                },
                "status": {
                    "bsonType": "string",
                    "enum": ["generating", "completed", "failed", "deleted"],
                    "description": "图表状态"
                },
                "generation_time_ms": {
                    "bsonType": ["int", "long"],
                    "minimum": 0,
                    "description": "生成耗时（毫秒）"
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "创建时间"
                },
                "updated_at": {
                    "bsonType": "date",
                    "description": "更新时间"
                },
                "expires_at": {
                    "bsonType": "date",
                    "description": "过期时间"
                }
            }
        }
        
        # 创建集合
        self.db.create_collection("chart_metadata", validator={"$jsonSchema": validation_schema})
        logger.info("Created chart_metadata collection with validation")
    
    def _create_chart_task_collection(self):
        """创建图表任务队列集合"""
        tasks_collection = self.db.chart_tasks
        
        # 删除已存在的集合
        tasks_collection.drop()
        
        # 创建任务队列验证模式
        validation_schema = {
            "bsonType": "object",
            "required": ["task_id", "task_type", "status", "created_at"],
            "properties": {
                "task_id": {
                    "bsonType": "string",
                    "description": "任务唯一标识符"
                },
                "task_type": {
                    "bsonType": "string",
                    "enum": ["generate", "batch_generate", "cleanup", "export"],
                    "description": "任务类型"
                },
                "priority": {
                    "bsonType": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "任务优先级"
                },
                "status": {
                    "bsonType": "string",
                    "enum": ["queued", "processing", "completed", "failed", "cancelled"],
                    "description": "任务状态"
                },
                "progress": {
                    "bsonType": ["int", "double"],
                    "minimum": 0,
                    "maximum": 100,
                    "description": "任务进度百分比"
                },
                "request_data": {
                    "bsonType": "object",
                    "description": "任务请求数据"
                },
                "result_data": {
                    "bsonType": "object",
                    "description": "任务结果数据"
                },
                "error_message": {
                    "bsonType": "string",
                    "description": "错误信息"
                },
                "worker_id": {
                    "bsonType": "string",
                    "description": "处理任务的工作者ID"
                },
                "estimated_duration": {
                    "bsonType": ["int", "long"],
                    "minimum": 0,
                    "description": "预估执行时间（秒）"
                },
                "actual_duration": {
                    "bsonType": ["int", "long"],
                    "minimum": 0,
                    "description": "实际执行时间（秒）"
                },
                "retry_count": {
                    "bsonType": "int",
                    "minimum": 0,
                    "maximum": 3,
                    "description": "重试次数"
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "创建时间"
                },
                "started_at": {
                    "bsonType": "date",
                    "description": "开始执行时间"
                },
                "completed_at": {
                    "bsonType": "date",
                    "description": "完成时间"
                },
                "expires_at": {
                    "bsonType": "date",
                    "description": "过期时间"
                }
            }
        }
        
        # 创建集合
        self.db.create_collection("chart_tasks", validator={"$jsonSchema": validation_schema})
        logger.info("Created chart_tasks collection with validation")
    
    def _create_chart_statistics_collection(self):
        """创建图表统计集合"""
        stats_collection = self.db.chart_statistics
        
        # 删除已存在的集合
        stats_collection.drop()
        
        # 插入初始统计数据
        initial_stats = {
            "_id": "chart_stats",
            "created_at": self.migration_date,
            "updated_at": self.migration_date,
            
            # 总体统计
            "overview": {
                "total_charts_generated": 0,
                "total_generation_time_ms": 0,
                "average_generation_time_ms": 0,
                "success_rate": 100.0,
                "total_file_size_bytes": 0
            },
            
            # 按图表类型统计
            "by_chart_type": {},
            
            # 按时间统计（每日）
            "daily_stats": [],
            
            # 性能指标
            "performance": {
                "fastest_generation_ms": None,
                "slowest_generation_ms": None,
                "most_popular_chart_type": None,
                "peak_generation_hour": None
            },
            
            # 错误统计
            "errors": {
                "total_errors": 0,
                "error_rate": 0.0,
                "common_errors": []
            }
        }
        
        stats_collection.insert_one(initial_stats)
        logger.info("Created chart_statistics collection with initial data")
    
    def _update_agent_roles_config(self):
        """更新agent_roles配置"""
        try:
            agent_roles_collection = self.db.agent_roles
            
            # 确保charting_artist角色存在且正确配置
            charting_artist_config = {
                "_id": "charting_artist",
                "name": "绘图师",
                "name_en": "Charting Artist",
                "description": "基于分析结果生成专业的可视化图表和技术图形",
                "role_type": "visualization",
                "priority": "clarity",
                "is_optional": True,
                "enabled_by_default": False,
                "updated_at": self.migration_date,
                
                # 专业领域
                "expertise": [
                    "K线图绘制",
                    "技术指标可视化",
                    "财务数据图表",
                    "趋势分析图表",
                    "风险热力图",
                    "投资组合饼图",
                    "时间序列图表",
                    "相关性矩阵图"
                ],
                
                # 图表类型
                "chart_types": [
                    "candlestick", "line_chart", "bar_chart", "pie_chart",
                    "scatter_plot", "heatmap", "radar_chart", "box_plot",
                    "waterfall", "gauge_chart"
                ],
                
                # 技术依赖
                "dependencies": [
                    "plotly", "pandas", "numpy", "matplotlib", "seaborn"
                ],
                
                # 输出特点
                "output_style": {
                    "format": "interactive_charts",
                    "length": "visual",
                    "focus": "data_storytelling",
                    "time_sensitivity": "low",
                    "interactive": True
                },
                
                # 性能要求
                "performance": {
                    "response_time": "fast",  # 5-15秒
                    "accuracy": "high",       # 85-95%
                    "cost_limit": 0.05,
                    "post_processing": True   # 标识为后处理角色
                }
            }
            
            # 使用upsert更新或插入配置
            agent_roles_collection.replace_one(
                {"_id": "charting_artist"},
                charting_artist_config,
                upsert=True
            )
            
            logger.info("Updated agent_roles configuration for charting_artist")
            
        except Exception as e:
            logger.error(f"Failed to update agent_roles config: {e}")
            raise
    
    def _create_indexes(self):
        """创建索引"""
        try:
            # chart_metadata索引
            charts_collection = self.db.chart_metadata
            charts_collection.create_index([("chart_id", ASCENDING)], unique=True)
            charts_collection.create_index([("analysis_id", ASCENDING)])
            charts_collection.create_index([("symbol", ASCENDING)])
            charts_collection.create_index([("chart_type", ASCENDING)])
            charts_collection.create_index([("status", ASCENDING)])
            charts_collection.create_index([("created_at", DESCENDING)])
            charts_collection.create_index([("expires_at", ASCENDING)])
            
            # 复合索引
            charts_collection.create_index([
                ("symbol", ASCENDING),
                ("chart_type", ASCENDING),
                ("created_at", DESCENDING)
            ])
            
            # 文本搜索索引
            charts_collection.create_index([
                ("title", TEXT),
                ("description", TEXT)
            ])
            
            # chart_tasks索引
            tasks_collection = self.db.chart_tasks
            tasks_collection.create_index([("task_id", ASCENDING)], unique=True)
            tasks_collection.create_index([("status", ASCENDING)])
            tasks_collection.create_index([("priority", ASCENDING)])
            tasks_collection.create_index([("task_type", ASCENDING)])
            tasks_collection.create_index([("created_at", DESCENDING)])
            tasks_collection.create_index([("expires_at", ASCENDING)])
            
            # 任务队列复合索引
            tasks_collection.create_index([
                ("status", ASCENDING),
                ("priority", DESCENDING),
                ("created_at", ASCENDING)
            ])
            
            logger.info("Created indexes for ChartingArtist collections")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
    
    def _insert_initial_data(self):
        """插入初始数据"""
        try:
            # 插入示例图表类型配置
            chart_types_collection = self.db.chart_type_configs
            chart_types_collection.drop()
            
            chart_type_configs = [
                {
                    "chart_type": "candlestick",
                    "display_name": "K线图",
                    "category": "technical",
                    "default_config": {
                        "theme": "plotly_dark",
                        "indicators": ["volume", "ma"],
                        "time_range": "1y"
                    },
                    "requirements": {
                        "data_fields": ["open", "high", "low", "close", "volume"],
                        "min_data_points": 20
                    },
                    "templates": {
                        "basic": {"ma_periods": [5, 20]},
                        "advanced": {"ma_periods": [5, 10, 20, 60], "bollinger": True}
                    }
                },
                {
                    "chart_type": "financial_dashboard",
                    "display_name": "财务仪表板",
                    "category": "fundamental",
                    "default_config": {
                        "theme": "plotly_white",
                        "sections": ["profitability", "solvency", "efficiency", "growth"]
                    },
                    "requirements": {
                        "data_fields": ["revenue", "profit", "assets", "liabilities"],
                        "min_periods": 4
                    }
                }
            ]
            
            chart_types_collection.insert_many(chart_type_configs)
            logger.info("Inserted initial chart type configurations")
            
        except Exception as e:
            logger.error(f"Failed to insert initial data: {e}")
            raise
    
    def _record_migration(self):
        """记录迁移"""
        try:
            migrations_collection = self.db.migrations
            migration_record = {
                "version": self.migration_version,
                "description": "ChartingArtist configuration and chart management schema",
                "executed_at": self.migration_date,
                "status": "completed",
                "collections_created": [
                    "charting_artist_config",
                    "chart_metadata", 
                    "chart_tasks",
                    "chart_statistics",
                    "chart_type_configs"
                ],
                "indexes_created": 15,
                "data_inserted": True
            }
            
            migrations_collection.insert_one(migration_record)
            logger.info(f"Recorded migration: {self.migration_version}")
            
        except Exception as e:
            logger.error(f"Failed to record migration: {e}")
            raise
    
    def _rollback_migration(self):
        """回滚迁移"""
        try:
            logger.warning("Rolling back ChartingArtist migration...")
            
            # 删除创建的集合
            collections_to_drop = [
                "charting_artist_config",
                "chart_metadata",
                "chart_tasks", 
                "chart_statistics",
                "chart_type_configs"
            ]
            
            for collection_name in collections_to_drop:
                try:
                    self.db[collection_name].drop()
                    logger.info(f"Dropped collection: {collection_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop collection {collection_name}: {e}")
            
            # 恢复agent_roles配置
            try:
                self.db.agent_roles.delete_one({"_id": "charting_artist"})
                logger.info("Removed charting_artist from agent_roles")
            except Exception as e:
                logger.warning(f"Failed to remove charting_artist config: {e}")
            
            logger.info("Migration rollback completed")
            
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")

def run_migration(mongodb_url: str):
    """运行ChartingArtist数据库迁移"""
    migration = ChartingArtistMigration(mongodb_url)
    
    try:
        migration.connect()
        success = migration.run_migration()
        return success
    except Exception as e:
        logger.error(f"Migration execution failed: {e}")
        return False
    finally:
        migration.disconnect()

def check_migration_required(mongodb_url: str) -> bool:
    """检查是否需要运行迁移"""
    migration = ChartingArtistMigration(mongodb_url)
    
    try:
        migration.connect()
        return not migration.check_migration_status()
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        return False
    finally:
        migration.disconnect()

if __name__ == "__main__":
    import os

    # 从环境变量获取MongoDB URL
    mongodb_url = os.getenv(
        "TRADINGAGENTS_MONGODB_URL", 
        "mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin"
    )
    
    print("🔄 Checking ChartingArtist migration status...")
    
    if check_migration_required(mongodb_url):
        print("📊 Running ChartingArtist database migration...")
        success = run_migration(mongodb_url)
        
        if success:
            print("✅ ChartingArtist migration completed successfully!")
        else:
            print("❌ ChartingArtist migration failed!")
            exit(1)
    else:
        print("✅ ChartingArtist migration already applied!")