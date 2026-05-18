import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AIzaSyAqbm3iifdKUIPmCw2HRjjEqLViIKNTqOc")

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")


def get_ai_price_suggestion(data: dict):
    prompt = f"""
You are a pricing engine assistant.

Return ONLY:
1. Price range in INR
2. One line reason

Volume: {data.get("volume")}
Material: {data.get("material")}
Infill: {data.get("infill")}
Complexity: {data.get("complexity")}
Tier: {data.get("machine_tier")}
"""

    response = model.generate_content(prompt)
    return response.text
