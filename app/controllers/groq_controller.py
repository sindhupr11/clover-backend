import os
import json
import requests
from io import BytesIO
from dotenv import load_dotenv
from fastapi import UploadFile, File, HTTPException, BackgroundTasks
from app.utils.docx_parser import extract_text_from_docx
from app.controllers.slack_controller import send_groq_summary_to_slack

load_dotenv()

API_URL = "https://api.groq.com/openai/v1/chat/completions" 
API_KEY = os.getenv("GROQ_API_KEY")


async def process_docx_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None) -> dict:
    if file.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")

    contents = await file.read()

    try:
        full_text = extract_text_from_docx(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read .docx file: {str(e)}")

    prompt = """
You are a text parser that extracts and formats information from team updates. Output *only* the formatted information for *all* team members in the input, in the exact format shown below, with no additional text or commentary. Summarize each field to 5-10 words, preserving technical terms and keywords. Use lowercase for tasks and blockers fields, and separate each person's summary with a single blank line.

Expected output format for each person:
{person_name}  
time: {time}  
yesterday: {yesterday_tasks}  
today: {today_tasks}  
blockers: {blockers}  

Input:
{input_text}

Output concise formatted summaries for all team members, in the specified format, with no extra text.
"""

    prompt = prompt.replace("{person_name}", "{{person_name}}")
    prompt = prompt.replace("{time}", "{{time}}")
    prompt = prompt.replace("{yesterday_tasks}", "{{yesterday_tasks}}")
    prompt = prompt.replace("{today_tasks}", "{{today_tasks}}")
    prompt = prompt.replace("{blockers}", "{{blockers}}")

    formatted_prompt = prompt.format(input_text=full_text)

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "user",
                "content": formatted_prompt
            }
        ],
        "max_tokens": 400,
        "temperature": 0.7,
        "stop": ["\n\n\n"]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        summary = result["choices"][0]["message"]["content"].strip()
        
        response_data = {
            "status": "success",
            "data": {
                "message": "Transcript processed successfully",
                "summary": summary
            }
        }
        
        if background_tasks:
            background_tasks.add_task(send_groq_summary_to_slack, response_data)
        
        return response_data
    except requests.exceptions.Timeout:
        error_data = {"status": "error", "error": "Request timed out. Please try again."}
        if background_tasks:
            background_tasks.add_task(send_groq_summary_to_slack, error_data)
        raise HTTPException(status_code=504, detail="Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        error_data = {"status": "error", "error": f"Error making API request: {str(e)}"}
        if background_tasks:
            background_tasks.add_task(send_groq_summary_to_slack, error_data)
        raise HTTPException(status_code=500, detail=f"Error making API request: {str(e)}")
    except (KeyError, json.JSONDecodeError) as e:
        error_data = {"status": "error", "error": f"Error parsing API response: {str(e)}"}
        if background_tasks:
            background_tasks.add_task(send_groq_summary_to_slack, error_data)
        raise HTTPException(status_code=500, detail=f"Error parsing API response: {str(e)}")
