import logging
import os
import google.generativeai as genai
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PresenterAgent:
    def __init__(self):
        pass

    def present(self, plan_result: Dict[str, Any], history: list = None, api_key: str = "", model_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
        if not api_key:
            return {"text": "Reference Code: NO_BRAIN. The AI model is offline.", "stats": {}}
        
        # Configure with user's API key and create model
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        query = plan_result.get("query")
        trace = "\n\n".join(plan_result.get("trace", []))
        
        # Format conversation history for context
        history_text = ""
        if history:
            recent_history = history[-10:]
            history_lines = []
            for msg in recent_history:
                role = "User" if msg.type == "human" else "AI"
                content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
                history_lines.append(f"{role}: {content}")
            history_text = "\n".join(history_lines)
        
        prompt = f"""
        You are a smart, friendly, and helpful Student Assistant.
        
        {"CONVERSATION HISTORY (previous messages in this chat):" + chr(10) + history_text if history_text else ""}
        
        USER QUERY: "{query}"
        
        Using the following information gathered by your Planner, answer the user.
        
        PLANNER TRACE:
        {trace}
        
        INSTRUCTIONS:
        1. **Be Human**: Speak naturally. Don't say "The tool returned...". Say "I found...", "According to the schedule..."
        2. **Cite Sources**: If the trace contains links (e.g., from search results or calendar), include them.
        3. **Give Advice**: If you see a quiz coming up, suggest studying. 
        4. **No Jargon**: Do not mention "JSON", "UUID", "Supabase", "ChromaDB", or "Planner".
        5. **Accuracy**: Only use information from the trace. If the trace is empty or failed, apologize and ask for clarification.
        6. **Conversational Continuity**: If there is conversation history, your response should feel like a natural continuation. Reference previous context when relevant (e.g. "As I mentioned earlier...", "Going back to your question about...").
        
        FORMAT:
        - Use Markdown.
        - Use emojis sparingly but effectively (📅, 📚).
        
        RESPONSE:
        """
        
        try:
            response = model.generate_content(prompt)
            print(prompt)
            return {
                "text": response.text,
                "stats": {
                     "model": model_name,
                     "calls": 1
                }
            }
        except Exception as e:
            logger.error(f"Presenter Error: {e}")
            return {
                "text": f"I had trouble formulating a response. Here is what I found:\n{trace}",
                "stats": {
                     "model": "gemini-2.5-flash",
                     "calls": 0,
                     "error": str(e)
                }
            }
