// =====================================================
// TradingAgents-CN MongoDB Schemas for Document Data
// News, Sentiment, Analysis Results, and Unstructured Data
// =====================================================

// =====================================================
// 1. NEWS DATA COLLECTIONS
// =====================================================

// News Articles Collection
db.createCollection("news_articles", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["article_id", "title", "content", "source", "published_at", "symbols"],
            properties: {
                article_id: {
                    bsonType: "string",
                    description: "Unique article identifier"
                },
                title: {
                    bsonType: "string",
                    description: "Article title"
                },
                content: {
                    bsonType: "string",
                    description: "Full article content"
                },
                summary: {
                    bsonType: "string",
                    description: "Article summary or snippet"
                },
                source: {
                    bsonType: "object",
                    required: ["name", "type"],
                    properties: {
                        name: { bsonType: "string" },
                        type: { enum: ["finnhub", "google_news", "reddit", "twitter", "rss"] },
                        url: { bsonType: "string" },
                        credibility_score: { bsonType: "number", minimum: 0, maximum: 1 }
                    }
                },
                published_at: {
                    bsonType: "date",
                    description: "Original publication timestamp"
                },
                collected_at: {
                    bsonType: "date",
                    description: "When we collected this article"
                },
                symbols: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        required: ["symbol", "relevance_score"],
                        properties: {
                            symbol: { bsonType: "string" },
                            market: { bsonType: "string" },
                            relevance_score: { bsonType: "number", minimum: 0, maximum: 1 }
                        }
                    }
                },
                language: {
                    bsonType: "string",
                    description: "Article language code (en, zh, etc.)"
                },
                region: {
                    bsonType: "string",
                    description: "Market region (US, CN, HK, etc.)"
                },
                categories: {
                    bsonType: "array",
                    items: { bsonType: "string" },
                    description: "News categories (earnings, merger, regulatory, etc.)"
                },
                sentiment: {
                    bsonType: "object",
                    properties: {
                        overall_score: { bsonType: "number", minimum: -1, maximum: 1 },
                        confidence: { bsonType: "number", minimum: 0, maximum: 1 },
                        positive: { bsonType: "number", minimum: 0, maximum: 1 },
                        negative: { bsonType: "number", minimum: 0, maximum: 1 },
                        neutral: { bsonType: "number", minimum: 0, maximum: 1 },
                        model_version: { bsonType: "string" }
                    }
                },
                impact_score: {
                    bsonType: "number",
                    minimum: 0,
                    maximum: 1,
                    description: "Predicted market impact score"
                },
                keywords: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        properties: {
                            term: { bsonType: "string" },
                            tf_idf: { bsonType: "number" },
                            importance: { bsonType: "number" }
                        }
                    }
                },
                entities: {
                    bsonType: "object",
                    properties: {
                        companies: { bsonType: "array", items: { bsonType: "string" } },
                        people: { bsonType: "array", items: { bsonType: "string" } },
                        organizations: { bsonType: "array", items: { bsonType: "string" } },
                        locations: { bsonType: "array", items: { bsonType: "string" } }
                    }
                },
                processing_status: {
                    enum: ["raw", "processed", "analyzed", "failed"],
                    description: "Processing pipeline status"
                },
                metadata: {
                    bsonType: "object",
                    description: "Additional source-specific metadata"
                }
            }
        }
    }
});

// News Processing Queue
db.createCollection("news_processing_queue", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["article_id", "status", "priority", "created_at"],
            properties: {
                article_id: { bsonType: "string" },
                status: { enum: ["pending", "processing", "completed", "failed", "retry"] },
                priority: { enum: ["low", "normal", "high", "urgent"] },
                processing_stage: { bsonType: "string" },
                retry_count: { bsonType: "int", minimum: 0 },
                error_message: { bsonType: "string" },
                assigned_worker: { bsonType: "string" },
                created_at: { bsonType: "date" },
                started_at: { bsonType: "date" },
                completed_at: { bsonType: "date" }
            }
        }
    }
});

// =====================================================
// 2. SOCIAL MEDIA & SENTIMENT DATA
// =====================================================

