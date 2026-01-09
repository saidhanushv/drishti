"""
Text-to-SQL Tool for DuckDB query execution
"""
import duckdb
from typing import Optional
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from config import Config
from utils import (
    QueryLogger,
    retry_with_backoff,
    timed_execution,
    get_httpx_client,
    record_tool_usage,
)
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class SQLTool:
    """Tool for converting natural language to SQL and executing queries"""
    
    def __init__(self, conn: duckdb.DuckDBPyConnection, schema_description: str):
        self.conn = conn
        self.schema_description = schema_description
        # Create ChatOpenAI with standard OpenAI API
        http_client = get_httpx_client()
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=Config.LLM_TEMPERATURE,
            openai_api_key=Config.OPENAI_API_KEY,
            http_client=http_client
        )
        
        self.sql_prompt = PromptTemplate(
            input_variables=["schema", "question"],
            template="""You are a SQL expert. Generate a DuckDB SQL query to answer the question.

DATABASE SCHEMA:
{schema}

IMPORTANT RULES:
1. Generate ONLY the SQL query, no explanations
2. Use proper DuckDB syntax
3. For quarter calculations, use the Quarter column (Q1, Q2, Q3, Q4)
4. Always use aggregate functions properly with GROUP BY
5. Use proper JOIN syntax if needed
6. Return SELECT queries only (no INSERT, UPDATE, DELETE)
7. For comparisons, use proper WHERE clauses
8. Format numbers properly in output

QUESTION: {question}

SQL QUERY:"""
        )
    
    @retry_with_backoff()
    @timed_execution
    def execute_sql(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL query with retry logic"""
        try:
            result = self.conn.execute(sql_query).fetchdf()
            return result
        except Exception as e:
            logger.error(f"SQL execution error: {str(e)}")
            raise
    
    def generate_sql(self, question: str) -> str:
        """Generate SQL query from natural language"""
        prompt = self.sql_prompt.format(
            schema=self.schema_description,
            question=question
        )
        
        response = self.llm.invoke(prompt)
        sql_query = response.content.strip()
        
        # Clean up the SQL query
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        return sql_query
    
    def run(self, question: str) -> str:
        """Main execution method for the tool"""
        try:
            record_tool_usage("SQL TOOL USED")
            print("[TOOL] SQL TOOL USED")
            logger.info("[TOOL] SQL_Query invoked")
            # Generate SQL
            logger.info(f"Generating SQL for question: {question}")
            sql_query = self.generate_sql(question)
            
            logger.info(f"Generated SQL Query:\n{sql_query}")
            print(f"\n{'='*80}")
            print(f"[SQL QUERY]")
            print(f"{sql_query}")
            print(f"{'='*80}\n")
            
            # Execute SQL with retry
            result_df = self.execute_sql(sql_query)
            
            # Log results
            QueryLogger.log_sql_query(sql_query, result=result_df)
            
            # Format output
            # output = f"SQL Query:\n{sql_query}\n\n"
            output = ""
            
            if len(result_df) == 0:
                output += "No results found."
                print("[RESULT] No results found.\n")
            else:
                output += f"Results ({len(result_df)} rows):\n"
                output += result_df.to_string(index=False)
                
                print(f"[RESULT] Found {len(result_df)} rows:")
                print(result_df.to_string(index=False))
                print()
            
            return output
            
        except Exception as e:
            error_msg = f"Error executing SQL query: {str(e)}"
            logger.error(error_msg)
            QueryLogger.log_sql_query(
                sql_query if 'sql_query' in locals() else "N/A",
                error=str(e)
            )
            print(f"\n[ERROR] {error_msg}\n")
            return error_msg
    
    def as_tool(self) -> Tool:
        """Convert to LangChain Tool"""
        return Tool(
            name="SQL_Query",
            func=self.run,
            description="""Use this tool for analytical queries that require calculations, aggregations, or filtering by exact values.
            
Examples:
- "Calculate average Value_Uplift by Region"
- "Show top 10 promotions by Volume_Uplift"
- "What is the total sales in Q1?"
- "Compare RAG status distribution between Q1 and Q3"
- "Find all promotions in North region with Value_Uplift > 20%"
- Note that ROI_PromoID is the actual ROI%, do not use ROI% when you have to calculate ROI
CONSTRAINTS:
- Do not display anything in a tabular format. If the output is similar to this-
 promotions_2025  avg_uplift_pct  avg_uplift_promoid_pct  weighted_uplift_pct  total_actual_promo_sales_value  total_baseline_sales_value
            1077           34.16                   42.65                 4.17                      1119261.62           
       1074423.42
  Then provide the answer in key value format-
  promotions_2025: 1077
  avg_uplift_pct: 34.16
  avg_uplift_promoid_pct: 42.65
  weighted_uplift_pct: 4.17
  total_actual_promo_sales_value: 1119261.62
  total_baseline_sales_value: 1074423.42

This tool generates and executes SQL queries on the DuckDB database.
Input should be a natural language question about the data."""
        )


if __name__ == "__main__":
    # Test the SQL tool
    from data_loader import DataLoader
    
    loader = DataLoader("downloads/part-00000-tid-8397012257644732603-1200992a-2c19-4df8-a301-752e4b275d40-52-1-c000.csv")
    conn, _, _ = loader.initialize()
    schema = loader.get_schema_description()
    
    sql_tool = SQLTool(conn, schema)
    result = sql_tool.run("What is the average Value_Uplift by Region?")
    print(result)