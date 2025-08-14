-- Multi-Model Collaboration Architecture Database Migration
-- TradingAgents-CN Multi-Model Architecture Setup

-- 智能体角色配置表
CREATE TABLE IF NOT EXISTS agent_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    role_type VARCHAR(20) NOT NULL, -- 'analyst', 'specialist', 'manager', 'decision_maker'
    preferred_models TEXT, -- JSON格式存储首选模型列表
    fallback_models TEXT, -- JSON格式存储备用模型列表
    task_complexity_mapping TEXT, -- JSON格式存储任务复杂度映射
    performance_weights TEXT, -- JSON格式存储性能权重配置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型性能评估表
CREATE TABLE IF NOT EXISTS model_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL, -- 'siliconflow', 'google'
    task_type VARCHAR(50) NOT NULL,
    performance_score DECIMAL(5,4),
    cost_per_token DECIMAL(10,8),
    avg_response_time INTEGER, -- 毫秒
    success_rate DECIMAL(5,4),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_model_task ON model_performance (model_name, task_type);

-- 智能路由决策日志表
CREATE TABLE IF NOT EXISTS routing_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(100),
    agent_role VARCHAR(50),
    task_type VARCHAR(50),
    selected_model VARCHAR(100),
    selected_provider VARCHAR(50),
    routing_reason TEXT,
    confidence_score DECIMAL(5,4),
    execution_time INTEGER,
    cost_estimate DECIMAL(10,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 扩展现有分析会话表 (检查列是否存在后添加)
ALTER TABLE analysis_sessions ADD COLUMN routing_strategy VARCHAR(50) DEFAULT 'intelligent';
ALTER TABLE analysis_sessions ADD COLUMN total_agents_used INTEGER DEFAULT 0;
ALTER TABLE analysis_sessions ADD COLUMN model_distribution TEXT; -- JSON格式存储模型使用分布

-- 智能体协作记录表
CREATE TABLE IF NOT EXISTS agent_collaboration_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(100),
    collaboration_stage VARCHAR(50), -- 'analysis', 'debate', 'decision'
    participating_agents TEXT, -- JSON格式
    interaction_sequence TEXT, -- JSON格式存储交互序列
    consensus_score DECIMAL(5,4),
    debate_rounds INTEGER,
    final_outcome TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化智能体角色数据
INSERT OR REPLACE INTO agent_roles (role_name, role_type, preferred_models, fallback_models, task_complexity_mapping, performance_weights) VALUES
('news_hunter', 'analyst', 
 '{"models": [{"model": "qwen3-turbo", "provider": "siliconflow", "use_case": "快速新闻筛选"}, {"model": "gemini-2.5-flash", "provider": "google", "use_case": "新闻情感分析"}]}',
 '{"models": [{"model": "deepseek-v3", "provider": "siliconflow"}]}',
 '{"low": "qwen3-turbo", "medium": "gemini-2.5-flash", "high": "deepseek-v3"}',
 '{"speed": 0.4, "cost": 0.3, "accuracy": 0.3}'),

('fundamental_expert', 'analyst',
 '{"models": [{"model": "deepseek-r1", "provider": "siliconflow", "use_case": "复杂财务分析"}, {"model": "gemini-2.5-pro", "provider": "google", "use_case": "综合基本面评估"}]}',
 '{"models": [{"model": "glm-4.5", "provider": "siliconflow"}]}',
 '{"low": "glm-4.5", "medium": "deepseek-r1", "high": "gemini-2.5-pro"}',
 '{"speed": 0.2, "cost": 0.2, "accuracy": 0.6}'),

('technical_analyst', 'analyst',
 '{"models": [{"model": "deepseek-r1", "provider": "siliconflow", "use_case": "技术图表分析"}, {"model": "kimi-k2", "provider": "siliconflow", "use_case": "趋势分析"}]}',
 '{"models": [{"model": "qwen3-turbo", "provider": "siliconflow"}]}',
 '{"low": "qwen3-turbo", "medium": "kimi-k2", "high": "deepseek-r1"}',
 '{"speed": 0.3, "cost": 0.2, "accuracy": 0.5}'),

('sentiment_analyst', 'analyst',
 '{"models": [{"model": "ernie-4.5", "provider": "siliconflow", "use_case": "中文情绪分析"}, {"model": "gemini-2.5-flash", "provider": "google", "use_case": "多语言情感分析"}]}',
 '{"models": [{"model": "qwen3-turbo", "provider": "siliconflow"}]}',
 '{"low": "qwen3-turbo", "medium": "ernie-4.5", "high": "gemini-2.5-flash"}',
 '{"speed": 0.4, "cost": 0.3, "accuracy": 0.3}'),

('policy_researcher', 'specialist',
 '{"models": [{"model": "ernie-4.5", "provider": "siliconflow", "use_case": "政策解读"}, {"model": "glm-4.5", "provider": "siliconflow", "use_case": "法规分析"}]}',
 '{"models": [{"model": "deepseek-v3", "provider": "siliconflow"}]}',
 '{"low": "glm-4.5", "medium": "ernie-4.5", "high": "deepseek-v3"}',
 '{"speed": 0.2, "cost": 0.3, "accuracy": 0.5}'),

('tool_engineer', 'specialist',
 '{"models": [{"model": "deepseek-v3", "provider": "siliconflow", "use_case": "工具开发"}, {"model": "step-3", "provider": "siliconflow", "use_case": "算法设计"}]}',
 '{"models": [{"model": "qwen3-turbo", "provider": "siliconflow"}]}',
 '{"low": "qwen3-turbo", "medium": "deepseek-v3", "high": "step-3"}',
 '{"speed": 0.3, "cost": 0.2, "accuracy": 0.5}'),

('risk_manager', 'manager',
 '{"models": [{"model": "deepseek-r1", "provider": "siliconflow", "use_case": "风险评估"}, {"model": "gemini-2.5-pro", "provider": "google", "use_case": "综合风控"}]}',
 '{"models": [{"model": "glm-4.5", "provider": "siliconflow"}]}',
 '{"low": "glm-4.5", "medium": "deepseek-r1", "high": "gemini-2.5-pro"}',
 '{"speed": 0.2, "cost": 0.2, "accuracy": 0.6}'),

('compliance_officer', 'manager',
 '{"models": [{"model": "ernie-4.5", "provider": "siliconflow", "use_case": "合规检查"}, {"model": "glm-4.5", "provider": "siliconflow", "use_case": "法规审核"}]}',
 '{"models": [{"model": "deepseek-v3", "provider": "siliconflow"}]}',
 '{"low": "glm-4.5", "medium": "ernie-4.5", "high": "deepseek-v3"}',
 '{"speed": 0.3, "cost": 0.2, "accuracy": 0.5}'),

('chief_decision_officer', 'decision_maker',
 '{"models": [{"model": "gemini-2.5-pro", "provider": "google", "use_case": "最终决策仲裁"}]}',
 '{"models": [{"model": "deepseek-r1", "provider": "siliconflow"}]}',
 '{"low": "deepseek-r1", "medium": "gemini-2.5-pro", "high": "gemini-2.5-pro"}',
 '{"speed": 0.1, "cost": 0.1, "accuracy": 0.8}');

-- 初始化模型性能基准数据
INSERT OR REPLACE INTO model_performance (model_name, provider, task_type, performance_score, cost_per_token, avg_response_time, success_rate) VALUES
-- SiliconFlow models
('deepseek-r1', 'siliconflow', 'reasoning', 0.95, 0.0000014, 8000, 0.98),
('deepseek-v3', 'siliconflow', 'general', 0.88, 0.0000007, 3000, 0.95),
('qwen3-turbo', 'siliconflow', 'speed', 0.82, 0.0000003, 1500, 0.93),
('glm-4.5', 'siliconflow', 'balanced', 0.85, 0.0000005, 2500, 0.94),
('kimi-k2', 'siliconflow', 'context', 0.87, 0.0000012, 4000, 0.92),
('ernie-4.5', 'siliconflow', 'chinese', 0.83, 0.0000008, 3500, 0.91),
('step-3', 'siliconflow', 'reasoning', 0.90, 0.0000015, 6000, 0.96),

-- Google models
('gemini-2.5-pro', 'google', 'premium', 0.92, 0.0000125, 5000, 0.97),
('gemini-2.5-flash', 'google', 'speed', 0.85, 0.0000025, 2000, 0.94);