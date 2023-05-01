from typing_extensions import Annotated
from fastapi import FastAPI
from pydub import AudioSegment
from fastapi import FastAPI, File, UploadFile
import os
import tempfile
from pydantic import BaseSettings
import openai
import asyncio
import time
from fastapi.middleware.cors import CORSMiddleware
import boto3


class Settings(BaseSettings):
    # Control Access
    SECRET_JWT_KEY: str

    # OPEN AI
    OPENAI_API_KEY: str

    # AWS Key
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    REGION: str
    BUCKET_NAME: str

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI()

# Configure other stuff
openai.api_key = settings.OPENAI_API_KEY
s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


async def convert_audio_to_binary(audio: AudioSegment, extension):
    print(f"Generating audio segment now with parameters extension:{extension}")
    with tempfile.NamedTemporaryFile(suffix=extension, delete=True) as temp_file:
        audio.export(temp_file.name, extension[1:])
        file = open(temp_file.name, "rb")
        res = await openai.Audio.atranscribe("whisper-1", file)
        return res["text"]


@app.get("/")
def health():
    return {"Message": "Ok"}


@app.post("/generate-summary")
async def generate_summary(text: str):
    start_time = time.time()

    prompt_template = """Write a concise summary of the following:"""

    return {"message": "OK"}


@app.post("/generate-transcript")
async def create_upload_file(key: str):
    # We first download a file using boto
    start_time = time.time()
    _, ext = os.path.splitext(key)
    if ext != ".mp3" and ext != ".mp4":
        raise ValueError("Invalid Key")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        s3.download_fileobj(settings.BUCKET_NAME, key, temp_file)
        print(temp_file.name)
        # # s3.download_file(settings.BUCKET_NAME, key, "./test.mp4")
        audio = AudioSegment.from_file(temp_file.name, ext[1:])
        print(f"Audio has a length of {len(audio)/1000}")
        second = 1 * 1000
        step = 240 * second
        overlap = 2 * second
        curr = 0
        chunks = []
        while curr < len(audio):
            end = min(len(audio), curr + step - overlap)
            chunks.append(audio[curr:end])
            curr = curr + step - overlap
        print(f"Generated {len(chunks)} chunks")
        jobs = [convert_audio_to_binary(chunk, ext) for chunk in chunks]
        res = await asyncio.gather(*jobs)
        print(
            "Time took to process the request and return response is {} sec".format(
                time.time() - start_time
            )
        )
        return {"Data": " ".join(res)}

    # start_time = time.time()
    # _, ext = os.path.splitext(file.filename)
    # match (ext):
    #     case ".mp4" | ".mp3":
    #         with tempfile.NamedTemporaryFile(delete=True) as temp_file:
    #             temp_file.write(await file.read())
    #             temp_file.seek(0)

    #             audio = AudioSegment.from_file(temp_file.name, ext[1:])

    #             print(f"Audio has a length of {len(audio)/1000}")
    #             # We provide it in the form of 5 min chunks
    #             chunks = []
    #             # Time expressed in seconds and

    #     case _:
    #         return {"Mesage": "Invalid File Format"}
