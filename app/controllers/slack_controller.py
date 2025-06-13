import os
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import schedule
import threading
import time
from datetime import datetime

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
UPLOAD_LINK = os.getenv("UPLOAD_LINK")
MEETING_END_TIME = os.getenv("MEETING_END_TIME")

client = WebClient(token=SLACK_BOT_TOKEN)
app = App(token=SLACK_BOT_TOKEN)

def send_daily_reminder():
    try:
        current_date = datetime.now().strftime("%B %d, %Y")
        current_time = datetime.now().strftime("%H:%M:%S")

        message = f"""
:wave: *Good morning team!* :sunny:

*Date:* {current_date}, {current_time}
*Action Required:* Please upload today's standup transcript here:
{UPLOAD_LINK}
"""
        response = client.chat_postMessage(
            channel=CHANNEL_ID,
            text=message,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        )
        print(f"✅ Daily reminder sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"❌ Failed to send daily reminder: {str(e)}")

#########################
# def send_test_reminder():
#     try:
#         current_time = datetime.now().strftime("%H:%M:%S")
#         current_date = datetime.now().strftime("%B %d, %Y")
#         message = f"""
#         (test message)
# :wave: *Good morning team!* :sunny:

# *Date:* {current_date}, {current_time}
# *Action Required:* Please upload today's standup transcript here:
# {UPLOAD_LINK}
# """
#         response = client.chat_postMessage(
#             channel=CHANNEL_ID,
#             text=message,
#             blocks=[
#                 {
#                     "type": "section",
#                     "text": {
#                         "type": "mrkdwn",
#                         "text": message
#                     }
#                 }
#             ]
#         )
#         print(f"✅ Test message sent at {current_time}")
#     except Exception as e:
#         print(f"❌ Failed to send test message: {str(e)}")
#########################

def send_groq_summary_to_slack(result: dict):
    try:
        if result.get("status") == "success" and "data" in result:
            summary = result["data"]["summary"]
            slack_response = client.chat_postMessage(
                channel=CHANNEL_ID,
                text=f"📝 *Team Update Summary:*\n```{summary}```"
            )
            print("✅ Summary sent to Slack:", slack_response["ts"])
        else:
            error_msg = result.get("error", "Unknown error occurred")
            client.chat_postMessage(
                channel=CHANNEL_ID,
                text=f"⚠️ *Error processing transcript:*\n{error_msg}"
            )
    except Exception as e:
        print("❌ Error sending summary to Slack:", e)
        client.chat_postMessage(
            channel=CHANNEL_ID,
            text=f"⚠️ *Error sending to Slack:*\n{str(e)}"
        )

def run_schedule():
    
    schedule.every().day.at(MEETING_END_TIME).do(send_daily_reminder)
    
    # schedule.every(1).minutes.do(send_test_reminder)#########################
    
    print(f"✅ Scheduler started with daily reminder at {MEETING_END_TIME}")
    while True:
        schedule.run_pending()
        time.sleep(1) 

def start_scheduler():
    thread = threading.Thread(target=run_schedule, daemon=True)
    thread.start()
    print("✅ Scheduler thread started")

def start_slack_bot():
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
