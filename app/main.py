from fastapi import BackgroundTasks
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
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import File as FileObject
from sqlalchemy.sql.expression import func
from datetime import datetime, timedelta

THRESHOLD = timedelta(minutes=30)


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

    # Database Stuff
    DATABASE_URL: str

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

# make sure to append +mysqlconnector to the db string
engine = create_engine(settings.DATABASE_URL, echo=True)


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


@app.post("/delete-file")
async def delete_file(key: str):
    # We validate that a file exists
    try:
        res = s3.Object(settings.BUCKET_NAME, key).delete()
        print(res)
        return {"Message": "Ok"}
    except Exception as e:
        print(e)
        return {"Error": "Unable to delete file"}


async def create_transcript(key: str):
    print(f"Starting to generate transcript with key of {key}")
    start_time = time.time()

    _, ext = os.path.splitext(key)
    if ext != ".mp3" and ext != ".mp4":
        raise ValueError("Invalid Key")

    Session = sessionmaker(bind=engine)
    session = Session()

    file = (
        session.query(FileObject)
        .filter(func.trim(FileObject.key) == key.replace("\t", ""))
        .first()
    )

    # We verify that there is a file object. Else we create one
    if not file:
        print("--File could not be found")
        return
    else:
        if file.isTranscribed:
            print("Cannot transcribe an audio track twice")
            return

        if file.isProcessing:
            print("Existing Mutex Lock....")
            elapsed_time = datetime.now() - file.startedprocessing
            minutes = int(elapsed_time.total_seconds() // 60)
            seconds = int(elapsed_time.total_seconds() % 60)
            if elapsed_time < THRESHOLD:
                print(
                    f"{minutes} minutes and {seconds} seconds have passed. Threshold is 30 minutes."
                )
                return
            print(
                f"{minutes} minutes and {seconds} seconds have passed. Ignoring Mutex Lock"
            )

    # Now we start a mutex lock on it
    file.isProcessing = True
    file.startedprocessing = datetime.now()
    session.commit()

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        try:
            obj = s3.Object(settings.BUCKET_NAME, key).load()
            if not obj:
                print(f"File with key:{key} does not exist ")
                return
            s3.download_fileobj(settings.BUCKET_NAME, key, temp_file)
        except Exception as e:
            print("File could not be found")
            file.isProcessing = False
            session.commit()

        print(temp_file.name)
        # # s3.download_file(settings.BUCKET_NAME, key, "./test.mp4")
        audio = AudioSegment.from_file(temp_file.name, ext[1:])
        print(f"Audio has a length of {len(audio)/1000}")
        second = 1 * 1000
        step = 120 * second
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
        transcript = " ".join(res)

        file.isProcessing = False
        file.isTranscribed = True
        file.transcript = transcript
        session.commit()

        print(f"Generated Transcript was {res}")
        print(
            "Time took to process the request and return response is {} sec".format(
                time.time() - start_time
            )
        )


@app.post("/generate-transcript")
async def create_upload_file(key: str, background_tasks: BackgroundTasks):
    print(f"Recieved request to generate transcript for {key}")
    background_tasks.add_task(create_transcript, key)
    return {"Message": "Ok"}
