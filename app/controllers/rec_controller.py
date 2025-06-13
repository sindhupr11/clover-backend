import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.utils.whisper_utils import convert_to_audio, transcribe_audio
from app.utils.whisper_groq_parser import process_transcript
from app.controllers.slack_controller import send_groq_summary_to_slack

router = APIRouter()

@router.post("/transcribe_and_summarize")
async def transcribe_and_summarize(file: UploadFile = File(...)):
    tmp_path = None
    audio_path = None
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
            
        file_ext = file.filename.lower().split('.')[-1]
        if file_ext not in ['mp3', 'wav', 'm4a', 'txt', 'docx']:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file provided")
            tmp.write(content)
            tmp_path = tmp.name

        # Step 1: Convert to audio (if needed)
        if file_ext in ['mp3', 'wav', 'm4a']:
            audio_path = tmp_path
        else:
            audio_path = convert_to_audio(tmp_path)

        # Step 2: Whisper transcription
        transcript = transcribe_audio(audio_path)
        if not transcript:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")

        # Step 3: Groq summarization
        summary = process_transcript(transcript)
        if not summary:
            raise HTTPException(status_code=500, detail="Failed to generate summary")

        # Prepare response
        response_data = {
            "status": "success",
            "data": {
                "summary": summary
            }
        }

        # Send to Slack
        send_groq_summary_to_slack(response_data)

        return response_data

    except HTTPException as he:
        error_data = {
            "status": "error",
            "error": str(he.detail)
        }
        send_groq_summary_to_slack(error_data)
        raise he
    except Exception as e:
        error_data = {
            "status": "error",
            "error": str(e)
        }
        send_groq_summary_to_slack(error_data)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Cleanup
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if audio_path and os.path.exists(audio_path) and audio_path != tmp_path:
            os.remove(audio_path)
