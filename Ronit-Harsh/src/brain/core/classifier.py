import os
import re
import requests
import json
from typing import Tuple, Optional

class EmailClassifier:

    @staticmethod
    def classify_email(sender: str, subject: str, body: str) -> Tuple[str, bool, str, str]:
        """
        Returns:
            (category, should_notify, reason, source)
            source will be "Rules" or "LLM"
        """
        #Try Rules
        category, should_notify, reason = EmailClassifier._classify_via_rules(sender, body, subject)
        
        if category:
            return category, should_notify, reason, "Rules"
        
        # Fallback to LLM
        print(f"Rules matched nothing for '{subject[:30]}...', asking Mistral AI ...")
        category, should_notify, reason = EmailClassifier._classify_via_llm(sender, subject, body)
        return category, should_notify, reason, "LLM"

    @staticmethod
    def _classify_via_rules(sender: str, body: str, subject: str = "") -> Tuple[Optional[str], bool, Optional[str]]:
        sender = sender.lower()
        body = body.lower()
        
        # AIMS System
        if "noreply.comp@mailer.iith.ac.in" in sender or "noreply.comp@mailer.iith.ac.in" in body:
            return "AIMS", True, "AIMS System Email"
            
        # NSS Forms
        if "office.nss@iith.ac.in" in sender:
            # We match simple word boundaries
            has_fill = re.search(r'\bfill\b', body)
            has_form = re.search(r'\bform\b', body)
            
            if has_fill and has_form:
                return "NSS", True, "NSS Form Request"
            else:
                return "NSS", True, "NSS Update" # Default to notifying for NSS for now
            
        # Google Classroom
        if "no-reply@classroom.google.com" in sender:
            return "info", False, "Google Classroom Update"

        # Moodle
        if "moodle@cse.iith.ac.in" in sender:
            if "new sign in to your" not in subject.lower():
                return "Academic", True, "Important Moodle Notification"
            else:
                return "info", False, "Moodle Sign-in Notification"

        # Seminars & Talks (Neutral)
        # We classify these as Neutral as per user request.
        text_to_check = (subject + " " + body).lower()
        
        neutral_keywords = [
            "research proposal seminar", 
            "industry lecture series", 
            "open colloquium", 
            "open coloqq",
            "talk by", 
            "talk announcement",
            "seminar",
            " rps ", 
            " oc ",
            "phd viva-voce",
            "workshop on",
            "symposium"
        ]
        
        for kw in neutral_keywords:
            if kw in text_to_check:
                return "neutral", False, f"Detected Keyword: {kw.strip()}"

        return None, False, None

    @staticmethod
    def _classify_via_llm(sender: str, subject: str, body: str) -> Tuple[str, bool, str]:
        """
        Classifies an email using Mistral AI when rule-based classification fails.
        """
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            print("Warning: MISTRAL_API_KEY not found. Skipping LLM classification.")
            return "Unclassified", False, "Missing API Key"
            
        url = "https://api.mistral.ai/v1/chat/completions"
        
        # Truncate body to avoid hitting token limits (approx 4000 chars)
        truncated_body = body[:4000]
        
        prompt = f"""
        You are an intelligent email assistant for a student. Your job is to classify the following email and decide if the student should be notified immediately.
        
        Email Details:
        From: {sender}
        Subject: {subject}
        Body:
        {truncated_body}
        
        Instructions:
        1. Classify the email into one of these categories: 'Career', 'Academic', 'Administrative', 'Event', 'Spam', 'Other'.
        2. Decide if the user should be notified immediately (True/False). Notify ONLY for:
           - Urgent deadlines
           - Job/Internship offers or tests
           - Important academic announcements (exams, grades)
           - Administrative issues requiring action
           - Do NOT notify for general newsletters, reminders of long-term events, or spam.
        3. Provide a brief reason.
        
        Output format must be a valid JSON object:
        {{
            "category": "category_name",
            "should_notify": true/false,
            "reason": "short explanation"
        }}
        """
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            
            return parsed.get("category", "Other"), parsed.get("should_notify", False), parsed.get("reason", "LLM Decision")
            
        except Exception as e:
            print(f"Error calling Mistral API: {e}")
            return "Unclassified", False, f"LLM Error: {str(e)}"
