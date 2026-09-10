import logging
import os
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional

from src.brain.core.mcp_tool import MCPTool
from src.brain.core.system_info import SystemInfo

logger = logging.getLogger(__name__)

class PlannerAgent:
    def __init__(self, tools: List[MCPTool]):
        self.tools = tools
        self.tool_map = {t.name: t for t in tools}
        self.system_info = SystemInfo()

    def plan_and_execute(self, user_query: str, user_id: str, history: list = None, api_key: str = "", model_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
        """
        Runs the ReAct loop with conversation history for multi-turn context.
        Uses the user's API key and chosen model.
        """
        if not api_key:
            return {"error": "No API Key"}
        
        # Configure with user's API key and create model
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        trace = [] # Log of what happened: "User asked...", "Tool X result..."
        max_steps = 5
        
        # Initial Context
        import datetime
        current_time = datetime.datetime.now().isoformat()
        
        system_context = self.system_info.get_system_prompt()
        tool_defs = "\n".join([f"- {t.name}: {t.description} (Schema: {t.input_schema})" for t in self.tools])
        
        # Format conversation history (cap to last 10 messages for context window)
        history_text = ""
        if history:
            recent_history = history[-10:]
            history_lines = []
            for msg in recent_history:
                role = "User" if msg.type == "human" else "AI"
                # Truncate long messages in history
                content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
                history_lines.append(f"{role}: {content}")
            history_text = "\n".join(history_lines)
        
        messages = [
            {"role": "user", "parts": [f"""
            CURRENT TIME: {current_time}
            
            {system_context}
            
            AVAILABLE TOOLS:
            {tool_defs}
            
            GOAL: Build a complete context to answer the user's query.
            You have a 'trace' of information.
            
            {"CONVERSATION HISTORY (previous messages in this chat):" + chr(10) + history_text if history_text else ""}
            
            INSTRUCTIONS:
            1. Analyze the User Query. Use the conversation history to understand context and references (e.g. "the first one", "tell me more", "that course").
            2. Decide if you need more information.
            3. If yes, output JSON to call a tool: {{ "tool": "name", "arguments": {{...}} }}
            4. If no (you have enough info or the user just said 'hi'), output JSON: {{ "done": true, "reason": "Gathered all info" }}
            
            USER QUERY: "{user_query}"
            """]}
        ]

        logger.info(f"--- Starting Plan for: {user_query} (with {len(history) if history else 0} history msgs) ---")

        for step in range(max_steps):
            # 1. Think
            try:
                # We use specific generation config to force JSON if possible, 
                # but Gemini Flash is good at following instruction.
                response = model.generate_content(
                    messages, 
                    generation_config={"response_mime_type": "application/json"}
                )
                raw_text = response.text
                # Remove Markdown code blocks if present
                if raw_text.startswith("```"):
                     raw_text = raw_text.strip("`").replace("json\n", "", 1)

                raw_action = json.loads(raw_text)
                
                if isinstance(raw_action, list):
                    if len(raw_action) > 0:
                        action = raw_action[0]
                    else:
                        action = {}
                else:
                    action = raw_action
            except Exception as e:
                logger.error(f"Planner Think Error: {e}")
                # trace.append(f"Planner Error: {e}")
                break

            # 2. Check for Done
            if action.get("done"):
                logger.info("Planner decided it is done.")
                break
                
            tool_name = action.get("tool")
            tool_args = action.get("arguments", {})
            
            if not tool_name:
                # Fallback if LLM outputs weird JSON
                break

            # 3. Act
            logger.info(f"Step {step+1}: Call {tool_name} {tool_args}")
            trace_entry = f"Step {step+1}: Action {tool_name}({tool_args})"
            
            tool = self.tool_map.get(tool_name)
            if tool:
                # 🛡️ MANUAL INJECTION: Inject user_id for security
                tool_args["user_id"] = user_id
                
                try:
                    result = str(tool.execute(**tool_args))
                except TypeError as te:
                    # Fallback for tools that don't accept user_id
                    if "unexpected keyword argument 'user_id'" in str(te):
                        del tool_args["user_id"]
                        result = str(tool.execute(**tool_args))
                    else:
                        result = f"Error executing tool: {te}"
            else:
                result = f"Error: Tool {tool_name} not found."
            
            # Truncate long results for the LLM context (but keep full for Final Presenter?)
            # Actually Planner needs to see the result to know if it needs to Read Deeper.
            # We truncate slightly to avoid blowing context window if it reads a massive book.
            result_snippet = result[:5000] 
            
            trace_entry += f"\nResult: {result_snippet}"
            trace.append(trace_entry)
            
            # 4. Observe (Feed back to LLM)
            messages.append({"role": "model", "parts": [response.text]})
            # Truncate slightly to avoiding huge context usage
            messages.append({"role": "user", "parts": [f"TOOL OUTPUT: {result[:8000]}"]})

            # Check trace limit
            if len(trace) > 10:
                 break
        
        return {
            "query": user_query,
            "trace": trace,
            "planner_stats": {
                "model": model_name,
                "calls": step + 1 # Each step is one call
            }
        }
