"""
ML Tool for predictive analytics and what-if scenarios
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from config import Config
from utils import (
    QueryLogger,
    cache,
    generate_cache_key,
    timed_execution,
    get_httpx_client,
    record_tool_usage,
)
import logging

logger = logging.getLogger(__name__)


class MLTool:
    """Tool for ML predictions and statistical analysis"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        # Create ChatOpenAI with standard OpenAI API
        http_client = get_httpx_client()
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=Config.LLM_TEMPERATURE,
            openai_api_key=Config.OPENAI_API_KEY,
            http_client=http_client
        )
        
        self.analysis_prompt = PromptTemplate(
            input_variables=["query", "data_summary"],
            template="""You are an expert data scientist. Analyze the following data and answer the user's prediction question.

USER QUESTION: {query}

DATA SUMMARY:
{data_summary}
- Note that ROI_PromoID is the actual ROI%, do not use ROI% when you have to calculate ROI

Based on this data, provide:
1. Direct answer to the prediction question
2. Statistical reasoning
3. Confidence level and caveats
4. Specific recommendations

ANALYSIS:"""
        )
        
        self.scenario_extraction_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Extract the scenario parameters from this what-if question. Return in format: Region=X, Customer=Y, etc.

QUESTION: {query}

EXTRACTED PARAMETERS (comma-separated key=value pairs):"""
        )
    
    def _get_statistical_summary(self, filters: Optional[Dict] = None) -> str:
        """Get statistical summary of data"""
        df_filtered = self.df.copy()
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if key in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered[key] == value]
        
        if len(df_filtered) == 0:
            return "No data matching the specified criteria."
        
        # Get numeric columns
        numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
        
        summary = f"Data Summary ({len(df_filtered)} rows):\n\n"
        
        # Calculate statistics for key metrics
        for col in numeric_cols:
            if 'Uplift' in col or 'Sales' in col or 'ROI' in col:
                stats = df_filtered[col].describe()
                summary += f"\n{col}:\n"
                summary += f"  Mean: {stats['mean']:.2f}\n"
                summary += f"  Median: {stats['50%']:.2f}\n"
                summary += f"  Std Dev: {stats['std']:.2f}\n"
                summary += f"  Min: {stats['min']:.2f}, Max: {stats['max']:.2f}\n"
        
        return summary
    
    def _statistical_prediction(self, query: str, scenario: Dict) -> str:
        """Perform statistical prediction without ML training"""
        logger.info("Performing statistical analysis (no ML training required)")
        
        # Get data summary for similar promotions
        data_summary = self._get_statistical_summary(scenario)
        
        # Use LLM for interpretation
        prompt = self.analysis_prompt.format(
            query=query,
            data_summary=data_summary
        )
        
        analysis = self.llm.invoke(prompt).content
        
        return f"STATISTICAL ANALYSIS:\n{analysis}\n\nBASED ON:\n{data_summary}"
    
    @timed_execution
    def _ml_prediction(self, query: str, scenario: Dict, target_variable: str) -> str:
        """Perform ML prediction with AutoML"""
        logger.info(f"Starting ML model training for target: {target_variable}")
        print(f"\n{'='*80}")
        print(f"[ML TRAINING] Training AutoML model for prediction...")
        print(f"Target Variable: {target_variable}")
        print(f"This may take 5-15 minutes. Please wait...")
        print(f"{'='*80}\n")
        
        try:
            from flaml import AutoML
            
            # Prepare data
            df_clean = self.df.copy()
            
            # Select features and target
            # Exclude non-predictive columns
            exclude_cols = ['Start_Prom', 'End_Prom', target_variable]
            feature_cols = [col for col in df_clean.columns if col not in exclude_cols]
            
            # Handle categorical variables
            categorical_cols = df_clean[feature_cols].select_dtypes(include=['object']).columns.tolist()
            
            category_mappings = {}
            for col in categorical_cols:
                cat_series = df_clean[col].astype('category')
                categories = list(cat_series.cat.categories)
                category_mappings[col] = {cat: idx for idx, cat in enumerate(categories)}
                df_clean[col] = cat_series.cat.codes
            
            # Remove rows with missing target
            df_clean = df_clean.dropna(subset=[target_variable])
            
            X = df_clean[feature_cols]
            y = df_clean[target_variable]
            X = X.fillna(X.mean())
            
            # Train AutoML model
            automl = AutoML()
            
            print("[ML TRAINING] Fitting model... (this will take several minutes)")
            
            automl.fit(
                X, y,
                task="regression",
                time_budget=Config.ML_TRAINING_TIMEOUT,
                metric="r2",
                verbose=0
            )
            
            print(f"[ML TRAINING] Training complete!")
            print(f"Best model: {automl.best_estimator}")
            print(f"R2 Score: {automl.best_loss:.4f}\n")
            
            # Make prediction for scenario
            # Convert scenario to feature vector
            scenario_df = pd.DataFrame([scenario]) if scenario else pd.DataFrame([{}])
            
            for col in categorical_cols:
                if col in scenario_df.columns:
                    scenario_df[col] = scenario_df[col].apply(
                        lambda val: category_mappings[col].get(val, -1)
                    )
                else:
                    scenario_df[col] = -1
            
            # Ensure all features are present and numeric
            for col in feature_cols:
                if col not in scenario_df.columns:
                    scenario_df[col] = X[col].mean()
                else:
                    if scenario_df[col].dtype == object:
                        scenario_df[col] = pd.to_numeric(scenario_df[col], errors='coerce')
                    scenario_df[col] = scenario_df[col].fillna(X[col].mean())
            
            scenario_df = scenario_df[feature_cols]
            prediction = automl.predict(scenario_df)
            
            result = f"""ML PREDICTION RESULTS:

