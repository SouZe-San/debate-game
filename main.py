from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import json
import os
import uvicorn
from dotenv import load_dotenv
from minio import Minio
import random
import string
from ai_engine import run_debate

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "sayan")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin123")
MINIO_BUCKET = "debate-history"

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Ensure bucket exists
if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)

# In-memory storage for active debate rooms
debate_rooms: Dict[str, dict] = {}

# Models


class Room(BaseModel):
    room_key: str
    topic: str
    player1_name: str
    player2_name: Optional[str] = None
    current_round: int = 1
    status: str = "waiting"  # waiting, in_progress, completed
    arguments: Dict[str, List[str]] = {}
    current_turn: Optional[str] = None
    created_at: datetime = datetime.now()


class JoinRoom(BaseModel):
    player_name: str


class Argument(BaseModel):
    argument: str

# Helper Functions


def generate_room_key(length: int = 6) -> str:
    """Generate a random room key"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# API Endpoints


@app.post("/create-room/{player_name}")
async def create_room(player_name: str):
    """Create a new debate room"""
    room_key = generate_room_key()

    # Get random topic from ai_engine
    debate_result = run_debate()
    topic = debate_result["topic"]

    room = Room(
        room_key=room_key,
        topic=topic,
        player1_name=player_name,
        arguments={player_name: []}
    )

    debate_rooms[room_key] = room.dict()

    return {"room_key": room_key, "topic": topic}


@app.post("/join-room/{room_key}")
async def join_room(room_key: str, join_request: JoinRoom):
    """Join an existing debate room"""
    if room_key not in debate_rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    room = debate_rooms[room_key]
    if room["player2_name"]:
        raise HTTPException(status_code=400, detail="Room is full")

    room["player2_name"] = join_request.player_name
    room["status"] = "in_progress"
    room["current_turn"] = room["player1_name"]
    room["arguments"][join_request.player_name] = []

    return {"message": "Joined successfully", "room": room}


@app.post("/submit-argument/{room_key}/{player_name}")
async def submit_argument(room_key: str, player_name: str, argument: Argument):
    """Submit an argument for the current round"""
    if room_key not in debate_rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    room = debate_rooms[room_key]

    if room["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Debate not in progress")

    if player_name != room["current_turn"]:
        raise HTTPException(status_code=400, detail="Not your turn")

    # Add argument
    room["arguments"][player_name].append(argument.argument)

    # Switch turns
    room["current_turn"] = room["player2_name"] if player_name == room["player1_name"] else room["player1_name"]

    # Check if round is complete
    if len(room["arguments"][room["player1_name"]]) == 5 and len(room["arguments"][room["player2_name"]]) == 5:
        # Run debate evaluation
        result = run_debate(
            topic=room["topic"],
            player1_name=room["player1_name"],
            player1_arguments=room["arguments"][room["player1_name"]],
            player2_name=room["player2_name"],
            player2_arguments=room["arguments"][room["player2_name"]]
        )

        # Store result in MinIO
        debate_data = json.dumps(result).encode('utf-8')
        minio_client.put_object(
            MINIO_BUCKET,
            f"debate_{room_key}.json",
            data=debate_data,
            length=len(debate_data)
        )

        room["status"] = "completed"
        return {"status": "completed", "result": result}

    return {
        "status": "in_progress",
        "current_round": len(room["arguments"][player_name]),
        "next_turn": room["current_turn"]
    }


@app.get("/room-status/{room_key}")
async def get_room_status(room_key: str):
    """Get current status of the debate room"""
    if room_key not in debate_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return debate_rooms[room_key]


@app.get("/debate/{debate_id}")
async def get_debate(debate_id: str):
    """Retrieve a completed debate from MinIO"""
    try:
        response = minio_client.get_object(
            MINIO_BUCKET, f"debate_{debate_id}.json")
        return json.loads(response.data.decode('utf-8'))
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Debate not found: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
