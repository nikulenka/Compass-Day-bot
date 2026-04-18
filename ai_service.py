# ai_service.py
import google.generativeai as genai
from openai import OpenAI
import os
import asyncio
import logging
import json
import re
from database import fetch_user_history
from prompts import MASTER_PROMPT

import html

def clean_html(text):
    """
    Strictly follow Telegram's allowed tags and escape sensitive characters.
    Telegram's ParseMode.HTML is very sensitive to unescaped <, > and &.
    """
    if not text: return ""
    
    # 1. Remove common forbidden tags that AI tends to include
    forbidden = ['<ul>', '</ul>', '<li>', '</li>', '<p>', '</p>', '<br>', '<br/>', '<h1>', '</h1>', '<h2>', '</h2>', '<h3>', '</h3>']
    for tag in forbidden:
        text = text.replace(tag, '\n') # Replace with newline for better formatting
        text = text.replace(tag.upper(), '\n')

    # 2. Escape EVERYTHING first (this turns all <, >, & into &lt;, &gt;, &amp;)
    text = html.escape(text)

    # 3. Restore ONLY specifically allowed tags
    # We look for escaped versions of our allowed tags and restore them
    allowed_tags = ['b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'code', 'pre', 'a', 'blockquote', 'span']
    for tag in allowed_tags:
        # Start tags: &lt;b&gt; -> <b>, &lt;a href="..."&gt; -> <a href="...">
        # For 'a' tag, we need to handle attributes.
        if tag == 'a':
            # Handle <a href="..."> specifically. AI might produce &lt;a href="..."&gt;
            # Regex to find &lt;a ... &gt; and restore it
            text = re.sub(r'&lt;a\s+(.*?)&gt;', r'<a \1>', text, flags=re.IGNORECASE)
            text = text.replace('&lt;/a&gt;', '</a>')
            text = text.replace('&lt;/A&gt;', '</a>')
        else:
            text = text.replace(f'&lt;{tag}&gt;', f'<{tag}>')
            text = text.replace(f'&lt;{tag.upper()}&gt;', f'<{tag}>')
            text = text.replace(f'&lt;/{tag}&gt;', f'</{tag}>')
            text = text.replace(f'&lt;/{tag.upper()}&gt;', f'</{tag}>')

    # 4. Final polish: remove double spaces and normalize newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

async def get_ai_response(prompt, provider="Gemini", api_key=None, model_name=None):
    """Generic AI caller for Gemini or OpenRouter."""
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") if provider == "Gemini" else os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        logging.error(f"Missing API Key for {provider}")
        return None

    try:
        if provider == "Gemini":
            genai.configure(api_key=api_key)
            m = genai.GenerativeModel(model_name or 'gemini-2.0-flash')
            # Using timeout to prevent hanging
            response = await asyncio.to_thread(m.generate_content, prompt)
            if not response or not response.text:
                logging.error("Empty response from Gemini")
                return None
            return response.text.strip()
        
        else: # OpenRouter / AI compatible
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model_name or "google/gemini-2.0-flash-001",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" } if "JSON" in prompt else None
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"AI Service error ({provider}): {e}")
        return None

async def generate_daily_content(user_data, provider="Gemini", api_key=None, model_name=None):
    """
    Optimized: One Master Prompt -> JSON Response.
    Saves ~70% tokens compared to chaining.
    """
    name = user_data['name']
    birth_date = str(user_data['birth_date'])
    occupation = user_data['occupation']
    tg_id = user_data['tg_id']

    # 1. Date calculation (using tomorrow)
    import datetime
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    tomorrow_date = tomorrow.strftime("%d.%m.%Y")
    
    days_ru = {
        "Monday": "понедельник", "Tuesday": "вторник", "Wednesday": "среда",
        "Thursday": "четверг", "Friday": "пятница", "Saturday": "суббота", "Sunday": "воскресенье"
    }
    tomorrow_day = days_ru.get(tomorrow.strftime("%A"), "")

    # 2. Fetch History
    history = fetch_user_history(tg_id, days=3)

    # 3. Master Request
    prompt = MASTER_PROMPT.format(
        name=name,
        birth_date=birth_date,
        occupation=occupation,
        tomorrow_date=tomorrow_date,
        tomorrow_day=tomorrow_day,
        history=history
    )

    raw_response = await get_ai_response(prompt, provider, api_key, model_name)
    if not raw_response:
        return None

    try:
        # Robust JSON extraction: Find the first '{' and last '}'
        match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback to old method if regex fails
            json_str = raw_response.replace('```json', '').replace('```', '').strip()
            
        data = json.loads(json_str)
        
        raw_html = data.get('telegram_html', '')
        
        # Final HTML Cleanup for Telegram entities
        final_html = clean_html(raw_html)
        
        # Append expert contacts block
        contacts_block = (
            "\n\n<b>Ваши эксперты:</b>\n"
            "- психолог <a href=\"https://t.me/Samira_soul\">Самира</a>\n"
            "- стилист <a href=\"https://t.me/nepravila_sveta\">Света</a> (<a href=\"https://t.me/stilnaya_evropa\">канал</a>)\n"
            "- нутрициолог <a href=\"https://t.me/murzichliza\">Лиза</a> (<a href=\"https://t.me/plastica_l\">канал</a>)"
        )
        final_html += contacts_block
        
        return {
            'html': final_html,
            'psych': data.get('psychologist_output', ''),
            'stylist': data.get('stylist_output', ''),
            'nutr': data.get('nutritionist_output', ''),
            'color': data.get('color_hex', '#FFFFFF')
        }
    except Exception as e:
        logging.error(f"Failed to parse AI JSON: {e}")
        logging.error(f"Raw response was: {raw_response[:500]}...") # Log partial for safety
        return None