// Social Media Posts Collection
db.createCollection("social_media_posts", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["post_id", "platform", "content", "author", "posted_at", "symbols"],
            properties: {
                post_id: { bsonType: "string" },
                platform: { enum: ["reddit", "twitter", "weibo", "stocktwits", "discord"] },
                content: { bsonType: "string" },
                author: {
                    bsonType: "object",
                    properties: {
                        username: { bsonType: "string" },
                        follower_count: { bsonType: "long" },
                        verified: { bsonType: "bool" },
                        influence_score: { bsonType: "number" }
                    }
                },
                posted_at: { bsonType: "date" },
                collected_at: { bsonType: "date" },
                symbols: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        properties: {
                            symbol: { bsonType: "string" },
                            mentions: { bsonType: "int" },
                            context: { bsonType: "string" }
                        }
                    }
                },
                engagement: {
                    bsonType: "object",
                    properties: {
                        likes: { bsonType: "long" },
                        shares: { bsonType: "long" },
                        comments: { bsonType: "long" },
                        views: { bsonType: "long" }
                    }
                },
                sentiment: {
                    bsonType: "object",
                    properties: {
                        score: { bsonType: "number", minimum: -1, maximum: 1 },
                        confidence: { bsonType: "number", minimum: 0, maximum: 1 },
                        emotion: { enum: ["joy", "anger", "fear", "sadness", "surprise", "disgust", "neutral"] }
                    }
                },
                language: { bsonType: "string" },
                hashtags: { bsonType: "array", items: { bsonType: "string" } },
                mentions: { bsonType: "array", items: { bsonType: "string" } }
            }
        }
    }
});

// Aggregated Sentiment Metrics
db.createCollection("sentiment_aggregates", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["symbol", "timeframe", "period_start", "period_end"],
            properties: {
                symbol: { bsonType: "string" },
                market: { bsonType: "string" },
                timeframe: { enum: ["1h", "4h", "1d", "1w"] },
                period_start: { bsonType: "date" },
                period_end: { bsonType: "date" },
                sentiment_metrics: {
                    bsonType: "object",
                    properties: {
                        overall_score: { bsonType: "number", minimum: -1, maximum: 1 },
                        bullish_ratio: { bsonType: "number", minimum: 0, maximum: 1 },
                        bearish_ratio: { bsonType: "number", minimum: 0, maximum: 1 },
                        neutral_ratio: { bsonType: "number", minimum: 0, maximum: 1 },
                        volatility: { bsonType: "number", minimum: 0 },
                        volume_weighted_score: { bsonType: "number", minimum: -1, maximum: 1 }
                    }
                },
                source_breakdown: {
                    bsonType: "object",
                    properties: {
                        news: { bsonType: "object" },
                        reddit: { bsonType: "object" },
                        twitter: { bsonType: "object" },
                        weibo: { bsonType: "object" }
                    }
                },
                data_quality: {
                    bsonType: "object",
                    properties: {
                        total_posts: { bsonType: "long" },
                        high_confidence_posts: { bsonType: "long" },
                        verified_authors: { bsonType: "long" },
                        spam_filtered: { bsonType: "long" }
                    }
                },
                trend_indicators: {
                    bsonType: "object",
                    properties: {
                        momentum: { bsonType: "number" },
                        acceleration: { bsonType: "number" },
                        consistency: { bsonType: "number" }
                    }
                }
            }
        }
    }
});

// =====================================================
// 3. ANALYSIS RESULTS & PREDICTIONS
// =====================================================

