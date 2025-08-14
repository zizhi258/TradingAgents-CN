-- =====================================================
-- TradingAgents-CN Optimized Database Schemas
-- Hybrid PostgreSQL + TimescaleDB + MongoDB Design
-- =====================================================

-- =====================================================
-- 1. TIME-SERIES DATA (PostgreSQL + TimescaleDB)
-- =====================================================

-- Enable TimescaleDB extension for time-series optimization
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Market Data Time-Series (Hypertable for OHLCV data)
CREATE TABLE market_data (
    id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(10) NOT NULL, -- 'US', 'CN', 'HK'
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(15,4) NOT NULL,
    high DECIMAL(15,4) NOT NULL,
    low DECIMAL(15,4) NOT NULL,
    close DECIMAL(15,4) NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    adjusted_close DECIMAL(15,4),
    data_source VARCHAR(20) NOT NULL, -- 'finnhub', 'tushare', 'yfinance'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol, market)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('market_data', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Technical Indicators Time-Series
CREATE TABLE technical_indicators (
    id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    indicator_type VARCHAR(50) NOT NULL, -- 'RSI', 'MACD', 'SMA50', etc.
    value DECIMAL(15,6),
    metadata JSONB, -- Store indicator parameters and additional data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol, indicator_type)
);

SELECT create_hypertable('technical_indicators', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Real-time Quote Data (High-frequency updates)
CREATE TABLE realtime_quotes (
    id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    bid DECIMAL(15,4),
    ask DECIMAL(15,4),
    last_price DECIMAL(15,4) NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    change_amount DECIMAL(15,4),
    change_percent DECIMAL(8,4),
    data_source VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol)
);

SELECT create_hypertable('realtime_quotes', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- ML Feature Store Time-Series
CREATE TABLE ml_features (
    id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    feature_set VARCHAR(100) NOT NULL, -- 'technical_v1', 'sentiment_v2', etc.
    features JSONB NOT NULL, -- Flexible feature storage
    feature_hash VARCHAR(64), -- For feature versioning and deduplication
    model_version VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol, feature_set)
);

SELECT create_hypertable('ml_features', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- =====================================================
-- 2. FUNDAMENTAL DATA (PostgreSQL)
-- =====================================================

-- Company Basic Information
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    market VARCHAR(10) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(3), -- ISO country code
    currency VARCHAR(3), -- ISO currency code
    market_cap BIGINT,
    shares_outstanding BIGINT,
    ipo_date DATE,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB, -- Store additional company information
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Financial Statements
CREATE TABLE financial_statements (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    statement_type VARCHAR(20) NOT NULL, -- 'income', 'balance', 'cashflow'
    period VARCHAR(20) NOT NULL, -- '2023Q4', '2023FY'
    report_date DATE NOT NULL,
    filing_date DATE,
    currency VARCHAR(3),
    financials JSONB NOT NULL, -- Store all financial metrics as JSON
    data_source VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, statement_type, period, report_date)
);

-- Financial Ratios and Metrics (Computed)
CREATE TABLE financial_metrics (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    period VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,
    pe_ratio DECIMAL(10,4),
    pb_ratio DECIMAL(10,4),
    ps_ratio DECIMAL(10,4),
    roe DECIMAL(8,4),
    roa DECIMAL(8,4),
    debt_to_equity DECIMAL(10,4),
    current_ratio DECIMAL(8,4),
    quick_ratio DECIMAL(8,4),
    gross_margin DECIMAL(8,4),
    operating_margin DECIMAL(8,4),
    net_margin DECIMAL(8,4),
    eps DECIMAL(10,4),
    revenue_growth DECIMAL(8,4),
    earnings_growth DECIMAL(8,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, period, report_date)
);

-- =====================================================
-- 3. USER MANAGEMENT & CONFIGURATION
-- =====================================================

-- Users and Authentication
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(20) DEFAULT 'user', -- 'admin', 'analyst', 'user'
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User Configurations
CREATE TABLE user_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    config_type VARCHAR(50) NOT NULL, -- 'watchlist', 'alerts', 'preferences'
    config_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, config_type)
);

-- API Usage Tracking
CREATE TABLE api_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(100),
    provider VARCHAR(50) NOT NULL, -- 'openai', 'gemini', 'siliconflow'
    model_name VARCHAR(100) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost DECIMAL(10,6) DEFAULT 0,
    analysis_type VARCHAR(50),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- Convert to hypertable for efficient time-series queries
SELECT create_hypertable('api_usage', 'timestamp', chunk_time_interval => INTERVAL '7 days');

-- =====================================================
-- 4. AUDIT & LOGGING
-- =====================================================

