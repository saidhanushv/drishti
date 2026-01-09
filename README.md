# Drishti Analytics

> **Vision. Insight. Action.**

Drishti Analytics is an intelligent, Agentic analytics platform designed to transform complex data into actionable insights. By combining modern dashboard visualizations with a conversational AI assistant, Drishti empowers users to explore their data through natural language query, automated SQL generation, and predictive analytics.

---

## Core Features

### ReAct Agent Chatbot
*   **Natural Language to SQL:** Ask questions like *"Show me the total sales for 2024"* in plain English. Drishti converts this to SQL, queries the database, and provides the answer.
*   **Navigation & Actions:** The assistant can navigate you to specific dashboard pages (e.g., *"Take me to the Gantt chart"*) and apply filters automatically.
*   **RAG (Retrieval-Augmented Generation):** Uses semantic search (FAISS) to understand context and retrieve relevant documentation or metadata.
*   **AutoML:** Run Machine Learning algorithms without writing a single line of code. The model cleans, prepares, normalizes values, finds the best model for the query and runs the model.

### Visualization Dashboard
*   **Analysis View:** A comprehensive tabular view using **AG Grid** with advanced filtering, sorting, and CSV export capabilities.
*   **Interactive Charts:** Beautiful, responsive charts powered by **ECharts** (Gauge charts, trend lines, etc.).
*   **Promotion Timeline:** A **Gantt Chart** view to visualize promotion schedules and overlaps.
*   **RAG Status:** A dedicated view for monitoring Red, Amber, and Green performance indicators with compact, high-visibility cards.

### Technical Capabilities
*   **Hybrid Query Engine:** Combines structured SQL querying (DuckDB) with unstructured semantic search.
*   **Azure ADLS Integration:** Seamlessly fetches and updates datasets from Azure Data Lake Storage.
*   **Performance:** Optimized for speed with a preset column-oriented database (DuckDB) and fast vector retrieval.

---

## Tech Stack

### Frontend
*   **Framework:** Angular 19 (Standalone Components)
*   **Styling:** Bootstrap 5.3, Custom "Premium UI" CSS Theme (Glassmorphism, gradients)
*   **Visualization:** Apache ECharts, AG Grid Enterprise/Community
*   **Language:** TypeScript

### Backend
*   **Framework:** Python (FastAPI/Uvicorn)
*   **Database:** DuckDB (OLAP SQL engine)
*   **Vector DB:** FAISS (Facebook AI Similarity Search)
*   **AI/LLM:** LangChain, OpenAI API
*   **Integration:** Azure ADLS Gen2

## Future Roadmap
*   **Predictive Modeling:** Deepening the integration of forecasting models directly into the "Predictive" dashboard tab.
*   **User Personalization:** Saving user preferences and chat history.
*   **Real-time Collaboration:** Allowing users to annotate and share insights directly from the dashboard.

Would love to find like minded people who want to develop the agent with me. Please feel free to reach out!
