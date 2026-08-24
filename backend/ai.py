import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API"))

def get_ai_data(issue_text):
    prompt = f"""
    You are an expert IT Helpdesk Assistant. Analyze this user issue: "{issue_text}"
    
    Return a raw JSON object with exactly these three keys:
    - "category": (Choose one: Network, Hardware, Software, Account Access, or Other)
    - "priority": (Choose one: between 1 to 5. 1 as high priority and 5 is lowest priority)
    - "suggested_fix": (A short, 1-sentence troubleshooting step for the IT admin)
    
    Return ONLY the JSON. Do not use markdown blocks like ```json.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        model_response = model.generate_content(prompt)
        clean_response = json.loads(model_response.text.strip())
        return clean_response
    except Exception as e:
        print(f"Failed to generate response.{e}")
        return dict()
