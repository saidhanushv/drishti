"""
ReAct Agent for orchestrating SQL, RAG, and ML tools
"""
from typing import List, AsyncIterator, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from config import Config
from utils import (
    QueryLogger,
    get_httpx_client,
    reset_tool_usage,
    get_tool_usage_status,
)
import logging

logger = logging.getLogger(__name__)


class PromotionAnalysisAgent:
    """ReAct Agent for FMCG Promotion Analysis"""
    
    def __init__(self, tools: List[Tool], schema_description: str, few_shot_examples: str = ""):
        self.tools = tools
        self.schema_description = schema_description
        self.few_shot_examples = few_shot_examples
        
        # Create ChatOpenAI with standard OpenAI API
        http_client = get_httpx_client()
        http_async_client = get_httpx_client(async_mode=True)
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=Config.LLM_TEMPERATURE,
            openai_api_key=Config.OPENAI_API_KEY,
            http_client=http_client,
            http_async_client=http_async_client
        )
        
        # Create managed ReAct agent via LangGraph prebuilt
        self.agent = create_react_agent(self.llm, self.tools)
    

    
    
    def query(self, question: str) -> dict:
        """Execute query through the agent"""
        logger.info(f"\n{'='*80}")
        logger.info(f"[NEW QUERY] {question}")
        logger.info(f"{'='*80}\n")
        
        print(f"\n{'='*80}")
        print("🤖 AGENT PROCESSING QUERY")
        print(f"{'='*80}")
        print()

        try:
            reset_tool_usage()
            # Compose context inline to steer few-shot and dataset context
            tools_desc = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
            prefix_parts = [
                "You are an expert FMCG Promotion Analysis Assistant.",
                f"DATASET CONTEXT:\n{self.schema_description}",
                "You have access to the following tools:",
                tools_desc,
                "Guidelines: Use SQL_Query for aggregations/comparisons, Semantic_Search for similarity, and ML_Prediction for forecasts.",
                "IMPORTANT: Do NOT include the generated SQL query in your final answer. Only show the results and analysis.",
                "FORMATTING: The output will be displayed in a narrow chat window (offcanvas). Keep lines concise, use bullet points, and avoid wide tables or long paragraphs.",
            ]
            if self.few_shot_examples:
                prefix_parts.append("EXAMPLES (learn the style and tool selection):\n" + self.few_shot_examples)
            composed_input = "\n\n".join(prefix_parts) + f"\n\nQuestion: {question}"

            graph_result = self.agent.invoke({
                "messages": [
                    {"role": "user", "content": composed_input}
                ]
            })

            # Extract final text from LangGraph result
            final_output = None
            steps = []
            try:
                messages = graph_result.get("messages", []) if isinstance(graph_result, dict) else []
                if messages:
                    final_msg = messages[-1]
                    final_output = getattr(final_msg, "content", None) or final_msg.get("content")
            except Exception:
                pass
            if not final_output:
                final_output = str(graph_result)

            QueryLogger.log_agent_action(action=question, observation=final_output)

            result = {"output": final_output, "intermediate_steps": steps}
            
            # Log the action
            QueryLogger.log_agent_action(
                action=question,
                observation=result.get("output", "")
            )
            
            tool_usage_message = get_tool_usage_status()

            print(f"\n{'='*80}")
            print("✅ FINAL ANSWER")
            print(f"{'='*80}")
            final_output = result.get("output") if isinstance(result, dict) else str(result)
            print(f"{final_output}\n")
            print(f"[TOOL USAGE] {tool_usage_message}\n")

            return {"output": final_output, "intermediate_steps": []}
            
        except Exception as e:
            error_msg = f"Agent execution error: {str(e)}"
            logger.error(error_msg)
            print(f"\n{'='*80}")
            print(f"❌ ERROR")
            print(f"{'='*80}")
            print(f"{error_msg}\n")
            
            return {
                "output": f"Error: {error_msg}",
                "intermediate_steps": []
            }
    
    def get_tool_usage_summary(self, result: dict) -> dict:
        """Get summary of which tools were used"""
        intermediate_steps = result.get("intermediate_steps", [])
        
        tool_usage = {
            "SQL_Query": 0,
            "Semantic_Search": 0,
            "ML_Prediction": 0
        }
        
        for step in intermediate_steps:
            if len(step) >= 2:
                action = step[0]
                tool_name = action.tool
                if tool_name in tool_usage:
                    tool_usage[tool_name] += 1
        
        return tool_usage
    
    async def query_stream(self, question: str) -> AsyncIterator[Dict[str, Any]]:
        """Execute query through the agent with streaming support"""
        logger.info(f"\n{'='*80}")
        logger.info(f"[NEW QUERY] {question}")
        logger.info(f"{'='*80}\n")
        
        import asyncio
        
        try:
            reset_tool_usage()
            
            # Compose context inline to steer few-shot and dataset context
            tools_desc = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
            prefix_parts = [
                "You are an expert FMCG Promotion Analysis Assistant.",
                f"DATASET CONTEXT:\n{self.schema_description}",
                "You have access to the following tools:",
                tools_desc,
                "Guidelines: Use SQL_Query for aggregations/comparisons, Semantic_Search for similarity, and ML_Prediction for forecasts.",
                "IMPORTANT: Do NOT include the generated SQL query in your final answer. Only show the results and analysis.",
                "FORMATTING: The output will be displayed in a narrow chat window (offcanvas). Keep lines concise, use bullet points, and avoid wide tables or long paragraphs.",
            ]
            if self.few_shot_examples:
                prefix_parts.append("EXAMPLES (learn the style and tool selection):\n" + self.few_shot_examples)
            composed_input = "\n\n".join(prefix_parts) + f"\n\nQuestion: {question}"
            
            # Map tool status to user-friendly messages
            status_messages = {
                "SQL TOOL USED": "Converting natural language to SQL...",
                "RAG TOOL USED": "Semantic search in progress...",
                "ML TOOL USED": "Running appropriate algorithm and statistical analysis to perform the prediction..."
            }
            
            # Track last tool status
            last_tool_status = None
            
            # Monitor tool usage while agent runs
            async def monitor_status():
                nonlocal last_tool_status
                while True:
                    await asyncio.sleep(0.2)  # Check every 200ms
                    current_status = get_tool_usage_status()
                    if current_status != last_tool_status and current_status != "INCUBATOR RESPONSE (NO TOOL USED)":
                        last_tool_status = current_status
                        status_msg = status_messages.get(current_status, "Processing...")
                        yield {
                            "type": "status",
                            "message": status_msg
                        }
            
            # Run agent in background and monitor status
            accumulated_text = ""
            
            # Stream from agent
            async for event in self.agent.astream({
                "messages": [
                    {"role": "user", "content": composed_input}
                ]
            }):
                # Check tool status
                current_status = get_tool_usage_status()
                if current_status != last_tool_status and current_status != "INCUBATOR RESPONSE (NO TOOL USED)":
                    last_tool_status = current_status
                    status_msg = status_messages.get(current_status, "Processing...")
                    yield {
                        "type": "status",
                        "message": status_msg
                    }
                
                # Process event for content
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if "messages" in node_output:
                            for msg in node_output["messages"]:
                                # Check for tool calls
                                if hasattr(msg, "tool_calls") and msg.tool_calls:
                                    for tool_call in msg.tool_calls:
                                        tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                                        tool_status_map = {
                                            "SQL_Query": "Converting natural language to SQL...",
                                            "Semantic_Search": "Semantic search in progress...",
                                            "ML_Prediction": "Running appropriate algorithm and statistical analysis to perform the prediction..."
                                        }
                                        status_msg = tool_status_map.get(tool_name, "Processing...")
                                        yield {
                                            "type": "status",
                                            "message": status_msg
                                        }
                                
                                # Extract content ONLY from AI messages, not tool responses
                                # Check if this is an AI message (not a tool message)
                                msg_type = getattr(msg, "type", None) or (msg.get("type") if isinstance(msg, dict) else None)
                                
                                # Only process if it's an AI message or if type is not set (assume AI)
                                is_tool_message = msg_type == "tool" or (hasattr(msg, "name") and msg.name)
                                
                                if not is_tool_message and hasattr(msg, "content") and msg.content:
                                    content = str(msg.content)
                                    # Skip empty content or tool output patterns
                                    if content and content != accumulated_text and not content.startswith("Results ("):
                                        new_content = content[len(accumulated_text):] if accumulated_text else content
                                        accumulated_text = content
                                        if new_content:
                                            yield {
                                                "type": "content",
                                                "content": new_content
                                            }
            
            # Ensure we have final output
            if not accumulated_text:
                # Get final result synchronously as fallback
                final_result = self.agent.invoke({
                    "messages": [{"role": "user", "content": composed_input}]
                })
                if isinstance(final_result, dict) and "messages" in final_result:
                    messages = final_result["messages"]
                    if messages:
                        final_msg = messages[-1]
                        accumulated_text = getattr(final_msg, "content", None) or final_msg.get("content", "")
                        if accumulated_text:
                            yield {
                                "type": "content",
                                "content": accumulated_text
                            }
            
            QueryLogger.log_agent_action(action=question, observation=accumulated_text)
            
            # Final completion
            yield {
                "type": "done",
                "content": accumulated_text
            }
            
        except Exception as e:
            error_msg = f"Agent execution error: {str(e)}"
            logger.error(error_msg)
            yield {
                "type": "error",
                "message": error_msg
            }


if __name__ == "__main__":
    pass