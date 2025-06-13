import ffmpeg
import whisper
import os
import tempfile

model = whisper.load_model("large")

def convert_to_audio(input_path: str) -> str:
    output_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    ffmpeg.input(input_path).output(output_audio, **{'q:a': 0, 'map': 'a'}).run(overwrite_output=True)
    return output_audio

def transcribe_audio(audio_path: str) -> str:
    result = model.transcribe(audio_path)
    return result["text"]
