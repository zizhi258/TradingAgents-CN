#!/usr/bin/env python3
"""
ML Pipeline Demo for TradingAgents-CN

This script demonstrates the complete ML pipeline integration with the TradingAgents-CN system,
showing how to use machine learning for stock market analysis, prediction, and trading signals.

Usage:
    python ml_pipeline_demo.py
    python ml_pipeline_demo.py --symbols AAPL MSFT GOOGL
    python ml_pipeline_demo.py --market CN --symbols 000001.SZ 000002.SZ
"""

import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import ML pipeline components
from tradingagents.ml import (
    MLPipeline, PipelineConfig, create_default_pipeline,
    FeatureConfig, ModelConfig, ValidationConfig, DeploymentConfig,
    create_ml_enhanced_agents, demonstrate_ml_integration
)
from tradingagents.ml.models import create_model
from tradingagents.utils.logging_init import get_logger

# Setup logging
logger = get_logger("ml_demo")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="ML Pipeline Demo for TradingAgents-CN")
    parser.add_argument(
        "--symbols", 
        nargs="+", 
        default=["AAPL", "MSFT", "GOOGL"],
        help="Stock symbols to analyze (default: AAPL MSFT GOOGL)"
    )
    parser.add_argument(
        "--market", 
        choices=["US", "CN", "HK"], 
        default="US",
        help="Market type (default: US)"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=365,
        help="Number of days of historical data (default: 365)"
    )
    parser.add_argument(
        "--output-dir", 
        default="./ml_demo_output",
        help="Output directory for results (default: ./ml_demo_output)"
    )
    parser.add_argument(
        "--skip-training", 
        action="store_true",
        help="Skip model training (use for quick demo)"
    )
    parser.add_argument(
        "--model-type", 
        choices=["xgboost", "random_forest", "lstm", "transformer"], 
        default="xgboost",
        help="Primary model type to use (default: xgboost)"
    )
    parser.add_argument(
        "--enable-deployment", 
        action="store_true",
        help="Enable model deployment and API serving"
    )
    
    return parser.parse_args()


def create_demo_config(args):
    """Create pipeline configuration from arguments"""
    
    # Adjust symbols for Chinese market
    symbols = args.symbols
    if args.market == "CN" and symbols == ["AAPL", "MSFT", "GOOGL"]:
        symbols = ["000001.SZ", "000002.SZ", "600000.SS"]  # Default Chinese stocks
        logger.info(f"Using default Chinese stocks: {symbols}")
    
    # Calculate date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    
    # Feature engineering config
    feature_config = FeatureConfig(
        lookback_window=60,
        technical_indicators=True,
        fundamental_features=True,
        sentiment_features=True,
        microstructure_features=True,
        time_series_features=True,
        normalize_features=True
    )
    
    # Model configurations
    model_configs = {
        "price_prediction": ModelConfig(
            model_type=args.model_type,
            task_type="regression",
            target_variable="future_return_5d",
            lookback_window=30,
            prediction_horizon=5
        ),
        "signal_classification": ModelConfig(
            model_type="random_forest",
            task_type="classification",
            target_variable="trading_signal",
            lookback_window=20
        ),
        "volatility_prediction": ModelConfig(
            model_type=args.model_type,
            task_type="regression",
            target_variable="future_volatility",
            lookback_window=40
        ),
        "risk_assessment": ModelConfig(
            model_type="random_forest",
            task_type="classification",
            target_variable="risk_level",
            lookback_window=50
        )
    }
    
    # Validation config
    validation_config = ValidationConfig(
        n_splits=3 if args.skip_training else 5,
        test_size=0.2,
        initial_capital=100000.0,
        transaction_cost=0.001
    )
    
    # Deployment config
    deployment_config = DeploymentConfig(
        model_registry_path=f"{args.output_dir}/models",
        api_host="0.0.0.0",
        api_port=8080,
        enable_monitoring=args.enable_deployment,
        enable_redis_cache=False,  # Disable Redis for demo
        enable_docker=False  # Disable Docker for demo
    )
    
    # Main pipeline config
    config = PipelineConfig(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        market_type=args.market,
        feature_config=feature_config,
        model_configs=model_configs,
        validation_config=validation_config,
        deployment_config=deployment_config,
        output_dir=args.output_dir,
        save_intermediate_results=True,
        min_training_samples=100 if args.skip_training else 500
    )
    
    return config


