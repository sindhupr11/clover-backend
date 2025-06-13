import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

ENV_FILE = ".env"
load_dotenv(ENV_FILE)

class BotConfig(BaseModel):
    bot_token: Optional[str] = os.getenv("SLACK_BOT_TOKEN")
    bot_app_token: Optional[str] = os.getenv("SLACK_APP_TOKEN")
    channel_id: Optional[str] = os.getenv("SLACK_CHANNEL_ID")
    meeting_end_time: Optional[str] = os.getenv("MEETING_END_TIME")  

class Config:
    _instance = None
    _config = BotConfig()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def set_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

                env_key = key.upper()
                if key == "bot_token":
                    env_key = "SLACK_BOT_TOKEN"
                elif key == "bot_app_token":
                    env_key = "SLACK_APP_TOKEN"
                elif key == "channel_id":
                    env_key = "SLACK_CHANNEL_ID"
                elif key == "meeting_end_time":
                    env_key = "MEETING_END_TIME"
                set_key(ENV_FILE, env_key, value)

    def get_config(self) -> BotConfig:
        load_dotenv(ENV_FILE, override=True) 
        self._config = BotConfig(
            bot_token=os.getenv("SLACK_BOT_TOKEN"),
            bot_app_token=os.getenv("SLACK_APP_TOKEN"),
            channel_id=os.getenv("SLACK_CHANNEL_ID"),
            meeting_end_time=os.getenv("MEETING_END_TIME", "09:00")
        )
        return self._config


config = Config()