Model: {automl.best_estimator}
R2 Score: {automl.best_loss:.4f}

Scenario: {scenario}
Predicted {target_variable}: {prediction[0]:.2f}

Model Interpretation:
The AutoML model analyzed {len(df_clean)} historical promotions and identified the best predictive model.
This prediction is based on patterns learned from similar promotions in the dataset.
"""
            
            QueryLogger.log_ml_prediction(query, prediction[0], f"{automl.best_estimator}")
            
            return result
            
        except ImportError:
            logger.error("FLAML not installed. Install with: pip install flaml")
            return "Error: AutoML library (FLAML) not installed. Please install it first."
        except Exception as e:
            logger.error(f"ML training error: {str(e)}")
            return f"Error during ML training: {str(e)}\n\nFalling back to statistical analysis..."
    
    def _extract_scenario(self, query: str) -> Dict:
        """Extract scenario parameters from query"""
        prompt = self.scenario_extraction_prompt.format(query=query)
        response = self.llm.invoke(prompt).content.strip()
        
        # Parse the response
        scenario = {}
        try:
            pairs = response.split(',')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.strip().split('=', 1)
                    scenario[key.strip()] = value.strip()
        except:
            logger.warning("Could not parse scenario parameters")
        
        return scenario

    def _normalize_scenario(self, scenario: Dict) -> Dict:
        """Normalize scenario keys to match dataframe columns and cast values when possible."""
        if not scenario:
            return {}
        
        column_map = {col.lower(): col for col in self.df.columns}
        normalized = {}
        for key, value in scenario.items():
            if value is None:
                continue
            column_name = column_map.get(key.lower())
            if not column_name:
                continue
            value_str = str(value).strip()
            # Attempt numeric conversion
            try:
                normalized[column_name] = float(value_str)
                continue
            except ValueError:
                pass
            normalized[column_name] = value_str
        return normalized
    
    def _detect_target_variable(self, query: str) -> Optional[str]:
        """Detect which variable to predict based on query"""
        query_lower = query.lower()
        
        # Check for explicit mentions
        target_preferences = [
            (
                ['value uplift', 'value_uplift'],
                [
                    'Actual_Promo_Sales_Value_Uplift_%',
                    'Planned_Promo_Sales_Value_Uplift_%',
                    'Actual_Promo_Sales_Value_Uplift_PromoID_%',
                ],
            ),
            (
                ['volume uplift', 'volume_uplift'],
                [
                    'Actual_Promo_Sales_Volume_Uplift',
                    'Planned_Promo_Sales_Volume_Uplift',
                ],
            ),
            (
                ['roi'],
                ['ROI%', 'ROI%_PromoID', 'Planned_ROI%'],
            ),
            (
                ['gross profit', 'profit'],
                ['Gross_Profit', 'Planned_Gross_Profit'],
            ),
            (
                ['sales'],
                ['Predicted_Sales', 'Sales_Value', 'Actual_Sales_Value'],
            ),
        ]

        for keywords, columns in target_preferences:
            if any(keyword in query_lower for keyword in keywords):
                for column in columns:
                    if column in self.df.columns:
                        return column

        fallback_order = [
            'Actual_Promo_Sales_Value_Uplift_%',
            'Actual_Promo_Sales_Volume_Uplift',
            'ROI%',
            'Predicted_Sales',
        ]
        for column in fallback_order:
            if column in self.df.columns:
                return column

        return None
    
    def _is_simple_query(self, query: str) -> bool:
        """Determine if query is simple enough for statistical analysis"""
        query_lower = query.lower()
        
        # If query explicitly asks for prediction/forecast, use ML
        prediction_keywords = ['predict', 'forecast', 'what would', 'what will', 'expected']
        if any(keyword in query_lower for keyword in prediction_keywords):
            return False  # Use AutoML
        
        # Otherwise check for simple statistical keywords
        simple_keywords = [
            'average', 'mean', 'typical', 'usual', 'normal',
            'similar to', 'like', 'comparable', 'historical'
        ]
        
        return any(keyword in query_lower for keyword in simple_keywords)
    
    def run(self, query: str) -> str:
        """Main execution method for the tool"""
        try:
            record_tool_usage("ML TOOL USED")
            print("[TOOL] ML TOOL USED")
            logger.info("[TOOL] ML_Prediction invoked")
            logger.info(f"Processing ML/prediction query: {query}")
            
            # Check cache first
            cache_key = generate_cache_key("ml_prediction", query)
            if Config.ML_CACHE_ENABLED and cache.has(cache_key):
                logger.info("Returning cached prediction")
                return cache.get(cache_key)
            
            # Extract scenario parameters
            raw_scenario = self._extract_scenario(query)
            scenario = self._normalize_scenario(raw_scenario)
            logger.info(f"Extracted scenario: {scenario}")
            
            # Determine if simple or complex query
            is_simple = self._is_simple_query(query)
            
            if is_simple:
                # Use statistical analysis
                result = self._statistical_prediction(query, scenario)
            else:
                # Detect target variable
                target_var = self._detect_target_variable(query)
                
                if not target_var:
                    logger.warning("Could not detect target variable, using statistical analysis")
                    result = self._statistical_prediction(query, scenario)
                else:
                    # Use ML prediction
                    result = self._ml_prediction(query, scenario, target_var)
            
            # Cache result
            if Config.ML_CACHE_ENABLED:
                cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            error_msg = f"Error during ML prediction: {str(e)}"
            logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}\n")
            return error_msg
    
    def as_tool(self) -> Tool:
        """Convert to LangChain Tool"""
        return Tool(
            name="ML_Prediction",
            func=self.run,
            description="""Use this tool for predictive analytics, forecasting, and what-if scenario analysis.

Examples:
- "Predict Value_Uplift for a promotion in North region with Customer X"
- "How would a promotion perform in South region similar to our best Q1 campaign?"
- "Forecast the expected ROI for electronics category in Q4"
- "What would be the typical uplift for a promotion with these characteristics?"

This tool uses statistical analysis for simple queries and trains AutoML models for complex predictions.
Input should be a natural language question about predictions or what-if scenarios."""
        )


if __name__ == "__main__":
    # Test the ML tool
    import pandas as pd
    
    df = pd.read_csv("downloads/part-00000-tid-8397012257644732603-1200992a-2c19-4df8-a301-752e4b275d40-52-1-c000.csv")
    ml_tool = MLTool(df)
    result = ml_tool.run("What would be the typical Value_Uplift for a promotion in North region?")
    print(result)