// Agent Analysis Results
db.createCollection("agent_analysis_results", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["analysis_id", "session_id", "agent_type", "symbol", "analysis_timestamp"],
            properties: {
                analysis_id: { bsonType: "string" },
                session_id: { bsonType: "string" },
                user_id: { bsonType: "string" },
                agent_type: { 
                    enum: ["market_analyst", "news_analyst", "technical_analyst", "fundamental_analyst", 
                           "risk_analyst", "bull_researcher", "bear_researcher", "trader"] 
                },
                symbol: { bsonType: "string" },
                market: { bsonType: "string" },
                analysis_timestamp: { bsonType: "date" },
                analysis_timeframe: { enum: ["1d", "1w", "1m", "3m", "6m", "1y"] },
                
                input_data: {
                    bsonType: "object",
                    properties: {
                        market_data_period: { bsonType: "string" },
                        news_lookback_days: { bsonType: "int" },
                        social_data_included: { bsonType: "bool" },
                        fundamental_data_included: { bsonType: "bool" }
                    }
                },
                
                analysis_content: {
                    bsonType: "object",
                    properties: {
                        summary: { bsonType: "string" },
                        detailed_analysis: { bsonType: "string" },
                        key_points: { bsonType: "array", items: { bsonType: "string" } },
                        supporting_evidence: { bsonType: "array", items: { bsonType: "string" } },
                        risk_factors: { bsonType: "array", items: { bsonType: "string" } },
                        methodology: { bsonType: "string" }
                    }
                },
                
                predictions: {
                    bsonType: "object",
                    properties: {
                        direction: { enum: ["strong_buy", "buy", "hold", "sell", "strong_sell"] },
                        confidence: { bsonType: "number", minimum: 0, maximum: 1 },
                        price_target: {
                            bsonType: "object",
                            properties: {
                                value: { bsonType: "number" },
                                timeframe: { bsonType: "string" },
                                probability: { bsonType: "number" }
                            }
                        },
                        risk_level: { enum: ["low", "medium", "high", "very_high"] },
                        volatility_prediction: { bsonType: "number" }
                    }
                },
                
                technical_indicators: {
                    bsonType: "object",
                    properties: {
                        rsi: { bsonType: "number" },
                        macd: { bsonType: "object" },
                        bollinger_bands: { bsonType: "object" },
                        moving_averages: { bsonType: "object" },
                        support_resistance: { bsonType: "object" }
                    }
                },
                
                model_metadata: {
                    bsonType: "object",
                    properties: {
                        model_name: { bsonType: "string" },
                        model_version: { bsonType: "string" },
                        provider: { bsonType: "string" },
                        input_tokens: { bsonType: "long" },
                        output_tokens: { bsonType: "long" },
                        processing_time_ms: { bsonType: "long" },
                        cost: { bsonType: "number" }
                    }
                },
                
                quality_metrics: {
                    bsonType: "object",
                    properties: {
                        coherence_score: { bsonType: "number" },
                        factual_consistency: { bsonType: "number" },
                        completeness_score: { bsonType: "number" },
                        human_review_flag: { bsonType: "bool" }
                    }
                },
                
                validation_status: { enum: ["pending", "validated", "needs_review", "rejected"] },
                human_feedback: {
                    bsonType: "object",
                    properties: {
                        rating: { bsonType: "int", minimum: 1, maximum: 5 },
                        comments: { bsonType: "string" },
                        corrections: { bsonType: "object" },
                        reviewer_id: { bsonType: "string" },
                        reviewed_at: { bsonType: "date" }
                    }
                }
            }
        }
    }
});

// Multi-Agent Collaboration Sessions
db.createCollection("multi_agent_sessions", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["session_id", "symbols", "strategy", "created_at"],
            properties: {
                session_id: { bsonType: "string" },
                user_id: { bsonType: "string" },
                symbols: { bsonType: "array", items: { bsonType: "string" } },
                strategy: { enum: ["sequential", "parallel", "debate", "consensus"] },
                status: { enum: ["active", "completed", "failed", "cancelled"] },
                
                session_config: {
                    bsonType: "object",
                    properties: {
                        max_iterations: { bsonType: "int" },
                        consensus_threshold: { bsonType: "number" },
                        time_limit_minutes: { bsonType: "int" },
                        cost_limit: { bsonType: "number" }
                    }
                },
                
                participant_agents: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        properties: {
                            agent_type: { bsonType: "string" },
                            weight: { bsonType: "number" },
                            specialization: { bsonType: "string" }
                        }
                    }
                },
                
                collaboration_flow: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        properties: {
                            step: { bsonType: "int" },
                            agent: { bsonType: "string" },
                            action: { bsonType: "string" },
                            input: { bsonType: "object" },
                            output: { bsonType: "object" },
                            timestamp: { bsonType: "date" }
                        }
                    }
                },
                
                consensus_result: {
                    bsonType: "object",
                    properties: {
                        final_recommendation: { bsonType: "string" },
                        confidence_level: { bsonType: "number" },
                        agreement_score: { bsonType: "number" },
                        dissenting_views: { bsonType: "array" },
                        key_disagreements: { bsonType: "array" }
                    }
                },
                
                performance_metrics: {
                    bsonType: "object",
                    properties: {
                        total_cost: { bsonType: "number" },
                        total_time_ms: { bsonType: "long" },
                        total_tokens: { bsonType: "long" },
                        iteration_count: { bsonType: "int" },
                        convergence_rate: { bsonType: "number" }
                    }
                },
                
                created_at: { bsonType: "date" },
                completed_at: { bsonType: "date" }
            }
        }
    }
});

