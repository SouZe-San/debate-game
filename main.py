from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ai_engine import run_debate
from minio import Minio
import json
import os
import uvicorn

# Initialize FastAPI app
app = FastAPI()

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = "debate-results"

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Set to True if using HTTPS
)

# Ensure bucket exists
if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)


class DebateRequest(BaseModel):
    topic: str
    player1_name: str
    player1_argument: str
    player2_name: str
    player2_argument: str
    game_id: int = None  # Optional game ID


@app.post("/debate/")
def start_debate(request: DebateRequest):
    """
    API endpoint to run a debate, score arguments, determine the winner, and store results.
    """
    try:
        result = run_debate(
            request.topic,
            request.player1_name,
            request.player1_argument,
            request.player2_name,
            request.player2_argument,
            request.game_id
        )

        # Save debate result to MinIO
        debate_id = f"debate_{request.game_id if request.game_id else 'latest'}.json"
        debate_data = json.dumps(result).encode("utf-8")

        minio_client.put_object(
            MINIO_BUCKET,
            debate_id,
            data=debate_data,
            length=len(debate_data),
            content_type="application/json"
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debate/{debate_id}")
def get_debate(debate_id: str):
    """
    API endpoint to retrieve a past debate result from MinIO.
    """
    try:
        response = minio_client.get_object(
            MINIO_BUCKET, f"debate_{debate_id}.json")
        return json.loads(response.data.decode("utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Debate ID {debate_id} not found.")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
