from fastapi import FastAPI
from dotenv import load_dotenv
import os
import redis

load_dotenv()

app = FastAPI()

r = redis.Redis.from_url(os.getenv("REDIS_URL"))


@app.get("/")
def root():
    return {"message": "UP2U backend is alive"}