def demo_feature_engineering(symbols, market_type="US"):
    """Demonstrate feature engineering capabilities"""
    
    print("\n=== Feature Engineering Demo ===")
    logger.info("Demonstrating feature engineering capabilities")
    
    try:
        from tradingagents.ml.feature_engineering import (
            TechnicalIndicatorEngine, FeatureConfig
        )
        from tradingagents.dataflows import get_YFin_data_window
        
        # Get sample data
        symbol = symbols[0]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        data = get_YFin_data_window(symbol, start_date, end_date)
        
        if data is None or data.empty:
            print(f"⚠️  No data available for {symbol}")
            return
        
        print(f"📊 Sample data for {symbol}: {len(data)} records")
        print(f"   Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
        
        # Demonstrate technical indicators
        config = FeatureConfig(normalize_features=False)  # Don't normalize for demo
        tech_engine = TechnicalIndicatorEngine(config)
        
        features = tech_engine.extract_features(data)
        
        print(f"🔧 Generated {len(features.columns)} technical indicators")
        print("   Sample features:")
        
        # Show sample features
        sample_features = features.columns[:10]
        for feature in sample_features:
            latest_value = features[feature].iloc[-1]
            if pd.notna(latest_value):
                print(f"     {feature}: {latest_value:.4f}")
        
        print(f"✅ Feature engineering demo completed for {symbol}")
        
    except Exception as e:
        print(f"❌ Feature engineering demo failed: {e}")
        logger.error(f"Feature engineering demo failed: {e}")


def demo_model_training(symbols, model_type="xgboost"):
    """Demonstrate model training capabilities"""
    
    print("\n=== Model Training Demo ===")
    logger.info(f"Demonstrating model training with {model_type}")
    
    try:
        from tradingagents.ml.models import create_model, ModelConfig
        import numpy as np
        import pandas as pd
        
        # Create dummy training data
        n_samples = 1000
        n_features = 20
        
        print(f"📦 Creating dummy training data: {n_samples} samples, {n_features} features")
        
        # Generate synthetic features
        np.random.seed(42)
        X = np.random.randn(n_samples, n_features)
        
        # Generate synthetic targets for different tasks
        tasks = {
            "price_prediction": np.random.normal(0, 0.02, n_samples),  # Returns
            "signal_classification": np.random.choice(["BUY", "HOLD", "SELL"], n_samples),
            "volatility_prediction": np.random.uniform(0.1, 0.5, n_samples),
            "risk_assessment": np.random.choice(["LOW", "MEDIUM", "HIGH"], n_samples)
        }
        
        # Train models for each task
        trained_models = {}
        
        for task_name, target in tasks.items():
            print(f"🤖 Training {model_type} model for {task_name}...")
            
            try:
                # Create model
                model = create_model(model_type, task_name)
                
                # Train model
                if hasattr(model, 'train'):
                    if task_name == "signal_classification":
                        # Convert string labels to pandas Series
                        target_series = pd.Series(target)
                        training_history = model.train(pd.DataFrame(X), target_series)
                    elif task_name == "risk_assessment":
                        # For risk assessment, need returns and volatility
                        returns = pd.Series(np.random.normal(0, 0.02, n_samples))
                        volatility = pd.Series(np.random.uniform(0.1, 0.5, n_samples))
                        training_history = model.train(pd.DataFrame(X), returns, volatility)
                    else:
                        training_history = model.train(pd.DataFrame(X), pd.Series(target))
                    
                    trained_models[task_name] = model
                    print(f"✅ {task_name} model training completed")
                    
                    # Show training metrics if available
                    if isinstance(training_history, dict) and 'train_score' in training_history:
                        print(f"     Train score: {training_history['train_score']:.4f}")
                    
                else:
                    print(f"⚠️  Model {model_type} does not support training for {task_name}")
                    
            except Exception as e:
                print(f"❌ Training failed for {task_name}: {e}")
                logger.error(f"Training failed for {task_name}: {e}")
        
        print(f"\n🎯 Successfully trained {len(trained_models)} models")
        
        # Demo predictions
        print("\n🔮 Testing predictions...")
        test_X = np.random.randn(5, n_features)  # 5 test samples
        
        for task_name, model in trained_models.items():
            try:
                if hasattr(model, 'predict'):
                    predictions = model.predict(pd.DataFrame(test_X))
                    print(f"   {task_name}: {predictions[:3] if hasattr(predictions, '__len__') else predictions}")
            except Exception as e:
                print(f"   {task_name}: Prediction failed - {e}")
        
    except Exception as e:
        print(f"❌ Model training demo failed: {e}")
        logger.error(f"Model training demo failed: {e}")


def demo_pipeline_components():
    """Demonstrate individual pipeline components"""
    
    print("\n=== Pipeline Components Demo ===")
    
    # Demo 1: Feature Engineering
    demo_feature_engineering(["AAPL", "MSFT"])
    
    # Demo 2: Model Training  
    demo_model_training(["AAPL", "MSFT"], "xgboost")
    
    print("\n✅ Pipeline components demo completed")


def run_full_pipeline_demo(config):
    """Run the complete ML pipeline demo"""
    
    print("\n=== Full ML Pipeline Demo ===")
    logger.info("Running complete ML pipeline demo")
    
    try:
        # Create ML pipeline
        print("🏗️  Creating ML pipeline...")
        pipeline = MLPipeline(config)
        
        print(f"📊 Pipeline configuration:")
        print(f"   Symbols: {config.symbols}")
        print(f"   Market: {config.market_type}")
        print(f"   Date range: {config.start_date} to {config.end_date}")
        print(f"   Models: {list(config.model_configs.keys())}")
        print(f"   Output directory: {config.output_dir}")
        
        # Run pipeline
        print("\n🚀 Running ML pipeline...")
        print("   This may take several minutes depending on data size and models...")
        
        results = pipeline.run_full_pipeline(config.symbols)
        
        # Display results summary
        print(f"\n📋 Pipeline Results Summary:")
        print(f"   Status: {results.get('status', 'unknown')}")
        print(f"   Duration: {results.get('duration_minutes', 0):.2f} minutes")
        
        if results.get('status') == 'completed':
            # Data results
            data_results = results.get('data_results', {})
            market_data = data_results.get('market_data', {})
            print(f"   Data ingested: {len(market_data)} symbols")
            
            for symbol, data in market_data.items():
                if hasattr(data, '__len__'):
                    print(f"     {symbol}: {len(data)} records")
            
            # Feature results
            feature_results = results.get('feature_results', {})
            features = feature_results.get('features', {})
            print(f"   Features generated: {len(features)} symbols")
            
            for symbol, feat_data in features.items():
                if hasattr(feat_data, 'shape'):
                    print(f"     {symbol}: {feat_data.shape[1]} features, {feat_data.shape[0]} samples")
            
            # Training results
            training_results = results.get('training_results', {})
            models = training_results.get('models', {})
            print(f"   Models trained: {sum(len(task_models) for task_models in models.values())}")
            
            for task, task_models in models.items():
                print(f"     {task}: {len(task_models)} models")
            
            # Validation results
            validation_results = results.get('validation_results', {})
            cv_results = validation_results.get('cross_validation', {})
            print(f"   Validation completed: {len(cv_results)} tasks")
            
            # Deployment results
            deployment_results = results.get('deployment_results', {})
            deployed_models = deployment_results.get('deployed_models', {})
            print(f"   Models deployed: {sum(len(task_deployments) for task_deployments in deployed_models.values())}")
            
            print("\n✅ Full pipeline demo completed successfully!")
            
            # Show pipeline status
            status = pipeline.get_pipeline_status()
            print(f"\n📊 Pipeline Status:")
            print(f"   Total runs: {status['total_runs']}")
            print(f"   Successful runs: {status['successful_runs']}")
            print(f"   Failed runs: {status['failed_runs']}")
            
        else:
            print(f"❌ Pipeline failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Full pipeline demo failed: {e}")
        logger.error(f"Full pipeline demo failed: {e}")
        return False
    
    return True


async def run_integration_demo(config):
    """Run ML integration with TradingAgents demo"""
    
    print("\n=== ML Integration Demo ===")
    logger.info("Running ML integration with TradingAgents demo")
    
    try:
        print("🤖 Creating ML-enhanced agents...")
        
        # Run integration demo
        demo_results = await demonstrate_ml_integration(config.symbols[:2])  # Use first 2 symbols
        
        if 'error' in demo_results:
            print(f"❌ Integration demo failed: {demo_results['error']}")
            return False
        
        print("✅ ML-enhanced agents created successfully!")
        
        # Show agent analysis results
        agent_analyses = demo_results.get('agent_analyses', {})
        print(f"\n📈 Agent Analysis Results:")
        
        for symbol, analysis in agent_analyses.items():
            if 'error' not in analysis:
                print(f"\n   {symbol}:")
                print(f"     Analysis type: {analysis.get('analysis_type', 'unknown')}")
                print(f"     Confidence: {analysis.get('confidence_score', 0):.2f}")
                
                # Show recommendations
                recommendations = analysis.get('recommendations', {})
                if recommendations:
                    action = recommendations.get('action', 'UNKNOWN')
                    reasoning = recommendations.get('reasoning', [])
                    print(f"     Recommended action: {action}")
                    if reasoning:
                        print(f"     Reasoning: {reasoning[0] if reasoning else 'None provided'}")
                
                # Show combined insights
                combined_insights = analysis.get('combined_insights', {})
                if combined_insights:
                    consensus = combined_insights.get('price_direction_consensus', 'unknown')
                    strength = combined_insights.get('consensus_strength', 'unknown')
                    print(f"     Price consensus: {consensus} ({strength})")
            else:
                print(f"   {symbol}: Analysis failed - {analysis['error']}")
        
        # Show chart results
        agent_charts = demo_results.get('agent_charts', {})
        print(f"\n📊 Chart Generation Results:")
        
        for symbol, chart in agent_charts.items():
            if 'error' not in chart:
                chart_type = chart.get('chart_type', 'unknown')
                market_data = chart.get('market_data', {})
                prices = market_data.get('prices', [])
                print(f"   {symbol}: {chart_type} chart with {len(prices)} price points")
                
                # Show ML overlays
                ml_overlays = chart.get('ml_overlays', {})
                if ml_overlays:
                    overlay_type = ml_overlays.get('type', 'unknown')
                    print(f"     ML overlay: {overlay_type}")
            else:
                print(f"   {symbol}: Chart generation failed - {chart['error']}")
        
        print("\n✅ ML integration demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Integration demo failed: {e}")
        logger.error(f"Integration demo failed: {e}")
        return False
    
    return True


def print_demo_summary(args, pipeline_success, integration_success):
    """Print demo summary"""
    
    print("\n" + "="*60)
    print("🎯 TRADINGAGENTS-CN ML PIPELINE DEMO SUMMARY")
    print("="*60)
    
    print(f"\n📊 Configuration:")
    print(f"   Symbols: {args.symbols}")
    print(f"   Market: {args.market}")
    print(f"   Data period: {args.days} days")
    print(f"   Model type: {args.model_type}")
    print(f"   Skip training: {args.skip_training}")
    print(f"   Output directory: {args.output_dir}")
    
    print(f"\n🏆 Results:")
    print(f"   Pipeline components demo: ✅ Completed")
    print(f"   Full ML pipeline: {'✅ Success' if pipeline_success else '❌ Failed'}")
    print(f"   ML integration demo: {'✅ Success' if integration_success else '❌ Failed'}")
    
    if pipeline_success:
        print(f"\n📁 Output files saved to: {args.output_dir}")
        print(f"   - Model files in: {args.output_dir}/models/")
        print(f"   - Pipeline results in: {args.output_dir}/")
    
    print(f"\n🚀 Next Steps:")
    if pipeline_success:
        print(f"   • Explore the generated model files and results")
        print(f"   • Integrate ML predictions into your trading strategy")
        print(f"   • Set up real-time model monitoring and retraining")
        if args.enable_deployment:
            print(f"   • Access the inference API at http://localhost:8080")
    else:
        print(f"   • Check the logs for error details")
        print(f"   • Try with different symbols or shorter time period")
        print(f"   • Use --skip-training for a faster demo")
    
    print(f"\n📚 Documentation:")
    print(f"   • Feature Engineering: tradingagents/ml/feature_engineering.py")
    print(f"   • Model Training: tradingagents/ml/models.py")
    print(f"   • Validation Framework: tradingagents/ml/validation.py")
    print(f"   • Deployment Pipeline: tradingagents/ml/deployment.py")
    print(f"   • Integration: tradingagents/ml/integration.py")
    
    print("\n" + "="*60)


def main():
    """Main demo function"""
    
    # Parse arguments
    args = parse_arguments()
    
    print("🎯 TradingAgents-CN ML Pipeline Demo")
    print("="*50)
    
    try:
        # Import pandas for error handling
        import pandas as pd
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        
        # Create pipeline configuration
        print("⚙️  Creating pipeline configuration...")
        config = create_demo_config(args)
        
        # Create output directory
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Output directory: {output_path.absolute()}")
        
        # Demo 1: Pipeline Components
        demo_pipeline_components()
        
        # Demo 2: Full Pipeline (optional)
        pipeline_success = False
        if not args.skip_training:
            pipeline_success = run_full_pipeline_demo(config)
        else:
            print("\n⏩ Skipping full pipeline training (--skip-training enabled)")
            pipeline_success = True  # Assume success for integration demo
        
        # Demo 3: ML Integration with TradingAgents
        integration_success = False
        if pipeline_success:
            integration_success = asyncio.run(run_integration_demo(config))
        
        # Print summary
        print_demo_summary(args, pipeline_success, integration_success)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\n💡 Please ensure all required packages are installed:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        logger.error(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()