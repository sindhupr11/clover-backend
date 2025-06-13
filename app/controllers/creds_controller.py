from app.config import config

def set_credentials(
    bot_token: str,
    bot_app_token: str,
    channel_id: str,
    meeting_end_time: str = "09:00"
):
    config.set_config(
        bot_token=bot_token,
        bot_app_token=bot_app_token,
        channel_id=channel_id,
        meeting_end_time=meeting_end_time
    )
    return {
        "message": "Credentials and settings saved successfully",
        "settings": {
            "channel_id": channel_id,
            "meeting_end_time": meeting_end_time
        }
    }

def get_credentials():
    return config.get_config().dict()
