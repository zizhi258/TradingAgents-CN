-- TimescaleDB initialization script for TradingAgents-CN
-- This script sets up the time-series database with optimized tables and indexes

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create database user for application
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'tradingagents') THEN
        CREATE ROLE tradingagents WITH LOGIN PASSWORD 'tradingagents123';
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE tradingagents TO tradingagents;
GRANT ALL ON SCHEMA public TO tradingagents;

-- ============================================================================
-- Market Data Tables
-- ============================================================================

-- Main market data table (OHLCV data)
CREATE TABLE IF NOT EXISTS market_data_daily (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT,
    market TEXT,
    open_price DECIMAL(12,4),
    high_price DECIMAL(12,4),
    low_price DECIMAL(12,4),
    close_price DECIMAL(12,4),
    volume BIGINT,
    turnover DECIMAL(20,4),
    market_cap DECIMAL(20,4),
    data_source TEXT NOT NULL,
    quality_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT market_data_daily_pkey PRIMARY KEY (time, symbol, data_source),
    CONSTRAINT market_data_daily_prices_check CHECK (
        high_price >= low_price AND 
        high_price >= open_price AND 
        high_price >= close_price AND
        low_price <= open_price AND 
        low_price <= close_price
    ),
    CONSTRAINT market_data_daily_volume_check CHECK (volume >= 0)
);

