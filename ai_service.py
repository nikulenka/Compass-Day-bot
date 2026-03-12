# ai_service.py
import google.generativeai as genai
import os
import asyncio
import logging
from database import fetch_active_users, log_daily_mailing, fetch_user_history
from prompts import PSYCHOLOGIST_PROMPT, STYLIST_PROMPT, NUTRITIONIST_PROMPT, SYNTHESIZER_PROMPT

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

async def get_expert_response(prompt):
    """Call Gemini API with rate limiting."""
    try:
        response = model.generate_content(prompt)
        # Gemini Free Tier limit is roughly 15 RPM. 
        # Adding a small delay to stay safe when processing multiple users.
        await asyncio.sleep(4) 
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        return ""

async def generate_daily_content(user_data):
    """
    Implements Prompt Chaining:
    Psychologist -> Stylist & Nutritionist -> Synthesizer
    """
    name = user_data['name']
    birth_date = user_data['birth_date']
    occupation = user_data['occupation']

    # 0. Fetch History
    history = fetch_user_history(user_data['tg_id'], days=3)

    # 1. Psychologist
    psych_input = PSYCHOLOGIST_PROMPT.format(
        name=name, 
        birth_date=birth_date,
        history=history
    )
    psych_output = await get_expert_response(psych_input)
    if not psych_output:
        return None

    # 2. Stylist (depends on Psychologist)
    stylist_input = STYLIST_PROMPT.format(
        name=name, 
        psych_output=psych_output, 
        occupation=occupation,
        history=history
    )
    stylist_output = await get_expert_response(stylist_input)

    # 3. Nutritionist (depends on Psychologist)
    nutr_input = NUTRITIONIST_PROMPT.format(
        psych_output=psych_output,
        history=history
    )
    nutr_output = await get_expert_response(nutr_input)

    # 4. Synthesizer (collects everything)
    synth_input = SYNTHESIZER_PROMPT.format(
        name=name,
        psych_output=psych_output,
        stylist_output=stylist_output,
        nutr_output=nutr_output
    )
    final_html = await get_expert_response(synth_input)

    return final_html
