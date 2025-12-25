"""
Configuration file for the FMCG Promotion Analysis Agent
"""
import os
from typing import List, Optional



# Ensure environment variables from .env are loaded regardless of CWD
try:
    from dotenv import load_dotenv, find_dotenv
    # 1) Explicitly load backend/.env (same directory as this file)
    current_dir = os.path.dirname(__file__)
    local_env_path = os.path.join(current_dir, ".env")
    if os.path.exists(local_env_path):
        load_dotenv(dotenv_path=local_env_path, override=False)
    # 2) Fallback: search upwards for any .env
    load_dotenv(find_dotenv(), override=False)
except Exception:
    # dotenv is optional at runtime; if unavailable, continue with system env
    pass

class Config:
    """Configuration class for the agent system"""
    
    # OpenAI API Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Azure Storage Configuration
    AZURE_STORAGE_ACCOUNT_NAME: str = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_STORAGE_ACCOUNT_KEY: str = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
    AZURE_STORAGE_CONTAINER_NAME: str = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "")
    AZURE_STORAGE_DIRECTORY: str = os.getenv("AZURE_STORAGE_DIRECTORY", "")
    
    # Model Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    LLM_TEMPERATURE: float = 0.0  # Deterministic for analytical queries
    
    # Vector Store Configuration
    VECTOR_STORE_TYPE: str = "faiss"  # Options: faiss, chroma
    FAISS_INDEX_PATH: str = "./faiss_index"
    TOP_K_RESULTS: int = 10  # Industry standard for 15K rows
    
    # DuckDB Configuration
    DUCKDB_PATH: str = "./promotion_data.duckdb"
    TABLE_NAME: str = "promotions"
    
    # Date Columns for Quarter Calculation
    DATE_COLUMNS: List[str] = ["Start_Prom", "End_Prom", "Start_Seas", "End_Seas"]
    WEEK_COLUMN: str = "Week"
    
    # Embedding Configuration
    # Leave empty to embed all columns, or specify columns to embed
    COLUMNS_TO_EMBED: Optional[List[str]] = None  # None = embed all columns
    EMBEDDING_CHUNK_SIZE: int = 100  # Number of documents to embed per API call (to stay under 300k token limit)
    
    # SQL Retry Configuration
    SQL_MAX_RETRIES: int = 5
    SQL_RETRY_DELAY: float = 1.0  # seconds
    
    # ML Configuration
    ML_TRAINING_TIMEOUT: int = 900  # 15 minutes max
    ML_CACHE_ENABLED: bool = True
    AUTO_ML_LIBRARY: str = "flaml"  # Options: flaml, autosklearn
    
    # Logging Configuration
    LOG_QUERIES: bool = True
    LOG_RESULTS: bool = True
    LOG_ERRORS: bool = True
    LOG_FILE: str = "./agent_logs.txt"
    
    # Agent Configuration
    AGENT_TYPE: str = "react"  # ReAct agent
    MAX_ITERATIONS: int = 10
    AGENT_VERBOSE: bool = True
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
        # Warn if Azure creds are missing but don't fail hard unless necessary
        if not all([cls.AZURE_STORAGE_ACCOUNT_NAME, cls.AZURE_STORAGE_ACCOUNT_KEY, cls.AZURE_STORAGE_CONTAINER_NAME]):
            print("WARNING: Azure Storage credentials missing. ADLS features will be disabled.")
            
        return True
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """Returns the system prompt with schema information"""
        return """You are an expert FMCG Promotion Analysis Assistant.

DATASET INFORMATION:
- This is a promotion dataset for an FMCG company
- Contains ~15,000 rows of historical promotion data
- Includes 50+ KPIs including baseline sales, predicted sales, value/volume uplift, RAG status, etc.

DATE COLUMNS:
- Start_Prom: Promotion start date
- End_Prom: Promotion end date
- Week: Week number (used to calculate quarters: Q1=Weeks 1-13, Q2=14-26, Q3=27-39, Q4=40-52)

AVAILABLE TOOLS:
1. SQL_Query: For calculations, aggregations, filtering (e.g., "average sales by region", "top 10 promotions")
2. Semantic_Search: For fuzzy matching, finding similar promotions (e.g., "promotions similar to X", "high-performing campaigns")
3. ML_Prediction: For forecasting or what-if scenarios (e.g., "predict promotion performance in Region A")

INSTRUCTIONS:
- Always consider the query type before selecting a tool
- For date-based queries, use the Week column to calculate quarters
- For complex queries, you may chain multiple tools
- When using SQL, always request to see the generated query and results
"""