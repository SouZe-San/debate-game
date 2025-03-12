from fastapi import FastAPI, HTTPException
from models import Room, JoinRoom, Argument, Player, TopicResponse
from player_service import PlayerService
import os
from dotenv import load_dotenv
from minio import Minio
from ai_engine import run_debate, generate_debate_topics_by_genre
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

# Valid genres for debate topics
VALID_GENRES = [
    "sports",
    "cinema",
    "philosophy",
    "music",
    "geopolitics",
    "brainrot"
]

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


@app.get("/topics/{genre}", response_model=TopicResponse)
async def get_debate_topics(genre: str):
    """Get three debate topics for a specific genre"""
    if genre.lower() not in VALID_GENRES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid genre",
                "valid_genres": VALID_GENRES
            }
        )

    topics = generate_debate_topics_by_genre(genre)
    return topics


@app.post("/register")
async def register_player(username: str):
    """Register a new player"""
    try:
        player = await player_service.create_player(username)
        return {"message": f"Player {username} registered successfully", "player": player}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create-room/{player_name}")
async def create_room(player_name: str, genre: str = None):
    """Create a new debate room with optional genre-specific topic"""
    # Verify player exists
    player = await player_service.get_player(player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    room_key = generate_room_key()

    # Generate topic based on genre if provided
    if genre:
        if genre.lower() not in VALID_GENRES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid genre. Valid genres are: {', '.join(VALID_GENRES)}"
            )
        topics = generate_debate_topics_by_genre(genre)
        topic = random.choice(topics["topics"])
    else:
        topic = run_debate()["topic"]

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


@app.post("/players/create")
async def create_player(player_name: str):
    """Create a new player"""
    try:
        # Create a new player using PlayerService
        player = await player_service.create_player(player_name)
        return {"message": f"Player {player_name} created successfully", "player": player}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/players/{username}")
async def get_player(username: str):
    """Get player details"""
    player = await player_service.get_player(username)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
