# main.py
from fastapi import FastAPI, HTTPException
from models import Room, JoinRoom, Argument, Player
from player_service import PlayerService
import os
from dotenv import load_dotenv
from minio import Minio
from ai_engine import run_debate
import random
import string
import json

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

# Initialize services
player_service = PlayerService(minio_client, MINIO_BUCKET)

# In-memory storage for active debate rooms
debate_rooms: dict[str, dict] = {}


def generate_room_key(length: int = 6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@app.post("/players/create/{username}")
async def create_player(username: str):
    """Create a new player profile"""
    player = await player_service.create_player(username)
    return {"message": "Player created successfully", "player": player}


@app.get("/players/{username}")
async def get_player_profile(username: str):
    """Get player profile"""
    player = await player_service.get_player(username)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.post("/create-room/{player_name}")
async def create_room(player_name: str):
    """Create a new debate room"""
    # Verify player exists
    player = await player_service.get_player(player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    room_key = generate_room_key()
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
    # Verify player exists
    player = await player_service.get_player(join_request.player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

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
    """Submit an argument and handle scoring"""
    if room_key not in debate_rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    room = debate_rooms[room_key]

    if room["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Debate not in progress")

    if player_name != room["current_turn"]:
        raise HTTPException(status_code=400, detail="Not your turn")

    room["arguments"][player_name].append(argument.argument)
    room["current_turn"] = room["player2_name"] if player_name == room["player1_name"] else room["player1_name"]

    if len(room["arguments"][room["player1_name"]]) == 5 and len(room["arguments"][room["player2_name"]]) == 5:
        result = run_debate(
            topic=room["topic"],
            player1_name=room["player1_name"],
            player1_arguments=room["arguments"][room["player1_name"]],
            player2_name=room["player2_name"],
            player2_arguments=room["arguments"][room["player2_name"]]
        )

        # Update player scores
        winner = result["winner"]
        loser = room["player2_name"] if winner == room["player1_name"] else room["player1_name"]
        winner_score = result["players"]["player1" if winner ==
                                         room["player1_name"] else "player2"]["rounds_won"]
        loser_score = result["players"]["player1" if loser ==
                                        room["player1_name"] else "player2"]["rounds_won"]

        await player_service.update_scores(winner, loser, winner_score, loser_score)

        # Store debate result
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
    if room_key not in debate_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return debate_rooms[room_key]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
