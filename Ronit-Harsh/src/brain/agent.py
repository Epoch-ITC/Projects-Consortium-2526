import logging
import os
from typing import List, TypedDict, Any
from dotenv import load_dotenv
from supabase import create_client

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.brain.core.mcp_tool import MCPTool
from src.brain.agents.planner import PlannerAgent
from src.brain.agents.presenter import PresenterAgent
from src.brain.tools.retriever import KnowledgeRetriever
from src.brain.tools.scheduler import SchedulerTool
from src.brain.tools.profile import ProfileTool

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Env
load_dotenv()

# --- State Definition ---
class AgentState(TypedDict):
    chat_id: str
    user_id: str
    messages: List[BaseMessage]
    final_response: str
    planner_stats: dict
    presenter_stats: dict
    user_settings: dict

class Agent:
    def __init__(self):
        # 1. Initialize Tools
        self.tools: List[MCPTool] = [
            KnowledgeRetriever(),
            SchedulerTool(),
            ProfileTool()
        ]
        
        # 2. Initialize Agents
        self.planner = PlannerAgent(self.tools)
        self.presenter = PresenterAgent()
        
        # 3. Initialize Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role for backend logic
        self.supabase = create_client(url, key)

        # 4. Build Graph
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Add Nodes
        workflow.add_node("load_settings", self.load_settings)
        workflow.add_node("load_history", self.load_history)
        workflow.add_node("agent_logic", self.agent_logic)
        workflow.add_node("save_history", self.save_history)
        
        # Set Entry Point
        workflow.set_entry_point("load_settings")
        
        # Edges
        workflow.add_edge("load_settings", "load_history")
        workflow.add_edge("load_history", "agent_logic")
        workflow.add_edge("agent_logic", "save_history")
        workflow.add_edge("save_history", END)
        
        return workflow.compile()

    def run(self, user_query: str, user_id: str, chat_id: str) -> str:
        """
        Entry point to run the graph.
        """
        logger.info(f"🧠 BRAIN: Received query: '{user_query}' (Chat: {chat_id}, User: {user_id})")
        
        initial_state = {
            "chat_id": chat_id,
            "user_id": user_id,
            "messages": [HumanMessage(content=user_query)], # The NEW message
            "final_response": "",
            "planner_stats": {},
            "presenter_stats": {},
            "user_settings": {}
        }
        
        result = self.graph.invoke(initial_state)
        return result.get("final_response")

    # --- Nodes ---

    def load_settings(self, state: AgentState):
        """Fetches user settings (API key, model choices) from Supabase."""
        user_id = state["user_id"]
        try:
            data = self.supabase.table("user_settings")\
                .select("gemini_api_key, planner_model, presenter_model, huggingface_token")\
                .eq("user_id", user_id)\
                .execute()
            
            if data.data:
                settings = data.data[0]
                return {"user_settings": {
                    "gemini_api_key": settings.get("gemini_api_key", ""),
                    "planner_model": settings.get("planner_model", "gemini-2.5-flash"),
                    "presenter_model": settings.get("presenter_model", "gemini-2.5-flash"),
                    "huggingface_token": settings.get("huggingface_token", ""),
                }}
            else:
                return {"user_settings": {
                    "gemini_api_key": "",
                    "planner_model": "gemini-2.5-flash",
                    "presenter_model": "gemini-2.5-flash",
                    "huggingface_token": "",
                }}
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
            return {"user_settings": {}}

    def load_history(self, state: AgentState):
        """Fetches past messages from Supabase and prepends to state."""
        chat_id = state["chat_id"]
        
        try:
            # Fetch last 20 messages for context
            response = self.supabase.table("messages")\
                .select("*")\
                .eq("chat_id", chat_id)\
                .order("created_at", desc=True)\
                .limit(20)\
                .execute()
                
            db_msgs = response.data
            history: List[BaseMessage] = []
            
            # They come in desc order, reverse them to be chronological
            for msg in reversed(db_msgs):
                if msg["role"] == "user":
                    history.append(HumanMessage(content=msg["content"]))
                else:
                    history.append(AIMessage(content=msg["content"]))
            
            # Prepend history to the *new* message in state
            return {"messages": history + state["messages"]}
            
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            # Continue even if history fails, just without context
            return {"messages": state["messages"]}

    def agent_logic(self, state: AgentState):
        """Runs the Planner and Presenter with conversation history."""
        user_id = state["user_id"]
        settings = state.get("user_settings", {})
        api_key = settings.get("gemini_api_key", "")
        hf_token = settings.get("huggingface_token", "")
        
        # Set HF token on KnowledgeRetriever tool
        for tool in self.tools:
            if hasattr(tool, 'set_hf_token'):
                tool.set_hf_token(hf_token)
        
        # Check for API key
        if not api_key:
            return {
                "final_response": "⚠️ **No Gemini API Key configured.**\n\nPlease go to **Settings** (in the sidebar) and add your Gemini API key to start chatting.\n\nYou can get a free API key from [Google AI Studio](https://aistudio.google.com/apikey).",
                "planner_stats": {},
                "presenter_stats": {}
            }
        
        planner_model = settings.get("planner_model", "gemini-2.5-flash")
        presenter_model = settings.get("presenter_model", "gemini-2.5-flash")
        
        all_messages = state["messages"]
        
        # The last message is the current user query
        user_query = all_messages[-1].content
        # Everything before is conversation history
        history = all_messages[:-1]
        
        logger.info(f"🧠 agent_logic: {len(history)} history msgs, planner={planner_model}, presenter={presenter_model}")
        
        plan_result = self.planner.plan_and_execute(user_query, user_id, history, api_key=api_key, model_name=planner_model)
        presenter_result = self.presenter.present(plan_result, history, api_key=api_key, model_name=presenter_model)
        
        return {
            "final_response": presenter_result.get("text"),
            "planner_stats": plan_result.get("planner_stats", {}),
            "presenter_stats": presenter_result.get("stats", {})
        }

    def save_history(self, state: AgentState):
        """Saves the NEW interaction to Supabase."""
        chat_id = state["chat_id"]
        user_query = state["messages"][-1].content # The user message we just processed
        ai_response = state["final_response"]
        
        try:
            # 1. Save User Message
            self.supabase.table("messages").insert({
                "chat_id": chat_id,
                "role": "user",
                "content": user_query
            }).execute()
            
            # 2. Save AI Response
            self.supabase.table("messages").insert({
                "chat_id": chat_id,
                "role": "ai",
                "content": ai_response
            }).execute()
            
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            
        # Log stats just for console visibility
        self._log_stats(state)
        return state

    def _log_stats(self, state):
        planner_stats = state.get("planner_stats", {})
        presenter_stats = state.get("presenter_stats", {})
        total_calls = planner_stats.get("calls", 0) + presenter_stats.get("calls", 0)
        
        print("\n" + "="*50)
        print(f"📊 QUERY USAGE REPORT")
        print(f"Planner Model: {planner_stats.get('model')} (Calls: {planner_stats.get('calls')})")
        print(f"Presenter Model: {presenter_stats.get('model')} (Calls: {presenter_stats.get('calls')})")
        print(f"💰 TOTAL LLM CALLS: {total_calls}")
        print("="*50 + "\n")

if __name__ == "__main__":
    pass