// =====================================================
// 4. TRADING SIGNALS & ALERTS
// =====================================================

// Trading Signals
db.createCollection("trading_signals", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["signal_id", "symbol", "signal_type", "generated_at"],
            properties: {
                signal_id: { bsonType: "string" },
                symbol: { bsonType: "string" },
                market: { bsonType: "string" },
                signal_type: { enum: ["buy", "sell", "hold", "alert"] },
                strength: { enum: ["weak", "moderate", "strong", "very_strong"] },
                timeframe: { enum: ["intraday", "swing", "position"] },
                
                trigger_conditions: {
                    bsonType: "object",
                    properties: {
                        price_condition: { bsonType: "object" },
                        volume_condition: { bsonType: "object" },
                        technical_condition: { bsonType: "object" },
                        news_trigger: { bsonType: "object" },
                        sentiment_trigger: { bsonType: "object" }
                    }
                },
                
                signal_details: {
                    bsonType: "object",
                    properties: {
                        entry_price: { bsonType: "number" },
                        stop_loss: { bsonType: "number" },
                        take_profit: { bsonType: "array", items: { bsonType: "number" } },
                        risk_reward_ratio: { bsonType: "number" },
                        position_size_pct: { bsonType: "number" }
                    }
                },
                
                confidence_metrics: {
                    bsonType: "object",
                    properties: {
                        overall_confidence: { bsonType: "number", minimum: 0, maximum: 1 },
                        technical_confidence: { bsonType: "number" },
                        fundamental_confidence: { bsonType: "number" },
                        sentiment_confidence: { bsonType: "number" },
                        historical_accuracy: { bsonType: "number" }
                    }
                },
                
                supporting_analysis: {
                    bsonType: "object",
                    properties: {
                        primary_agent: { bsonType: "string" },
                        analysis_ids: { bsonType: "array", items: { bsonType: "string" } },
                        consensus_level: { bsonType: "number" }
                    }
                },
                
                generated_at: { bsonType: "date" },
                expires_at: { bsonType: "date" },
                status: { enum: ["active", "expired", "triggered", "cancelled"] },
                
                performance_tracking: {
                    bsonType: "object",
                    properties: {
                        triggered_at: { bsonType: "date" },
                        trigger_price: { bsonType: "number" },
                        max_favorable_move: { bsonType: "number" },
                        max_adverse_move: { bsonType: "number" },
                        final_outcome: { enum: ["profit", "loss", "breakeven", "pending"] },
                        pnl_pct: { bsonType: "number" }
                    }
                }
            }
        }
    }
});

// User Alert Subscriptions
db.createCollection("user_alerts", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["user_id", "alert_type", "conditions", "created_at"],
            properties: {
                user_id: { bsonType: "string" },
                alert_name: { bsonType: "string" },
                alert_type: { enum: ["price", "volume", "technical", "news", "sentiment", "signal"] },
                symbols: { bsonType: "array", items: { bsonType: "string" } },
                
                conditions: {
                    bsonType: "object",
                    properties: {
                        price_above: { bsonType: "number" },
                        price_below: { bsonType: "number" },
                        volume_spike: { bsonType: "number" },
                        sentiment_threshold: { bsonType: "number" },
                        technical_pattern: { bsonType: "string" },
                        news_keywords: { bsonType: "array" }
                    }
                },
                
                delivery_preferences: {
                    bsonType: "object",
                    properties: {
                        email: { bsonType: "bool" },
                        sms: { bsonType: "bool" },
                        webhook: { bsonType: "string" },
                        in_app: { bsonType: "bool" }
                    }
                },
                
                is_active: { bsonType: "bool" },
                created_at: { bsonType: "date" },
                last_triggered: { bsonType: "date" },
                trigger_count: { bsonType: "long" }
            }
        }
    }
});

// =====================================================
// 5. RESEARCH & REPORTS
// =====================================================