-- Convert to hypertable (time-series optimization)
SELECT create_hypertable(
    'market_data_daily', 
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create space partitioning by symbol for better performance
SELECT add_dimension(
    'market_data_daily',
    'symbol',
    number_partitions => 4,
    if_not_exists => TRUE
);

-- Intraday/tick data table
CREATE TABLE IF NOT EXISTS market_data_intraday (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DECIMAL(12,4),
    volume INTEGER,
    bid DECIMAL(12,4),
    ask DECIMAL(12,4),
    trade_type TEXT, -- 'B' for buy, 'S' for sell, 'N' for neutral
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT market_data_intraday_pkey PRIMARY KEY (time, symbol, data_source)
);

-- Convert to hypertable with smaller chunks for intraday data
SELECT create_hypertable(
    'market_data_intraday', 
    'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Technical indicators table
CREATE TABLE IF NOT EXISTS technical_indicators (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    indicator_set TEXT NOT NULL,
    indicators JSONB NOT NULL,
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT technical_indicators_pkey PRIMARY KEY (time, symbol, indicator_set)
);

SELECT create_hypertable(
    'technical_indicators', 
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- News and Sentiment Data
-- ============================================================================

-- News impact tracking
CREATE TABLE IF NOT EXISTS news_impact (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    news_id TEXT,
    sentiment_score DECIMAL(3,2), -- -1.0 to 1.0
    confidence_score DECIMAL(3,2), -- 0.0 to 1.0
    impact_category TEXT, -- 'earnings', 'guidance', 'merger', etc.
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT news_impact_pkey PRIMARY KEY (time, symbol, news_id),
    CONSTRAINT news_impact_sentiment_check CHECK (
        sentiment_score >= -1.0 AND sentiment_score <= 1.0
    ),
    CONSTRAINT news_impact_confidence_check CHECK (
        confidence_score >= 0.0 AND confidence_score <= 1.0
    )
);

SELECT create_hypertable(
    'news_impact', 
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- Financial Statements Data
-- ============================================================================

-- Quarterly financial metrics
CREATE TABLE IF NOT EXISTS financial_metrics (
    time TIMESTAMPTZ NOT NULL, -- Report date
    symbol TEXT NOT NULL,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    statement_type TEXT, -- 'income', 'balance', 'cashflow'
    metrics JSONB NOT NULL,
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT financial_metrics_pkey PRIMARY KEY (time, symbol, statement_type),
    CONSTRAINT financial_metrics_quarter_check CHECK (
        fiscal_quarter >= 1 AND fiscal_quarter <= 4
    )
);

SELECT create_hypertable(
    'financial_metrics', 
    'time',
    chunk_time_interval => INTERVAL '3 months',
    if_not_exists => TRUE
);

-- ============================================================================
-- ML Features and Predictions
-- ============================================================================

-- ML features for model training
CREATE TABLE IF NOT EXISTS ml_features (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    feature_set TEXT NOT NULL,
    model_version TEXT,
    features JSONB NOT NULL,
    target_values JSONB, -- For training data
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT ml_features_pkey PRIMARY KEY (time, symbol, feature_set, model_version)
);

SELECT create_hypertable(
    'ml_features', 
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Model predictions
CREATE TABLE IF NOT EXISTS model_predictions (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    prediction_horizon TEXT, -- '1d', '5d', '1w', '1m'
    predictions JSONB NOT NULL,
    confidence_scores JSONB,
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT model_predictions_pkey PRIMARY KEY (time, symbol, model_name, prediction_horizon)
);

SELECT create_hypertable(
    'model_predictions', 
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- Data Quality Metrics
-- ============================================================================

-- Data quality monitoring
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    time TIMESTAMPTZ NOT NULL,
    dataset_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DECIMAL(10,6),
    threshold_value DECIMAL(10,6),
    passed BOOLEAN,
    severity TEXT,
    details JSONB,
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT data_quality_metrics_pkey PRIMARY KEY (time, dataset_name, metric_name)
);

SELECT create_hypertable(
    'data_quality_metrics', 
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================================================
-- Performance Optimization Indexes
-- ============================================================================

-- Market data indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_daily_symbol_time 
ON market_data_daily (symbol, time DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_daily_exchange_time 
ON market_data_daily (exchange, time DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_daily_source_time 
ON market_data_daily (data_source, time DESC);

-- Intraday data indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_intraday_symbol_time 
ON market_data_intraday (symbol, time DESC);

-- Technical indicators indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tech_indicators_symbol_set_time 
ON technical_indicators (symbol, indicator_set, time DESC);

-- News impact indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_impact_symbol_time 
ON news_impact (symbol, time DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_news_impact_sentiment 
ON news_impact (sentiment_score, time DESC) 
WHERE sentiment_score IS NOT NULL;

-- Financial metrics indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_financial_metrics_symbol_year 
ON financial_metrics (symbol, fiscal_year DESC);

-- ML features indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ml_features_symbol_set_time 
ON ml_features (symbol, feature_set, time DESC);

-- Model predictions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_symbol_model_time 
ON model_predictions (symbol, model_name, time DESC);

-- Data quality indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dq_metrics_dataset_time 
ON data_quality_metrics (dataset_name, time DESC);

-- ============================================================================
-- Compression Policies (Data Lifecycle Management)
-- ============================================================================

-- Enable compression for older data to save storage
SELECT add_compression_policy('market_data_daily', INTERVAL '7 days');
SELECT add_compression_policy('market_data_intraday', INTERVAL '1 day');
SELECT add_compression_policy('technical_indicators', INTERVAL '7 days');
SELECT add_compression_policy('news_impact', INTERVAL '30 days');
SELECT add_compression_policy('financial_metrics', INTERVAL '90 days');
SELECT add_compression_policy('ml_features', INTERVAL '7 days');
SELECT add_compression_policy('model_predictions', INTERVAL '7 days');
SELECT add_compression_policy('data_quality_metrics', INTERVAL '7 days');

-- ============================================================================
-- Data Retention Policies
-- ============================================================================

-- Automatically drop old data to manage storage
SELECT add_retention_policy('market_data_intraday', INTERVAL '90 days');
SELECT add_retention_policy('news_impact', INTERVAL '2 years');
SELECT add_retention_policy('ml_features', INTERVAL '1 year');
SELECT add_retention_policy('data_quality_metrics', INTERVAL '1 year');

-- Keep daily market data and financial metrics longer
SELECT add_retention_policy('market_data_daily', INTERVAL '10 years');
SELECT add_retention_policy('financial_metrics', INTERVAL '20 years');

-- ============================================================================
-- Materialized Views for Common Queries
-- ============================================================================

-- Latest prices materialized view (refreshed every minute)
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_market_prices AS
SELECT DISTINCT ON (symbol)
    symbol,
    time,
    close_price as price,
    open_price,
    high_price,
    low_price,
    volume,
    data_source,
    updated_at
FROM market_data_daily
ORDER BY symbol, time DESC;

CREATE UNIQUE INDEX ON latest_market_prices (symbol);

-- Create a refresh policy for the materialized view
CREATE OR REPLACE FUNCTION refresh_latest_prices()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY latest_market_prices;
END;
$$ LANGUAGE plpgsql;

-- Daily aggregated stats
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_market_stats AS
SELECT 
    time_bucket('1 day', time) as day,
    symbol,
    first(open_price, time) as open,
    max(high_price) as high,
    min(low_price) as low,
    last(close_price, time) as close,
    sum(volume) as volume,
    avg(close_price) as avg_price,
    stddev(close_price) as price_volatility,
    count(*) as data_points
FROM market_data_daily
WHERE time >= NOW() - INTERVAL '1 year'
GROUP BY day, symbol
ORDER BY day DESC, symbol;

CREATE UNIQUE INDEX ON daily_market_stats (day, symbol);

-- ============================================================================
-- Utility Functions
-- ============================================================================

-- Function to calculate simple moving average
CREATE OR REPLACE FUNCTION sma(symbol_param TEXT, period_days INTEGER, end_date TIMESTAMPTZ DEFAULT NOW())
RETURNS TABLE(time TIMESTAMPTZ, sma_value DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.time,
        AVG(t.close_price) OVER (
            ORDER BY t.time 
            ROWS BETWEEN period_days-1 PRECEDING AND CURRENT ROW
        )::DECIMAL as sma_value
    FROM market_data_daily t
    WHERE t.symbol = symbol_param 
      AND t.time <= end_date
      AND t.time >= end_date - INTERVAL '1 year'
    ORDER BY t.time;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate daily returns
CREATE OR REPLACE FUNCTION daily_returns(symbol_param TEXT, days INTEGER DEFAULT 252)
RETURNS TABLE(time TIMESTAMPTZ, daily_return DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.time,
        (t.close_price - LAG(t.close_price) OVER (ORDER BY t.time)) / 
        LAG(t.close_price) OVER (ORDER BY t.time) as daily_return
    FROM market_data_daily t
    WHERE t.symbol = symbol_param 
      AND t.time >= NOW() - INTERVAL '1 day' * days
    ORDER BY t.time;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Monitoring Views
-- ============================================================================

-- Data pipeline health monitoring
CREATE OR REPLACE VIEW pipeline_health AS
SELECT 
    'market_data_daily' as table_name,
    COUNT(*) as total_records,
    MAX(time) as latest_data,
    MIN(time) as earliest_data,
    COUNT(DISTINCT symbol) as unique_symbols,
    AVG(CASE WHEN quality_score IS NOT NULL THEN quality_score ELSE NULL END) as avg_quality_score
FROM market_data_daily
WHERE time >= NOW() - INTERVAL '7 days'

UNION ALL

SELECT 
    'market_data_intraday' as table_name,
    COUNT(*) as total_records,
    MAX(time) as latest_data,
    MIN(time) as earliest_data,
    COUNT(DISTINCT symbol) as unique_symbols,
    NULL as avg_quality_score
FROM market_data_intraday
WHERE time >= NOW() - INTERVAL '1 day'

UNION ALL

SELECT 
    'news_impact' as table_name,
    COUNT(*) as total_records,
    MAX(time) as latest_data,
    MIN(time) as earliest_data,
    COUNT(DISTINCT symbol) as unique_symbols,
    AVG(confidence_score) as avg_quality_score
FROM news_impact
WHERE time >= NOW() - INTERVAL '7 days';

-- Grant permissions to application user
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tradingagents;
GRANT SELECT ON ALL VIEWS IN SCHEMA public TO tradingagents;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO tradingagents;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO tradingagents;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB initialization completed successfully for TradingAgents-CN';
    RAISE NOTICE 'Created % hypertables with optimized indexes and compression policies', 
        (SELECT COUNT(*) FROM timescaledb_information.hypertables);
END $$;