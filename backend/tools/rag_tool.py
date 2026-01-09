"""
RAG Tool for semantic search and retrieval
"""
from typing import Optional, Dict, List
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from config import Config
from utils import (
    QueryLogger,
    parse_date_filter,
    timed_execution,
    get_httpx_client,
    record_tool_usage,
)
import logging

logger = logging.getLogger(__name__)


class RAGTool:
    """Tool for semantic search using embeddings"""
    
    def __init__(self, vectorstore: FAISS):
        self.vectorstore = vectorstore
        # Create ChatOpenAI with standard OpenAI API
        http_client = get_httpx_client()
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=Config.LLM_TEMPERATURE,
            openai_api_key=Config.OPENAI_API_KEY,
            http_client=http_client
        )
        
        self.interpretation_prompt = PromptTemplate(
            input_variables=["query", "results"],
            template="""You are an expert analyst. Based on the semantic search results, provide insights to answer the user's question.

USER QUESTION: {query}

RETRIEVED DATA:
{results}

Provide a clear, concise analysis based on these results. Focus on:
1. Direct answer to the question
2. Key patterns or trends
3. Notable observations
4. Specific examples from the data

ANALYSIS:"""
        )
    
    @timed_execution
    def search_with_filters(self, query: str, filters: Optional[Dict] = None, k: int = None) -> List:
        """Perform semantic search with metadata filtering"""
        if k is None:
            k = Config.TOP_K_RESULTS
        
        if filters:
            # Filter-aware search
            logger.info(f"Searching with filters: {filters}")
            
            # Get all documents and filter manually (FAISS doesn't support complex filtering natively)
            all_docs = self.vectorstore.similarity_search(query, k=k*3)  # Retrieve more to account for filtering
            
            filtered_docs = []
            for doc in all_docs:
                match = True
                for key, value in filters.items():
                    if key in doc.metadata and doc.metadata[key] != value:
                        match = False
                        break
                
                if match:
                    filtered_docs.append(doc)
                
                if len(filtered_docs) >= k:
                    break
            
            return filtered_docs
        else:
            # Standard similarity search
            return self.vectorstore.similarity_search(query, k=k)
    
    def format_results(self, docs: List) -> str:
        """Format retrieved documents for LLM"""
        if not docs:
            return "No matching results found."
        
        formatted = ""
        for i, doc in enumerate(docs, 1):
            formatted += f"\n--- Result {i} ---\n"
            formatted += f"Content: {doc.page_content}\n"
            
            if doc.metadata:
                formatted += "Metadata: "
                metadata_str = ", ".join([f"{k}={v}" for k, v in doc.metadata.items() if v is not None])
                formatted += metadata_str + "\n"
        
        return formatted
    
    def run(self, query: str) -> str:
        """Main execution method for the tool"""
        try:
            record_tool_usage("RAG TOOL USED")
            print("[TOOL] RAG TOOL USED")
            logger.info("[TOOL] Semantic_Search invoked")
            logger.info(f"Performing semantic search for: {query}")
            
            # Parse date/quarter filters from query
            filters = parse_date_filter(query)
            
            if filters:
                logger.info(f"Applying filters: {filters}")
                print(f"\n{'='*80}")
                print(f"[RAG SEARCH] Applying filters: {filters}")
                print(f"{'='*80}\n")
            
            # Perform search
            docs = self.search_with_filters(query, filters)
            
            # Log search
            QueryLogger.log_rag_search(query, docs, filters)
            
            if not docs:
                return "No relevant results found for your query."
            
            # Format results
            formatted_results = self.format_results(docs)
            
            print(f"\n{'='*80}")
            print(f"[RAG RESULTS] Retrieved {len(docs)} relevant promotions")
            print(f"{'='*80}\n")
            
            # Get LLM interpretation
            prompt = self.interpretation_prompt.format(
                query=query,
                results=formatted_results
            )
            
            interpretation = self.llm.invoke(prompt).content
            
            # Combine results with interpretation
            output = interpretation
            
            print(f"[ANALYSIS]\n{interpretation}\n")
            
            return output
            
        except Exception as e:
            import traceback
            error_msg = f"Error during semantic search: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"\n[ERROR] {error_msg}\n")
            print(f"[TRACEBACK] {traceback.format_exc()}\n")
            return error_msg
    
    def as_tool(self) -> Tool:
        """Convert to LangChain Tool"""
        return Tool(
            name="Semantic_Search",
            func=self.run,
            description="""Use this tool for semantic search and finding similar promotions based on descriptions, patterns, or fuzzy matching.

Examples:
- "Find promotions similar to high-performing campaigns in electronics"
- "Show promotions with customer feedback mentioning dissatisfaction"
- "What promotions in Q3 had characteristics similar to successful Q1 campaigns?"
- "Find promotions in North region with high uplift"
- "Show me promotions with Green RAG status"
- Note that ROI_PromoID is the actual ROI%, do not use ROI% when you have to calculate ROI

CONSTRAINTS-
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
  If there are multiple key value pairs in 1 point, then make that a bullet point and have multiple key value pairs under that

This tool performs semantic search on embedded promotion data and provides LLM-powered interpretation.
Input should be a natural language query about finding similar or matching promotions."""
        )


if __name__ == "__main__":
    # Test the RAG tool
    from data_loader import DataLoader
    
    loader = DataLoader("downloads\part-00000-tid-8397012257644732603-1200992a-2c19-4df8-a301-752e4b275d40-52-1-c000.csv")
    _, vectorstore, _ = loader.initialize()
    
    rag_tool = RAGTool(vectorstore)
    result = rag_tool.run("Find promotions in Q1 with high Value_Uplift")
    print(result)