// Research Reports
db.createCollection("research_reports", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["report_id", "title", "type", "author", "created_at"],
            properties: {
                report_id: { bsonType: "string" },
                title: { bsonType: "string" },
                type: { enum: ["daily_brief", "weekly_outlook", "sector_analysis", "company_deep_dive", "market_commentary"] },
                author: {
                    bsonType: "object",
                    properties: {
                        type: { enum: ["human", "ai_agent", "mixed"] },
                        name: { bsonType: "string" },
                        credentials: { bsonType: "string" }
                    }
                },
                
                content: {
                    bsonType: "object",
                    properties: {
                        executive_summary: { bsonType: "string" },
                        main_content: { bsonType: "string" },
                        key_insights: { bsonType: "array", items: { bsonType: "string" } },
                        recommendations: { bsonType: "array", items: { bsonType: "object" } },
                        charts_data: { bsonType: "array" },
                        references: { bsonType: "array" }
                    }
                },
                
                scope: {
                    bsonType: "object",
                    properties: {
                        symbols: { bsonType: "array", items: { bsonType: "string" } },
                        sectors: { bsonType: "array", items: { bsonType: "string" } },
                        markets: { bsonType: "array", items: { bsonType: "string" } },
                        time_horizon: { bsonType: "string" }
                    }
                },
                
                quality_metrics: {
                    bsonType: "object",
                    properties: {
                        readability_score: { bsonType: "number" },
                        factual_accuracy: { bsonType: "number" },
                        completeness: { bsonType: "number" },
                        timeliness: { bsonType: "number" }
                    }
                },
                
                distribution: {
                    bsonType: "object",
                    properties: {
                        access_level: { enum: ["public", "premium", "private"] },
                        subscriber_groups: { bsonType: "array" },
                        delivery_channels: { bsonType: "array" }
                    }
                },
                
                created_at: { bsonType: "date" },
                published_at: { bsonType: "date" },
                status: { enum: ["draft", "review", "published", "archived"] }
            }
        }
    }
});

// =====================================================
// 6. INDEXES FOR MONGODB COLLECTIONS
// =====================================================

// News Articles Indexes
db.news_articles.createIndex({ "symbols.symbol": 1, "published_at": -1 });
db.news_articles.createIndex({ "source.type": 1, "published_at": -1 });
db.news_articles.createIndex({ "published_at": -1 });
db.news_articles.createIndex({ "region": 1, "published_at": -1 });
db.news_articles.createIndex({ "processing_status": 1 });
db.news_articles.createIndex({ "categories": 1, "published_at": -1 });
db.news_articles.createIndex({ "impact_score": -1, "published_at": -1 });

// Text search indexes for news
db.news_articles.createIndex({ 
    "title": "text", 
    "content": "text", 
    "summary": "text" 
}, {
    weights: { 
        "title": 3, 
        "content": 1, 
        "summary": 2 
    },
    name: "news_text_search"
});

// Social Media Posts Indexes
db.social_media_posts.createIndex({ "symbols.symbol": 1, "posted_at": -1 });
db.social_media_posts.createIndex({ "platform": 1, "posted_at": -1 });
db.social_media_posts.createIndex({ "author.username": 1, "posted_at": -1 });
db.social_media_posts.createIndex({ "sentiment.score": 1, "posted_at": -1 });

// Text search for social media
db.social_media_posts.createIndex({ "content": "text" }, { name: "social_text_search" });

// Sentiment Aggregates Indexes
db.sentiment_aggregates.createIndex({ "symbol": 1, "timeframe": 1, "period_start": -1 });
db.sentiment_aggregates.createIndex({ "symbol": 1, "period_end": -1 });

// Analysis Results Indexes  
db.agent_analysis_results.createIndex({ "symbol": 1, "analysis_timestamp": -1 });
db.agent_analysis_results.createIndex({ "session_id": 1, "analysis_timestamp": -1 });
db.agent_analysis_results.createIndex({ "agent_type": 1, "analysis_timestamp": -1 });
db.agent_analysis_results.createIndex({ "user_id": 1, "analysis_timestamp": -1 });
db.agent_analysis_results.createIndex({ "predictions.direction": 1, "analysis_timestamp": -1 });
db.agent_analysis_results.createIndex({ "validation_status": 1 });

// Multi-Agent Sessions Indexes
db.multi_agent_sessions.createIndex({ "user_id": 1, "created_at": -1 });
db.multi_agent_sessions.createIndex({ "symbols": 1, "created_at": -1 });
db.multi_agent_sessions.createIndex({ "status": 1, "created_at": -1 });

