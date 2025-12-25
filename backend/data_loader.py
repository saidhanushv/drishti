"""
Data loader for CSV to DuckDB and FAISS embeddings
"""
import pandas as pd
import duckdb
import numpy as np
from typing import List, Optional, Dict
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from config import Config
import logging
from openai import OpenAI
import httpx
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Handles CSV loading, DuckDB ingestion, and embedding generation"""
    
    def __init__(self, csv_path: str, config: Config = Config):
        self.csv_path = csv_path
        self.config = config
        self.conn = None
        self.df = None
        
        # Standard OpenAI client
        from utils import get_httpx_client
        http_client = get_httpx_client()
        
        # Set chunk_size to avoid exceeding token limits
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            http_client=http_client,
            chunk_size=config.EMBEDDING_CHUNK_SIZE,
            max_retries=3
        )
        self.vectorstore = None
        
    def load_csv(self) -> pd.DataFrame:
        """Load CSV file into pandas DataFrame"""
        logger.info(f"Loading CSV from {self.csv_path}...")
        self.df = pd.read_csv(self.csv_path)
        logger.info(f"Loaded {len(self.df)} rows and {len(self.df.columns)} columns")
        logger.info(f"Columns: {list(self.df.columns)}")
        return self.df
    
    def create_duckdb(self) -> duckdb.DuckDBPyConnection:
        """Create DuckDB database and load data"""
        logger.info(f"Creating DuckDB at {self.config.DUCKDB_PATH}...")
        
        # Remove existing database if present
        if os.path.exists(self.config.DUCKDB_PATH):
            os.remove(self.config.DUCKDB_PATH)
        
        self.conn = duckdb.connect(self.config.DUCKDB_PATH)
        
        # Create table from DataFrame
        # Register the in-memory DataFrame as a DuckDB relation
        self.conn.register("df", self.df)
        self.conn.execute(f"""
            CREATE TABLE {self.config.TABLE_NAME} AS 
            SELECT * FROM df
        """)
        
        # Add quarter calculation column
        logger.info("Adding Quarter column based on Week...")
        self.conn.execute(f"""
            ALTER TABLE {self.config.TABLE_NAME} 
            ADD COLUMN Quarter VARCHAR
        """)
        
        self.conn.execute(f"""
            UPDATE {self.config.TABLE_NAME}
            SET Quarter = CASE
                WHEN EXTRACT(WEEK FROM STRPTIME({self.config.WEEK_COLUMN}, '%d-%m-%Y')) BETWEEN 1 AND 13 THEN 'Q1'
                WHEN EXTRACT(WEEK FROM STRPTIME({self.config.WEEK_COLUMN}, '%d-%m-%Y')) BETWEEN 14 AND 26 THEN 'Q2'
                WHEN EXTRACT(WEEK FROM STRPTIME({self.config.WEEK_COLUMN}, '%d-%m-%Y')) BETWEEN 27 AND 39 THEN 'Q3'
                WHEN EXTRACT(WEEK FROM STRPTIME({self.config.WEEK_COLUMN}, '%d-%m-%Y')) BETWEEN 40 AND 52 THEN 'Q4'
                ELSE 'Unknown'
            END
        """)
        
        # Verify data
        row_count = self.conn.execute(
            f"SELECT COUNT(*) FROM {self.config.TABLE_NAME}"
        ).fetchone()[0]
        logger.info(f"DuckDB table '{self.config.TABLE_NAME}' created with {row_count} rows")
        
        return self.conn
    
    def get_schema_description(self) -> str:
        """Generate schema description for LLM"""
        schema_info = self.conn.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{self.config.TABLE_NAME}'
        """).fetchall()
        
        schema_desc = f"Table: {self.config.TABLE_NAME}\nColumns:\n"
        for col_name, col_type in schema_info:
            schema_desc += f"  - {col_name} ({col_type})\n"
        
        return schema_desc
    
    def _prepare_text_for_embedding(self, row: pd.Series, columns: Optional[List[str]] = None) -> str:
        """Prepare row text for embedding"""
        if columns is None:
            columns = self.df.columns.tolist()
        
        # Create text representation of the row
        text_parts = []
        for col in columns:
            value = row[col]
            # Handle different data types
            if pd.isna(value):
                continue
            elif isinstance(value, (int, float)):
                text_parts.append(f"{col}: {value}")
            else:
                text_parts.append(f"{col}: {str(value)}")
        
        return " | ".join(text_parts)
    
    def _prepare_metadata(self, row: pd.Series, index: int) -> Dict:
        """Prepare metadata for filtering"""
        metadata = {"row_index": index}
        
        # Add date columns if present
        for date_col in self.config.DATE_COLUMNS:
            if date_col in row.index:
                metadata[date_col] = str(row[date_col])
        
        # Add week and quarter
        if self.config.WEEK_COLUMN in row.index:
            week_value = row[self.config.WEEK_COLUMN]
            week_number = None
            if not pd.isna(week_value):
                # Try interpret as date and extract ISO week number; fallback to numeric
                dt_val = pd.to_datetime(week_value, format="%d-%m-%Y", errors="coerce")
                if not pd.isna(dt_val):
                    week_number = int(dt_val.isocalendar().week)
                else:
                    try:
                        week_number = int(week_value)
                    except Exception:
                        week_number = None

            metadata["Week"] = week_number
            
            # Calculate quarter
            week = metadata["Week"]
            if week:
                if 1 <= week <= 13:
                    metadata["Quarter"] = "Q1"
                elif 14 <= week <= 26:
                    metadata["Quarter"] = "Q2"
                elif 27 <= week <= 39:
                    metadata["Quarter"] = "Q3"
                elif 40 <= week <= 52:
                    metadata["Quarter"] = "Q4"
        
        # Add other useful metadata (customize as needed)
        for col in ["Region", "Customer", "Product", "RAG_Status"]:
            if col in row.index:
                metadata[col] = str(row[col]) if not pd.isna(row[col]) else None
        
        return metadata
    
    def create_embeddings(self, columns_to_embed: Optional[List[str]] = None) -> FAISS:
        """Create FAISS vector store with embeddings"""
        logger.info("Creating embeddings for all rows...")
        from utils import get_httpx_client
        http_client = get_httpx_client()
        
        # Set chunk_size to avoid exceeding token limits
        self.embeddings = OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            openai_api_key=Config.OPENAI_API_KEY,
            http_client=http_client,
            chunk_size=self.config.EMBEDDING_CHUNK_SIZE,
            max_retries=3
        )
        if columns_to_embed is None:
            columns_to_embed = self.config.COLUMNS_TO_EMBED
        
        if columns_to_embed is None:
            columns_to_embed = self.df.columns.tolist()
            logger.info(f"Embedding all {len(columns_to_embed)} columns")
        else:
            logger.info(f"Embedding specified columns: {columns_to_embed}")
        
        # Create documents for embedding
        documents = []
        for idx, row in self.df.iterrows():
            text = self._prepare_text_for_embedding(row, columns_to_embed)
            metadata = self._prepare_metadata(row, idx)
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)
        
        logger.info(f"Creating FAISS index for {len(documents)} documents...")
        logger.info("This may take a few minutes depending on dataset size...")
        
        # Create FAISS vectorstore with manual batching to avoid token limit errors
        # Process documents in batches to ensure we stay under 300k token limit per request
        batch_size = self.config.EMBEDDING_CHUNK_SIZE
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(documents)} documents in {total_batches} batches of ~{batch_size} documents each...")
        
        # Initialize vectorstore with first batch
        first_batch = documents[:batch_size]
        self.vectorstore = FAISS.from_documents(first_batch, self.embeddings)
        logger.info(f"Processed batch 1/{total_batches} ({len(first_batch)} documents)")
        
        # Add remaining batches incrementally
        for i in range(1, total_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(documents))
            batch = documents[start_idx:end_idx]
            
            # Create temporary vectorstore for this batch
            batch_vectorstore = FAISS.from_documents(batch, self.embeddings)
            
            # Merge with main vectorstore
            self.vectorstore.merge_from(batch_vectorstore)
            logger.info(f"Processed batch {i+1}/{total_batches} ({len(batch)} documents, total: {end_idx}/{len(documents)})")
        
        # Save to disk
        self.vectorstore.save_local(self.config.FAISS_INDEX_PATH)
        logger.info(f"FAISS index saved to {self.config.FAISS_INDEX_PATH}")
        
        return self.vectorstore
    
    def load_existing_vectorstore(self) -> FAISS:
        """Load existing FAISS vectorstore from disk"""
        logger.info(f"Loading existing FAISS index from {self.config.FAISS_INDEX_PATH}...")
        self.vectorstore = FAISS.load_local(
            self.config.FAISS_INDEX_PATH,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        logger.info("FAISS index loaded successfully")
        return self.vectorstore
    
    def initialize(self, force_rebuild: bool = False) -> tuple:
        """Initialize all components"""
        # Load CSV
        self.load_csv()
        
        # Create DuckDB
        self.create_duckdb()
        
        # Create or load embeddings
        if force_rebuild or not os.path.exists(self.config.FAISS_INDEX_PATH):
            self.create_embeddings()
        else:
            self.load_existing_vectorstore()
        
        return self.conn, self.vectorstore, self.df


if __name__ == "__main__":
    # Example usage
    loader = DataLoader("downloads/part-00000-tid-8397012257644732603-1200992a-2c19-4df8-a301-752e4b275d40-52-1-c000.csv")
    conn, vectorstore, df = loader.initialize(force_rebuild=True)
    print("Data loading complete!")
    print(f"Schema:\n{loader.get_schema_description()}")