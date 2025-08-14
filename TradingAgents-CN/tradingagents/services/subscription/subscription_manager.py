#!/usr/bin/env python3
"""
订阅管理器
管理股票分析报告的邮件订阅
"""

from datetime import datetime
from typing import List, Dict, Optional
import re

from tradingagents.config.mongodb_storage import MongoDBStorage
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('subscription')


class SubscriptionManager:
    """订阅管理器

    支持三类订阅：
    - stock: 个股订阅（默认）
    - market: 市场级订阅（A股/美股/港股/全球 摘要）
    - index: 指数订阅（如 沪深300/中证500/上证50 等）
    """
    
    def __init__(self):
        """初始化订阅管理器"""
        try:
            self.storage = MongoDBStorage()
            self.collection = 'stock_subscriptions'
            self._init_indexes()
            logger.info("✅ 订阅管理器初始化成功（MongoDB模式）")
        except Exception as e:
            logger.warning(f"⚠️ MongoDB不可用，使用内存存储: {e}")
            self.storage = None
            self._memory_storage = []
            
    def _init_indexes(self):
        """初始化数据库索引"""
        if self.storage:
            try:
                # 创建复合索引，提高查询性能
                self.storage.db[self.collection].create_index([
                    ('email', 1),
                    ('symbol', 1),
                    ('status', 1)
                ])
                self.storage.db[self.collection].create_index([
                    ('market_type', 1),
                    ('frequency', 1)
                ])
                # 新增：类型与范围相关索引
                self.storage.db[self.collection].create_index([
                    ('subscription_type', 1),
                    ('market_scope', 1),
                ])
                # 指数订阅相关索引（按邮箱+类型+代码）
                self.storage.db[self.collection].create_index([
                    ('subscription_type', 1),
                    ('email', 1),
                    ('symbol', 1),
                ], name='idx_sub_type_email_symbol')
            except Exception as e:
                logger.debug(f"索引可能已存在: {e}")
                
    def add_subscription(self, 
                        email: str,
                        symbol: str,
                        market_type: str,
                        frequency: str = 'close',
                        custom_time: str = None,
                        notification_types: List[str] = None,
                        attachment_config: Optional[Dict] = None,
                        subscription_type: str = 'stock',
                        market_scope: Optional[str] = None,
                        preset_type: Optional[str] = None,
                        *,
                        index_slug: Optional[str] = None,
                        index_name: Optional[str] = None) -> str:
        """添加订阅
        
        Args:
            email: 订阅者邮箱
            symbol: 股票代码
            market_type: 市场类型（A股/港股/美股）
            frequency: 订阅频率（close/daily/weekly/custom）
            custom_time: 自定义时间（仅frequency='custom'时使用）
            notification_types: 通知类型列表（email/sms/wechat）
            attachment_config: 附件配置字典
            
        Returns:
            subscription_id: 订阅ID
        """
        # 验证邮箱格式
        if not self._validate_email(email):
            raise ValueError(f"无效的邮箱地址: {email}")

        # 订阅类型校验
        subscription_type = (subscription_type or 'stock').lower()
        if subscription_type not in ('stock', 'market', 'index'):
            raise ValueError(f"无效的订阅类型: {subscription_type}")

        # 针对不同订阅类型的校验
        if subscription_type == 'stock':
            # 验证股票代码
            if not self._validate_symbol(symbol, market_type):
                raise ValueError(f"无效的股票代码: {symbol}")
        elif subscription_type == 'market':
            # 市场级订阅无需个股代码
            symbol = (symbol or '').strip() or '*'
            valid_scopes = ['A股', '美股', '港股', '全球']
            if not market_scope or market_scope not in valid_scopes:
                raise ValueError(f"无效的市场范围: {market_scope}，应为 {valid_scopes}")
        else:
            # 指数订阅：验证指数代码
            if not self._validate_index_code(symbol):
                raise ValueError(f"无效的指数代码: {symbol}")
            # 自动推断市场类型
            if not market_type:
                market_type = self._infer_market_from_index(symbol)

        # 验证频率
        valid_frequencies = ['close', 'daily', 'weekly', 'hourly', 'custom']
        if frequency not in valid_frequencies:
            raise ValueError(f"无效的订阅频率: {frequency}")
            
        # 构建订阅数据
        subscription = {
            'email': email.lower(),
            'symbol': symbol.upper(),
            'market_type': market_type,
            'frequency': frequency,
            'custom_time': custom_time,
            'notification_types': notification_types or ['email'],
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'status': 'active',
            'last_sent': None,
            'send_count': 0,
            'subscription_type': subscription_type,
            'market_scope': market_scope if subscription_type == 'market' else None,
            'preset_type': preset_type if subscription_type == 'market' else None,
            # 指数订阅扩展信息
            'index_slug': index_slug if subscription_type == 'index' else None,
            'index_name': index_name if subscription_type == 'index' else None,
            'preferences': {
                'include_charts': True,
                'include_news': True,
                'language': 'zh-CN'
            },
            'attachment_config': attachment_config or {
                'pdf_report': True,
                'word_report': False,
                'markdown_report': False,
                'charts': True,
                'data_excel': False,
                'summary_image': False,
                'template': '标准模板',
                'naming': '股票代码_日期'
            }
        }
        
        # 检查是否已存在
        if subscription_type == 'market':
            existing = self._find_market_subscription(email, market_scope or '')
        elif subscription_type == 'index':
            existing = self._find_index_subscription(email, symbol)
        else:
            existing = self._find_subscription(email, symbol)
        if existing and existing.get('status') == 'active':
            logger.info(f"订阅已存在: {email} - {symbol}")
            return str(existing.get('_id', existing.get('id', 'memory')))
            
        # 保存订阅
        if self.storage:
            result = self.storage.insert(self.collection, subscription)
            subscription_id = str(result)
        else:
            subscription['id'] = f"sub_{len(self._memory_storage)}"
            self._memory_storage.append(subscription)
            subscription_id = subscription['id']
            
        logger.info(f"✅ 新增订阅: {email} - {symbol} ({market_type})")
        return subscription_id
        
    def remove_subscription(self, email: str, symbol: str = None) -> int:
        """移除订阅
        
        Args:
            email: 订阅者邮箱
            symbol: 股票代码（可选，不提供则移除该邮箱所有订阅）
            
        Returns:
            removed_count: 移除的订阅数量
        """
        query = {'email': email.lower(), 'status': 'active'}
        if symbol:
            query['symbol'] = symbol.upper()
            
        if self.storage:
            # 软删除，将状态改为inactive
            result = self.storage.update_many(
                self.collection,
                query,
                {'$set': {
                    'status': 'inactive',
                    'updated_at': datetime.now()
                }}
            )
            count = result.modified_count
        else:
            # 内存存储模式
            count = 0
            for sub in self._memory_storage:
                if (sub.get('email') == email.lower() and 
                    sub.get('status') == 'active'):
                    if not symbol or sub.get('symbol') == symbol.upper():
                        sub['status'] = 'inactive'
                        count += 1
                        
        logger.info(f"✅ 移除订阅: {email} - {symbol or '所有'} ({count}个)")
        return count
        
    def get_subscriptions_by_market(self, exchanges: List[str]) -> List[Dict]:
        """获取特定交易所的订阅列表
        
        Args:
            exchanges: 交易所列表，如 ['SH', 'SZ']
            
        Returns:
            subscriptions: 订阅列表
        """
        # 交易所到市场类型的映射
        market_map = {
            'SH': 'A股', 'SZ': 'A股',
            'HK': '港股',
            'NYSE': '美股', 'NASDAQ': '美股'
        }
        
        market_types = list(set(market_map.get(ex) for ex in exchanges if ex in market_map))
        
        if not market_types:
            return []
            
        # 仅返回个股订阅（避免市场级订阅混入）
        query = {
            'market_type': {'$in': market_types},
            'frequency': 'close',
            'status': 'active',
            'subscription_type': {'$in': ['stock', None]}
        }
        
        if self.storage:
            subscriptions = list(self.storage.find(self.collection, query))
        else:
            # 内存存储模式
            subscriptions = [
                sub for sub in self._memory_storage
                if (sub.get('market_type') in market_types and
                    sub.get('frequency') == 'close' and
                    sub.get('status') == 'active' and
                    (sub.get('subscription_type') in (None, 'stock')))
            ]
            
        return subscriptions
        
    def get_user_subscriptions(self, email: str) -> List[Dict]:
        """获取用户的所有订阅
        
        Args:
            email: 用户邮箱
            
        Returns:
            subscriptions: 订阅列表
        """
        query = {'email': email.lower(), 'status': 'active'}
        
        if self.storage:
            subscriptions = list(self.storage.find(self.collection, query))
        else:
            subscriptions = [
                sub for sub in self._memory_storage
                if (sub.get('email') == email.lower() and
                    sub.get('status') == 'active')
            ]
            
        return subscriptions
        
    def update_subscription(self, 
                          email: str,
                          symbol: str,
                          updates: Dict) -> bool:
        """更新订阅设置
        
        Args:
            email: 订阅者邮箱
            symbol: 股票代码
            updates: 更新内容
            
        Returns:
            success: 是否更新成功
        """
        # 添加更新时间
        updates['updated_at'] = datetime.now()
        
        query = {
            'email': email.lower(),
            'symbol': symbol.upper(),
            'status': 'active'
        }
        
        if self.storage:
            result = self.storage.update_one(
                self.collection,
                query,
                {'$set': updates}
            )
            return result.modified_count > 0
        else:
            # 内存存储模式
            for sub in self._memory_storage:
                if (sub.get('email') == email.lower() and
                    sub.get('symbol') == symbol.upper() and
                    sub.get('status') == 'active'):
                    sub.update(updates)
                    return True
            return False
            
    def mark_as_sent(self, subscription_id: str):
        """标记订阅已发送
        
        Args:
            subscription_id: 订阅ID
        """
        updates = {
            'last_sent': datetime.now(),
            '$inc': {'send_count': 1}
        }
        
        if self.storage:
            self.storage.update_one(
                self.collection,
                {'_id': subscription_id},
                updates
            )
        else:
            # 内存存储模式
            for sub in self._memory_storage:
                if sub.get('id') == subscription_id:
                    sub['last_sent'] = datetime.now()
                    sub['send_count'] = sub.get('send_count', 0) + 1
                    break
                    
    def get_subscription_stats(self) -> Dict:
        """获取订阅统计信息"""
        if self.storage:
            total = self.storage.count(self.collection, {'status': 'active'})
            
            # 按市场类型统计
            pipeline = [
                {'$match': {'status': 'active'}},
                {'$group': {
                    '_id': '$market_type',
                    'count': {'$sum': 1}
                }}
            ]
            market_stats = list(self.storage.db[self.collection].aggregate(pipeline))
            
            # 按频率统计
            pipeline[1]['$group']['_id'] = '$frequency'
            frequency_stats = list(self.storage.db[self.collection].aggregate(pipeline))
            
        else:
            # 内存存储模式
            active_subs = [s for s in self._memory_storage if s.get('status') == 'active']
            total = len(active_subs)
            
            market_stats = {}
            frequency_stats = {}
            for sub in active_subs:
                market = sub.get('market_type')
                freq = sub.get('frequency')
                market_stats[market] = market_stats.get(market, 0) + 1
                frequency_stats[freq] = frequency_stats.get(freq, 0) + 1
                
            market_stats = [{'_id': k, 'count': v} for k, v in market_stats.items()]
            frequency_stats = [{'_id': k, 'count': v} for k, v in frequency_stats.items()]
            
        # 类型统计
        if self.storage:
            try:
                pipeline = [
                    {'$match': {'status': 'active'}},
                    {'$group': {'_id': {'$ifNull': ['$subscription_type', 'stock']}, 'count': {'$sum': 1}}}
                ]
                type_stats = list(self.storage.db[self.collection].aggregate(pipeline))
            except Exception:
                type_stats = []
        else:
            type_counts = {}
            for s in active_subs:
                t = s.get('subscription_type') or 'stock'
                type_counts[t] = type_counts.get(t, 0) + 1
            type_stats = [{'_id': k, 'count': v} for k, v in type_counts.items()]

        return {
            'total': total,
            'by_market': {item['_id']: item['count'] for item in market_stats},
            'by_frequency': {item['_id']: item['count'] for item in frequency_stats},
            'by_type': {item['_id']: item['count'] for item in type_stats}
        }
    
    def get_statistics(self) -> Dict:
        """获取统计信息（别名方法，为了兼容Web组件）"""
        return self.get_subscription_stats()
        
    def _find_subscription(self, email: str, symbol: str) -> Optional[Dict]:
        """查找订阅"""
        query = {
            'email': email.lower(),
            'symbol': symbol.upper()
        }
        
        if self.storage:
            return self.storage.find_one(self.collection, query)
        else:
            for sub in self._memory_storage:
                if (sub.get('email') == email.lower() and
                    sub.get('symbol') == symbol.upper()):
                    return sub
            return None

    def _find_market_subscription(self, email: str, market_scope: str) -> Optional[Dict]:
        """查找市场级订阅（按邮箱+范围唯一）"""
        query = {
            'email': email.lower(),
            'subscription_type': 'market',
            'market_scope': market_scope
        }
        if self.storage:
            return self.storage.find_one(self.collection, query)
        else:
            for sub in self._memory_storage:
                if (sub.get('email') == email.lower() and
                    sub.get('subscription_type') == 'market' and
                    sub.get('market_scope') == market_scope):
                    return sub
            return None
    
    def _find_index_subscription(self, email: str, index_code: str) -> Optional[Dict]:
        """查找指数订阅（按邮箱+指数代码唯一）。"""
        query = {
            'email': email.lower(),
            'subscription_type': 'index',
            'symbol': index_code.upper()
        }
        if self.storage:
            return self.storage.find_one(self.collection, query)
        else:
            for sub in self._memory_storage:
                if (sub.get('email') == email.lower() and
                    sub.get('subscription_type') == 'index' and
                    sub.get('symbol') == index_code.upper()):
                    return sub
            return None
            
    def _validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
        
    def _validate_symbol(self, symbol: str, market_type: str) -> bool:
        """验证股票代码格式"""
        patterns = {
            'A股': r'^[0-9]{6}$',  # 6位数字
            '港股': r'^[0-9]{4,5}(\.HK)?$',  # 4-5位数字，可选.HK后缀
            '美股': r'^[A-Z]{1,5}$'  # 1-5个大写字母
        }

        pattern = patterns.get(market_type)
        if not pattern:
            return False
            
        # 移除可能的后缀
        clean_symbol = symbol.upper().replace('.HK', '')
        return bool(re.match(pattern, clean_symbol))

    def _validate_index_code(self, code: str) -> bool:
        """验证指数代码格式（000300.SH / 399004.SZ / 000016.SH）。"""
        if not code:
            return False
        c = code.strip().upper()
        return bool(re.match(r'^[0-9]{6}((\.SH)|(\.SZ))?$', c))

    def _infer_market_from_index(self, code: str) -> str:
        """根据指数代码推断市场类型。"""
        c = (code or '').upper()
        if c.endswith('.SH') or c.endswith('.SZ'):
            return 'A股'
        return 'A股'
    
    def get_active_subscriptions(self, frequency_filter: Optional[List[str]] = None, *, subscription_type: Optional[str] = None) -> List[Dict]:
        """获取活跃订阅列表
        
        Args:
            frequency_filter: 频率过滤器，如 ['daily', 'weekly']
            
        Returns:
            subscriptions: 活跃订阅列表
        """
        query = {'status': 'active'}
        
        if frequency_filter:
            query['frequency'] = {'$in': frequency_filter}
        if subscription_type:
            query['subscription_type'] = subscription_type
        
        if self.storage:
            subscriptions = list(self.storage.find(self.collection, query))
        else:
            # 内存存储模式
            subscriptions = [
                sub for sub in self._memory_storage
                if (sub.get('status') == 'active' and
                    (not frequency_filter or sub.get('frequency') in frequency_filter) and
                    (not subscription_type or sub.get('subscription_type') == subscription_type))
            ]
            
        return subscriptions

    def get_market_subscriptions(self, *, scope: Optional[str] = None, frequency_filter: Optional[List[str]] = None) -> List[Dict]:
        """获取市场级订阅列表

        Args:
            scope: 限定范围（A股/美股/港股/全球）
            frequency_filter: 频率过滤
        """
        subs = self.get_active_subscriptions(frequency_filter=frequency_filter, subscription_type='market')
        if scope:
            subs = [s for s in subs if s.get('market_scope') == scope]
        return subs

    def get_index_subscriptions(self, *, market: Optional[str] = None, frequency_filter: Optional[List[str]] = None) -> List[Dict]:
        """获取指数订阅列表。

        Args:
            market: 市场类型（如 'A股'）
            frequency_filter: 频率过滤
        """
        subs = self.get_active_subscriptions(frequency_filter=frequency_filter, subscription_type='index')
        if market:
            subs = [s for s in subs if s.get('market_type') == market]
        return subs

    def list_common_index_options(self) -> List[Dict]:
        """返回后端内置的一组常见指数选项（代码、名称、slug）。

        供前端渲染“指数订阅”下拉选项使用。
        """
        options: List[Dict] = []
        try:
            # 首选从API模块导入内置映射
            from tradingagents.api.market_data_endpoints import INDEX_PRESETS  # type: ignore
            for slug, meta in INDEX_PRESETS.items():
                options.append({
                    'slug': slug,
                    'code': meta.get('index_code'),
                    'name': meta.get('name')
                })
        except Exception:
            pass

        # 补充更多常用宽基指数
        extra = [
            {'slug': 'sse', 'code': '000001.SH', 'name': '上证指数'},
            {'slug': 'szse', 'code': '399001.SZ', 'name': '深证成指'},
            {'slug': 'chinext', 'code': '399006.SZ', 'name': '创业板指'},
            {'slug': 'zz1000', 'code': '000852.SH', 'name': '中证1000'},
        ]
        # 去重并合并
        seen = {(o['code'], o['name']) for o in options}
        for e in extra:
            if (e['code'], e['name']) not in seen:
                options.append(e)
        return options
