from fastapi import BackgroundTasks, Depends, HTTPException
from fastapi import FastAPI
from pydub import AudioSegment
from fastapi import FastAPI, File, UploadFile
import os
import tempfile
from pydantic import BaseModel, BaseSettings, Field
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
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status
import typing as t
from fastapi.security import OAuth2PasswordBearer
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
import json


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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key != settings.SECRET_JWT_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Forbidden"
        )


# Configure other stuff
openai.api_key = settings.OPENAI_API_KEY
s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
model_name = 'text-davinci-003'
temperature = 0.2
model = OpenAI(model_name=model_name, temperature=temperature, openai_api_key=settings.OPENAI_API_KEY)

class PromptRequest(BaseModel):
    notes: str

class RePromptRequest(BaseModel):
    notes: str
    reprompt: str
    previousResponse: str

class ActionRequest(BaseModel):
    notes: str
    previousResponse: str

class ActionResponse(BaseModel):
    recipient: t.List[str] = Field(description = "comma separated list of name(s) of recipient(s)")
    email: str = Field(description = "verbose, complete, eloquent follow-up email to be sent to recipient(s)")
    collaterals: str = Field(description = "comma separated list of description of possible collaterals to be created and to be sent to recipient(s)")

class ActionResponseList(BaseModel):
    actions: t.List[ActionResponse] = Field(description = "list of possible emails to be sent to recipient(s)")


# Pydantic datastructures
class Summary(BaseModel):
    date: str = Field(description = "date of conversation")
    prospect: str = Field(description = "comma separated list of name(s) of prospect(s)")
    company: str = Field(description = "name(s) of company or organisation that prospect(s) work for")
    summary: str = Field(description = "efficiently summarised conversation, detailed, specific, non-verbose")
    actions: str = Field(description = "comma separated list of efficiently summarised actionables, non-verbose")


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


@app.post("/generate-summary", dependencies=[Depends(api_key_auth)])
async def generate_summary(request: PromptRequest):
    print("---Generating Summary")
    data = request.dict()
    notes = data['notes']

    parser = PydanticOutputParser(pydantic_object=Summary)

    prompt = PromptTemplate(
        template="Please extract the required information accurately and match the specified field names and descriptions. Only use information explicitly stated and return '' if information cannot be found.\n{format_instructions}\nHere are the meeting notes:\n{summary}",
        input_variables=["summary"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    print(prompt.format(summary=notes))

    output = model(prompt.format(summary=notes))
    print(output)
    print({"summary": parser.parse(output)})

    return {"summary": parser.parse(output)}


@app.post("/generate-actions", dependencies=[Depends(api_key_auth)])
async def generate_actions(request: ActionRequest):
    print("---Generating Actions")
    data = request.dict()
    notes = data['notes']
    previousResponse = data['previousResponse']

    parser = PydanticOutputParser(pydantic_object=ActionResponse)

    prompt = PromptTemplate(
        template="Please help generate good follow-up emails for the meeting. Except for collaterals, only use information explicitly stated and return '' if information cannot be found.\n{format_instructions}\nHere are the meeting notes:\n{summary}\n Here is an effective summary of those notes: {previous_response}",
        input_variables=["summary", "previous_response"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    output = model(prompt.format(summary=notes, previous_response=previousResponse))
    print(output)
    print({"actions": parser.parse(output)})
    return {"actions": parser.parse(output)}


# async def summarize(request, notes):
#     print("---Generating Summary")
#     data = await request.json()
#     notes = data['notes']

#     parser = PydanticOutputParser(pydantic_object=Summary)

#     prompt = PromptTemplate(
#         template="Please extract the required information accurately and match the specified field names and descriptions. Only use information explicitly stated and return '' if information cannot be found.\n{format_instructions}\nHere are the meeting notes:\n{summary}",
#         input_variables=["summary"],
#         partial_variables={"format_instructions": parser.get_format_instructions()}
#     )

#     output = model(prompt.format(summary=notes))

#     return {"summary": parser.parse(output)}

@app.post("/reprompt-summary", dependencies=[Depends(api_key_auth)])
async def reprompt(request: RePromptRequest):
    print("---Re-generating Summary")
    data = request.dict()
    notes = data['notes']
    reprompt = data['reprompt']
    previousResponse = data['previousResponse']

    parser = PydanticOutputParser(pydantic_object=Summary)

    prompt = PromptTemplate(
        template="Extract the required information accurately, matching the specified field names and descriptions. Only use explicitly stated information and return '' if any information cannot be found.\nFormat Instructions:{format_instructions}\nMeeting Notes:{summary}\nPlease revise your previous response: {previous_response} using the following instructions: {reprompt}",
        input_variables=["summary", "previous_response", "reprompt"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    output = model(
        prompt.format(summary=notes,
                      reprompt=reprompt,
                      previous_response=json.dumps(previousResponse)))

    return {"summary": parser.parse(output)}

@app.post("/delete-file", dependencies=[Depends(api_key_auth)])
async def delete_file(key: str):
    # We validate that a file exists
    try:
        print(f"Recieved request to delete {key}")
        res = s3.delete_object(Bucket=settings.BUCKET_NAME, Key=key)
        print(res)
        return {"Message": "Ok"}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Item not found")


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

        except Exception as e:
            print("File could not be found")
            file.isProcessing = False
            session.commit()

        s3.download_fileobj(settings.BUCKET_NAME, key, temp_file)
        print(
            f"---Succesfully downloaded file from {settings.BUCKET_NAME} with key : {temp_file.name}, ext: {ext[1:]}"
        )
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


@app.post("/generate-transcript", dependencies=[Depends(api_key_auth)])
async def create_upload_file(key: str, background_tasks: BackgroundTasks):
    print(f"Recieved request to generate transcript for {key}")
    background_tasks.add_task(create_transcript, key.strip())
    return {"Message": "Ok"}
