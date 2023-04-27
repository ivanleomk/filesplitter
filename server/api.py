from fastapi import FastAPI
from pydub import AudioSegment
from fastapi import FastAPI, File, UploadFile
import os
import tempfile
from pydantic import BaseSettings
import openai
import asyncio
import time


class Settings(BaseSettings):
    SECRET_JWT_KEY: str
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI()
openai.api_key = settings.OPENAI_API_KEY


async def convert_audio_to_binary(audio: AudioSegment, extension):
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as temp_file:
        audio.export(temp_file.name, extension)
        file = open(temp_file.name, "rb")
        res = await openai.Audio.atranscribe("whisper-1", file)
        return res["text"]


@app.post("/")
async def create_upload_file(file: UploadFile):
    start_time = time.time()
    _, ext = os.path.splitext(file.filename)
    match (ext):
        case ".mp4" | ".mp3":
            with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                temp_file.write(await file.read())
                temp_file.seek(0)

                audio = AudioSegment.from_file(temp_file.name, ext[1:])

                print(f"Audio has a length of {len(audio)/1000}")
                # We provide it in the form of 5 min chunks
                chunks = []
                # Time expressed in seconds and
                second = 1 * 1000
                step = 240 * second
                overlap = 2 * second
                curr = 0

                while curr < len(audio):
                    end = min(len(audio), curr + step - overlap)
                    chunks.append(audio[curr:end])
                    curr = curr + step - overlap
                print(f"Generated {len(chunks)} chunks")
                jobs = [convert_audio_to_binary(chunk, ext[1:]) for chunk in chunks]
                res = await asyncio.gather(*jobs)
                print(
                    "Time took to process the request and return response is {} sec".format(
                        time.time() - start_time
                    )
                )
                return {"Transcribed Message": " ".join(res)}
        case _:
            return {"Mesage": "Invalid File Format"}