-- System Events and Audit Log
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL, -- 'login', 'analysis', 'config_change'
    event_data JSONB NOT NULL,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('audit_logs', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Error and Performance Logs
CREATE TABLE performance_logs (
    id BIGSERIAL PRIMARY KEY,
    component VARCHAR(50) NOT NULL, -- 'api', 'data_fetch', 'analysis'
    operation VARCHAR(100) NOT NULL,
    duration_ms INTEGER,
    status VARCHAR(20) NOT NULL, -- 'success', 'error', 'timeout'
    error_message TEXT,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('performance_logs', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- =====================================================
-- 5. ML MODEL METADATA & VERSIONING
-- =====================================================

-- ML Models Registry
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL, -- 'classification', 'regression', 'clustering'
    version VARCHAR(20) NOT NULL,
    description TEXT,
    algorithm VARCHAR(50),
    hyperparameters JSONB,
    training_data_hash VARCHAR(64),
    performance_metrics JSONB,
    is_active BOOLEAN DEFAULT false,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model_name, version)
);

-- Model Training Runs
CREATE TABLE model_training_runs (
    id BIGSERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES ml_models(id),
    run_id VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed'
    training_start TIMESTAMPTZ,
    training_end TIMESTAMPTZ,
    dataset_size INTEGER,
    validation_score DECIMAL(8,6),
    artifacts JSONB, -- Store model artifacts metadata
    logs TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Feature Engineering Pipeline
CREATE TABLE feature_pipelines (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL UNIQUE,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    input_features JSONB NOT NULL,
    transformation_steps JSONB NOT NULL,
    output_schema JSONB NOT NULL,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(pipeline_name, version)
);

-- =====================================================
-- 6. INDEXES FOR PERFORMANCE OPTIMIZATION
-- =====================================================

-- Market Data Indexes
CREATE INDEX CONCURRENTLY idx_market_data_symbol_time ON market_data (symbol, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_market_data_market_time ON market_data (market, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_market_data_source ON market_data (data_source, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_market_data_volume ON market_data (volume DESC, timestamp DESC) WHERE volume > 0;

-- Technical Indicators Indexes
CREATE INDEX CONCURRENTLY idx_technical_indicators_symbol_type ON technical_indicators (symbol, indicator_type, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_technical_indicators_type ON technical_indicators (indicator_type, timestamp DESC);

-- Real-time Quotes Indexes
CREATE INDEX CONCURRENTLY idx_realtime_quotes_symbol ON realtime_quotes (symbol, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_realtime_quotes_market ON realtime_quotes (market, timestamp DESC);

-- ML Features Indexes
CREATE INDEX CONCURRENTLY idx_ml_features_symbol_set ON ml_features (symbol, feature_set, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_ml_features_hash ON ml_features (feature_hash);
CREATE INDEX CONCURRENTLY idx_ml_features_model_version ON ml_features (model_version, timestamp DESC);

-- Companies Indexes
CREATE INDEX CONCURRENTLY idx_companies_market ON companies (market);
CREATE INDEX CONCURRENTLY idx_companies_sector ON companies (sector);
CREATE INDEX CONCURRENTLY idx_companies_active ON companies (is_active) WHERE is_active = true;

-- Financial Data Indexes
CREATE INDEX CONCURRENTLY idx_financial_statements_symbol_period ON financial_statements (symbol, statement_type, period DESC);
CREATE INDEX CONCURRENTLY idx_financial_statements_report_date ON financial_statements (report_date DESC);
CREATE INDEX CONCURRENTLY idx_financial_metrics_symbol_period ON financial_metrics (symbol, period DESC);

-- User and Configuration Indexes
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);
CREATE INDEX CONCURRENTLY idx_users_active ON users (is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_user_configs_user_type ON user_configs (user_id, config_type);

-- API Usage Indexes
CREATE INDEX CONCURRENTLY idx_api_usage_user_time ON api_usage (user_id, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_api_usage_provider ON api_usage (provider, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_api_usage_session ON api_usage (session_id, timestamp DESC);

-- Audit and Performance Indexes
CREATE INDEX CONCURRENTLY idx_audit_logs_user_time ON audit_logs (user_id, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_audit_logs_event_type ON audit_logs (event_type, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_performance_logs_component ON performance_logs (component, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_performance_logs_status ON performance_logs (status, timestamp DESC) WHERE status != 'success';

-- ML Model Indexes
CREATE INDEX CONCURRENTLY idx_ml_models_type ON ml_models (model_type, is_active);
CREATE INDEX CONCURRENTLY idx_model_training_runs_model_id ON model_training_runs (model_id, training_start DESC);
CREATE INDEX CONCURRENTLY idx_feature_pipelines_active ON feature_pipelines (is_active) WHERE is_active = true;

-- =====================================================
-- 7. DATA RETENTION POLICIES (TimescaleDB)
-- =====================================================

-- Retention policies for different data types
-- Keep detailed market data for 2 years, then compress
SELECT add_retention_policy('market_data', INTERVAL '2 years');

-- Keep real-time quotes for 30 days only
SELECT add_retention_policy('realtime_quotes', INTERVAL '30 days');

-- Keep API usage logs for 1 year
SELECT add_retention_policy('api_usage', INTERVAL '1 year');

-- Keep audit logs for 7 years (compliance)
SELECT add_retention_policy('audit_logs', INTERVAL '7 years');

-- Keep performance logs for 90 days
SELECT add_retention_policy('performance_logs', INTERVAL '90 days');

-- ML features retention based on model lifecycle
SELECT add_retention_policy('ml_features', INTERVAL '1 year');

-- =====================================================
-- 8. COMPRESSION POLICIES (TimescaleDB)
-- =====================================================

-- Compress market data older than 7 days
SELECT add_compression_policy('market_data', INTERVAL '7 days');

-- Compress technical indicators older than 7 days
SELECT add_compression_policy('technical_indicators', INTERVAL '7 days');

-- Compress API usage older than 7 days
SELECT add_compression_policy('api_usage', INTERVAL '7 days');

-- Compress audit logs older than 30 days
SELECT add_compression_policy('audit_logs', INTERVAL '30 days');

-- Compress performance logs older than 7 days
SELECT add_compression_policy('performance_logs', INTERVAL '7 days');

-- Compress ML features older than 7 days
SELECT add_compression_policy('ml_features', INTERVAL '7 days');

-- =====================================================
-- 9. MATERIALIZED VIEWS FOR ANALYTICS
-- =====================================================

-- Daily market summary materialized view
CREATE MATERIALIZED VIEW daily_market_summary AS
SELECT 
    symbol,
    market,
    DATE(timestamp) as trade_date,
    first(open, timestamp) as day_open,
    max(high) as day_high,
    min(low) as day_low,
    last(close, timestamp) as day_close,
    sum(volume) as day_volume,
    COUNT(*) as data_points
FROM market_data
WHERE timestamp >= NOW() - INTERVAL '1 year'
GROUP BY symbol, market, DATE(timestamp)
ORDER BY symbol, market, trade_date DESC;

-- Create index on materialized view
CREATE INDEX idx_daily_summary_symbol_date ON daily_market_summary (symbol, trade_date DESC);
CREATE INDEX idx_daily_summary_market_date ON daily_market_summary (market, trade_date DESC);

-- Weekly API usage summary
CREATE MATERIALIZED VIEW weekly_api_usage AS
SELECT 
    DATE_TRUNC('week', timestamp) as week_start,
    provider,
    model_name,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost) as total_cost
FROM api_usage
WHERE timestamp >= NOW() - INTERVAL '6 months'
GROUP BY DATE_TRUNC('week', timestamp), provider, model_name
ORDER BY week_start DESC, total_cost DESC;

-- =====================================================
-- 10. FUNCTIONS AND STORED PROCEDURES
-- =====================================================

-- Function to get latest quote for a symbol
CREATE OR REPLACE FUNCTION get_latest_quote(p_symbol VARCHAR(20))
RETURNS TABLE(
    symbol VARCHAR(20),
    last_price DECIMAL(15,4),
    change_percent DECIMAL(8,4),
    volume BIGINT,
    timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rq.symbol,
        rq.last_price,
        rq.change_percent,
        rq.volume,
        rq.timestamp
    FROM realtime_quotes rq
    WHERE rq.symbol = p_symbol
    ORDER BY rq.timestamp DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate technical indicators
CREATE OR REPLACE FUNCTION calculate_sma(p_symbol VARCHAR(20), p_period INTEGER, p_start_date TIMESTAMPTZ)
RETURNS TABLE(
    timestamp TIMESTAMPTZ,
    sma_value DECIMAL(15,6)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        md.timestamp,
        AVG(md.close) OVER (
            ORDER BY md.timestamp 
            ROWS BETWEEN p_period-1 PRECEDING AND CURRENT ROW
        ) as sma_value
    FROM market_data md
    WHERE md.symbol = p_symbol 
      AND md.timestamp >= p_start_date
    ORDER BY md.timestamp;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_market_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY weekly_api_usage;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 11. TRIGGERS FOR DATA CONSISTENCY
-- =====================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_configs_updated_at BEFORE UPDATE ON user_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 12. SECURITY AND PERMISSIONS
-- =====================================================

-- Create roles for different access levels
CREATE ROLE trading_readonly;
CREATE ROLE trading_analyst;
CREATE ROLE trading_admin;

-- Grant permissions to readonly role
GRANT SELECT ON ALL TABLES IN SCHEMA public TO trading_readonly;
GRANT USAGE ON SCHEMA public TO trading_readonly;

-- Grant permissions to analyst role
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO trading_analyst;
GRANT DELETE ON api_usage, audit_logs, performance_logs TO trading_analyst;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trading_analyst;
GRANT USAGE ON SCHEMA public TO trading_analyst;

-- Grant all permissions to admin role
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_admin;
GRANT USAGE ON SCHEMA public TO trading_admin;

-- Row Level Security (RLS) for user data
ALTER TABLE user_configs ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_configs_policy ON user_configs 
    FOR ALL TO trading_analyst
    USING (user_id = current_setting('app.current_user_id')::integer);

ALTER TABLE api_usage ENABLE ROW LEVEL SECURITY;  
CREATE POLICY api_usage_policy ON api_usage
    FOR ALL TO trading_analyst
    USING (user_id = current_setting('app.current_user_id')::integer OR user_id IS NULL);