// Trading Signals Indexes
db.trading_signals.createIndex({ "symbol": 1, "generated_at": -1 });
db.trading_signals.createIndex({ "signal_type": 1, "generated_at": -1 });
db.trading_signals.createIndex({ "status": 1, "generated_at": -1 });
db.trading_signals.createIndex({ "expires_at": 1 });
db.trading_signals.createIndex({ "strength": 1, "generated_at": -1 });

// User Alerts Indexes
db.user_alerts.createIndex({ "user_id": 1, "is_active": 1 });
db.user_alerts.createIndex({ "symbols": 1, "is_active": 1 });
db.user_alerts.createIndex({ "alert_type": 1, "is_active": 1 });

// Research Reports Indexes
db.research_reports.createIndex({ "type": 1, "created_at": -1 });
db.research_reports.createIndex({ "scope.symbols": 1, "created_at": -1 });
db.research_reports.createIndex({ "status": 1, "created_at": -1 });
db.research_reports.createIndex({ "published_at": -1 });

// Text search for research reports
db.research_reports.createIndex({ 
    "title": "text", 
    "content.executive_summary": "text", 
    "content.main_content": "text" 
}, {
    weights: { 
        "title": 3, 
        "content.executive_summary": 2, 
        "content.main_content": 1 
    },
    name: "reports_text_search"
});

// =====================================================
// 7. TTL INDEXES FOR DATA EXPIRATION
// =====================================================

// Automatically delete old news processing queue entries
db.news_processing_queue.createIndex({ "created_at": 1 }, { expireAfterSeconds: 604800 }); // 7 days

// Delete old social media posts based on collection strategy
db.social_media_posts.createIndex({ "posted_at": 1 }, { expireAfterSeconds: 2592000 }); // 30 days

// Expire old trading signals
db.trading_signals.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });

// =====================================================
// 8. AGGREGATION PIPELINES (Stored as Views)
// =====================================================

// Daily Sentiment Summary Pipeline
db.createView("daily_sentiment_summary", "social_media_posts", [
    {
        $match: {
            posted_at: { $gte: new Date(Date.now() - 30*24*60*60*1000) } // Last 30 days
        }
    },
    {
        $group: {
            _id: {
                symbol: "$symbols.symbol",
                date: { $dateToString: { format: "%Y-%m-%d", date: "$posted_at" } }
            },
            avg_sentiment: { $avg: "$sentiment.score" },
            post_count: { $sum: 1 },
            total_engagement: { 
                $sum: { 
                    $add: ["$engagement.likes", "$engagement.shares", "$engagement.comments"] 
                }
            }
        }
    },
    {
        $sort: { "_id.date": -1, "_id.symbol": 1 }
    }
]);

// Top Trending Symbols Pipeline  
db.createView("trending_symbols", "news_articles", [
    {
        $match: {
            published_at: { $gte: new Date(Date.now() - 24*60*60*1000) } // Last 24 hours
        }
    },
    {
        $unwind: "$symbols"
    },
    {
        $group: {
            _id: "$symbols.symbol",
            mention_count: { $sum: 1 },
            avg_relevance: { $avg: "$symbols.relevance_score" },
            avg_sentiment: { $avg: "$sentiment.overall_score" },
            total_impact: { $sum: "$impact_score" }
        }
    },
    {
        $sort: { mention_count: -1, total_impact: -1 }
    },
    {
        $limit: 50
    }
]);

// Agent Performance Summary
db.createView("agent_performance_summary", "agent_analysis_results", [
    {
        $match: {
            analysis_timestamp: { $gte: new Date(Date.now() - 7*24*60*60*1000) } // Last 7 days
        }
    },
    {
        $group: {
            _id: "$agent_type",
            total_analyses: { $sum: 1 },
            avg_processing_time: { $avg: "$model_metadata.processing_time_ms" },
            total_cost: { $sum: "$model_metadata.cost" },
            avg_confidence: { $avg: "$predictions.confidence" },
            validated_count: {
                $sum: { $cond: [{ $eq: ["$validation_status", "validated"] }, 1, 0] }
            }
        }
    },
    {
        $addFields: {
            validation_rate: { $divide: ["$validated_count", "$total_analyses"] }
        }
    },
    {
        $sort: { total_analyses: -1 }
    }
]);