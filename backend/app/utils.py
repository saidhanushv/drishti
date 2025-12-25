"""
Utility functions for logging, caching, and retry logic
"""
import logging
import time
from functools import wraps
from typing import Any, Callable
from datetime import datetime
from config import Config
from openai import OpenAI
import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class QueryLogger:
    """Logger for tracking queries, results, and errors"""
    
    @staticmethod
    def log_sql_query(query: str, result: Any = None, error: str = None):
        """Log SQL query execution"""
        timestamp = datetime.now().isoformat()
        
        if Config.LOG_QUERIES:
            logger.info(f"\n{'='*80}")
            logger.info(f"[SQL QUERY] Timestamp: {timestamp}")
            logger.info(f"Query:\n{query}")
            
            if error:
                logger.error(f"Error: {error}")
            elif result is not None:
                logger.info(f"Result: {result}")
            
            logger.info(f"{'='*80}\n")
    
    @staticmethod
    def log_rag_search(query: str, results: list, filters: dict = None):
        """Log RAG semantic search"""
        timestamp = datetime.now().isoformat()
        
        if Config.LOG_QUERIES:
            logger.info(f"\n{'='*80}")
            logger.info(f"[RAG SEARCH] Timestamp: {timestamp}")
            logger.info(f"Query: {query}")
            if filters:
                logger.info(f"Filters: {filters}")
            logger.info(f"Retrieved {len(results)} results")
            logger.info(f"{'='*80}\n")
    
    @staticmethod
    def log_ml_prediction(query: str, prediction: Any, model_info: str = None):
        """Log ML prediction"""
        timestamp = datetime.now().isoformat()
        
        if Config.LOG_QUERIES:
            logger.info(f"\n{'='*80}")
            logger.info(f"[ML PREDICTION] Timestamp: {timestamp}")
            logger.info(f"Query: {query}")
            if model_info:
                logger.info(f"Model: {model_info}")
            logger.info(f"Prediction: {prediction}")
            logger.info(f"{'='*80}\n")
    
    @staticmethod
    def log_agent_action(action: str, observation: str):
        """Log agent actions"""
        logger.info(f"\n[AGENT ACTION] {action}")
        logger.info(f"[OBSERVATION] {observation}\n")


def retry_with_backoff(max_retries: int = None, delay: float = None):
    """Decorator for retry logic with exponential backoff"""
    if max_retries is None:
        max_retries = Config.SQL_MAX_RETRIES
    if delay is None:
        delay = Config.SQL_RETRY_DELAY
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    wait_time = delay * (2 ** (retries - 1))  # Exponential backoff
                    logger.warning(f"Attempt {retries} failed: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator


class SimpleCache:
    """Simple in-memory cache for ML predictions and queries"""
    
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str) -> Any:
        """Get cached value"""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any):
        """Set cached value"""
        self.cache[key] = value
    
    def clear(self):
        """Clear all cached values"""
        self.cache.clear()
    
    def has(self, key: str) -> bool:
        """Check if key exists in cache"""
        return key in self.cache


# Global cache instance
cache = SimpleCache()


def generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """Generate a cache key from function name and arguments"""
    import hashlib
    import json
    
    # Create a string representation of args and kwargs
    key_data = {
        'func': func_name,
        'args': str(args),
        'kwargs': str(sorted(kwargs.items()))
    }
    
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


def timed_execution(func: Callable) -> Callable:
    """Decorator to measure execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(f"[TIMING] {func.__name__} executed in {execution_time:.2f}s")
        return result
    return wrapper


def parse_date_filter(query: str) -> dict:
    """Parse date/quarter filters from natural language query"""
    filters = {}
    query_lower = query.lower()
    
    # Check for quarter mentions
    quarters = {
        'q1': 'Q1', 'quarter 1': 'Q1', 'first quarter': 'Q1',
        'q2': 'Q2', 'quarter 2': 'Q2', 'second quarter': 'Q2',
        'q3': 'Q3', 'quarter 3': 'Q3', 'third quarter': 'Q3',
        'q4': 'Q4', 'quarter 4': 'Q4', 'fourth quarter': 'Q4'
    }
    
    for key, value in quarters.items():
        if key in query_lower:
            filters['Quarter'] = value
            break
    
    return filters


def format_dataframe_for_llm(df, max_rows: int = 10) -> str:
    """Format DataFrame for LLM consumption"""
    if len(df) == 0:
        return "No results found."
    
    # Limit rows
    df_display = df.head(max_rows)
    
    # Convert to string with better formatting
    result = f"Found {len(df)} total rows. Showing first {min(len(df), max_rows)}:\n\n"
    result += df_display.to_string(index=False)
    
    if len(df) > max_rows:
        result += f"\n\n... and {len(df) - max_rows} more rows"
    
    return result


# --- Tool usage tracking ---------------------------------------------------
class ToolUsageTracker:
    """Tracks which tool handled the latest query."""

    DEFAULT_MESSAGE = "INCUBATOR RESPONSE (NO TOOL USED)"

    def __init__(self):
        self.reset()

    def record(self, message: str):
        self._last_message = message

    def reset(self):
        self._last_message = self.DEFAULT_MESSAGE

    def get(self) -> str:
        return self._last_message


_tool_usage_tracker = ToolUsageTracker()


def record_tool_usage(message: str):
    _tool_usage_tracker.record(message)


def reset_tool_usage():
    _tool_usage_tracker.reset()


def get_tool_usage_status() -> str:
    return _tool_usage_tracker.get()


# --- OpenAI client factory ---
_http_client = None
_http_async_client = None
_openai_client = None


def get_httpx_client(async_mode: bool = False):
    """Return a singleton httpx client/async client."""
    global _http_client, _http_async_client
    if async_mode:
        if _http_async_client is None:
            # Use verify=False if needed, but standard OpenAI usually works with default.
            # Keeping verify=False as user might have specific env needs, but removing custom transport.
            _http_async_client = httpx.AsyncClient(verify=False, timeout=60.0)
        return _http_async_client
    else:
        if _http_client is None:
            _http_client = httpx.Client(verify=False, timeout=60.0)
        return _http_client


def get_openai_client() -> OpenAI:
    """Return a singleton OpenAI client."""
    global _openai_client
    if _openai_client is None:
        http_client = get_httpx_client()
        _openai_client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            http_client=http_client
        )
    return _openai_client