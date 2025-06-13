from fastapi import FastAPI, Body, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
from app.controllers.groq_controller import process_docx_file
from app.controllers.slack_controller import start_scheduler
from app.controllers.creds_controller import set_credentials, get_credentials
from app.controllers.rec_controller import transcribe_and_summarize

app = FastAPI(title="Bot Backend Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload_media")
async def upload_media(file: UploadFile = File(...)):
    return await transcribe_and_summarize(file)

@app.post("/set-credentials", tags=["Credentials"])
def set_creds_route(
    bot_token: str = Body(..., description="Slack Bot User OAuth Token"),
    bot_app_token: str = Body(..., description="Slack App-Level Token"),
    channel_id: str = Body(..., description="Slack Channel ID where messages will be sent"),
    meeting_end_time: str = Body("09:00", description="Time when the daily meeting ends (24-hour format, e.g., '09:00')")
):
    return set_credentials(bot_token, bot_app_token, channel_id, meeting_end_time)

@app.get("/get-credentials", tags=["Credentials"])
def get_creds_route():
    return get_credentials()

@app.post("/upload-transcript", tags=["Transcript"])
async def upload_transcript(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    print("📥 Received file:", file.filename)
    result = await process_docx_file(file, background_tasks)
    print("📤 Generated summary:", result)
    return result

@app.on_event("startup")
def startup_event():
    start_scheduler()
    print("✅ Scheduler started")
