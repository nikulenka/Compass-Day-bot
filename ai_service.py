# ai_service.py
import google.generativeai as genai
import os
import asyncio
import logging
from database import fetch_user_history
from prompts import PSYCHOLOGIST_PROMPT, STYLIST_PROMPT, NUTRITIONIST_PROMPT, SYNTHESIZER_PROMPT

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash-latest')

async def get_expert_response(prompt):
    """Call Gemini API with rate limiting."""
    try:
        response = model.generate_content(prompt)
        await asyncio.sleep(4) 
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        return ""

async def generate_daily_content(user_data):
    """
    Implements Prompt Chaining and returns structured data for logging.
    """
    name = user_data['name']
    birth_date = user_data['birth_date']
    occupation = user_data['occupation']
    tg_id = user_data['tg_id']

    # 1. Fetch History
    history = fetch_user_history(tg_id, days=3)

    # 2. Psychologist
    psych_input = PSYCHOLOGIST_PROMPT.format(
        name=name, 
        birth_date=birth_date,
        history=history
    )
    psych_output = await get_expert_response(psych_input)
    if not psych_output:
        return None

    # 3. Stylist
    stylist_input = STYLIST_PROMPT.format(
        name=name, 
        psych_output=psych_output, 
        occupation=occupation,
        history=history
    )
    stylist_output = await get_expert_response(stylist_input)

    # 4. Nutritionist
    nutr_input = NUTRITIONIST_PROMPT.format(
        psych_output=psych_output,
        history=history
    )
    nutr_output = await get_expert_response(nutr_input)

    # 5. Synthesizer
    synth_input = SYNTHESIZER_PROMPT.format(
        name=name,
        psych_output=psych_output,
        stylist_output=stylist_output,
        nutr_output=nutr_output
    )
    final_html = await get_expert_response(synth_input)

    # Try to extract a color if needed, otherwise send None
    # (Synthesizer prompt could be updated to return JSON with color if required)
    
    return {
        'html': final_html,
        'psych': psych_output,
        'stylist': stylist_output,
        'nutr': nutr_output,
        'color': None # Default for now
    }
