"""
Main entry point for the FMCG Promotion Analysis Agent
"""
import sys
import os
from typing import Optional
from config import Config
from data_loader import DataLoader
from tools.sql_tool import SQLTool
from tools.rag_tool import RAGTool
from tools.ml_tool import MLTool
from agent import PromotionAnalysisAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromotionAnalysisSystem:
    """Main system orchestrator"""
    
    def __init__(self, csv_path: str, force_rebuild: bool = False):
        self.csv_path = csv_path
        self.force_rebuild = force_rebuild
        
        # Components
        self.loader = None
        self.conn = None
        self.vectorstore = None
        self.df = None
        self.agent = None
        
        # Validate configuration
        Config.validate()
    
    def initialize(self):
        """Initialize all components"""
        print("\n" + "="*80)
        print("🚀 INITIALIZING FMCG PROMOTION ANALYSIS SYSTEM")
        print("="*80 + "\n")
        
        # Step 1: Load data
        print("📊 Step 1/4: Loading data...")
        self.loader = DataLoader(self.csv_path, Config)
        self.conn, self.vectorstore, self.df = self.loader.initialize(
            force_rebuild=self.force_rebuild
        )
        print("✅ Data loaded successfully!\n")
        
        # Step 2: Get schema
        print("📋 Step 2/4: Analyzing schema...")
        schema_description = self.loader.get_schema_description()
        print(f"Schema:\n{schema_description}\n")
        
        # Step 3: Create tools
        print("🔧 Step 3/4: Setting up tools...")
        
        sql_tool = SQLTool(self.conn, schema_description)
        rag_tool = RAGTool(self.vectorstore)
        ml_tool = MLTool(self.df)
        
        tools = [
            sql_tool.as_tool(),
            rag_tool.as_tool(),
            ml_tool.as_tool()
        ]
        
        print(f"✅ Created {len(tools)} tools: SQL_Query, Semantic_Search, ML_Prediction\n")
        
        # Step 4: Create agent
        print("🤖 Step 4/4: Initializing ReAct Agent...")
        self.agent = PromotionAnalysisAgent(tools, schema_description)
        print("✅ Agent ready!\n")
        
        print("="*80)
        print("✨ SYSTEM INITIALIZATION COMPLETE")
        print("="*80 + "\n")
    
    def query(self, question: str) -> dict:
        """Execute a query"""
        if not self.agent:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        return self.agent.query(question)
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("\n" + "="*80)
        print("💬 INTERACTIVE MODE")
        print("="*80)
        print("Enter your questions about the promotion data.")
        print("Type 'exit' or 'quit' to stop.\n")
        
        while True:
            try:
                question = input("\n🔍 Your question: ").strip()
                
                if question.lower() in ['exit', 'quit', 'q', ""]:
                    print("\n👋 Goodbye!")
                    break
                
                if not question:
                    continue
                
                # Execute query
                result = self.query(question)
                
                # Show tool usage
                tool_usage = self.agent.get_tool_usage_summary(result)
                print(f"\n📊 Tool Usage Summary:")
                for tool, count in tool_usage.items():
                    if count > 0:
                        print(f"  - {tool}: {count} time(s)")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                print(f"\n❌ Error: {str(e)}\n")
    
    def batch_queries(self, queries: list):
        """Execute multiple queries in batch"""
        print("\n" + "="*80)
        print("📦 BATCH MODE")
        print(f"Processing {len(queries)} queries...")
        print("="*80 + "\n")
        
        results = []
        for i, query in enumerate(queries, 1):
            print(f"\n[Query {i}/{len(queries)}]")
            result = self.query(query)
            results.append({
                'query': query,
                'result': result
            })
        
        return results


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="FMCG Promotion Analysis Agent with ReAct (auto-detects CSV in ../downloads)"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild of DuckDB and embeddings"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to execute (non-interactive mode)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="Path to file containing queries (one per line)"
    )
    
    args = parser.parse_args()
    
    # Always auto-detect a CSV in downloads/ relative to this file's directory
    backend_dir = os.path.dirname(__file__)
    downloads_dir = os.path.normpath(os.path.join(backend_dir, "downloads"))
    try:
        candidates = [
            os.path.join(downloads_dir, f)
            for f in os.listdir(downloads_dir)
            if f.lower().endswith(".csv")
        ] if os.path.isdir(downloads_dir) else []
    except Exception:
        candidates = []
    if candidates:
        candidates.sort()
        resolved_csv_path = candidates[0]
    else:
        print("❌ Error: No CSV found in downloads/ relative to backend/main.py.")
        sys.exit(1)
    
    # Initialize system
    system = PromotionAnalysisSystem(resolved_csv_path, force_rebuild=args.rebuild)
    system.initialize()
    
    # Execute based on mode
    if args.query:
        # Single query mode
        result = system.query(args.query)
        print(f"\nFinal Answer:\n{result['output']}")
    
    elif args.batch:
        # Batch mode
        if not os.path.exists(args.batch):
            print(f"❌ Error: Batch file not found: {args.batch}")
            sys.exit(1)
        
        with open(args.batch, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
        
        results = system.batch_queries(queries)
        
        # Save results
        output_file = "batch_results.txt"
        with open(output_file, 'w') as f:
            for item in results:
                f.write(f"Query: {item['query']}\n")
                f.write(f"Answer: {item['result']['output']}\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"\n✅ Results saved to {output_file}")
    
    else:
        # Interactive mode
        system.interactive_mode()


if __name__ == "__main__":
    main()