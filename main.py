from fastapi import FastAPI, HTTPException, Query
from models import Player, Room, JoinRoom, Argument, TopicResponse
from player_service import PlayerService
import os
from dotenv import load_dotenv
from minio import Minio
from ai_engine import run_debate, generate_debate_topics_by_genre
import random
import string
import json
from io import BytesIO
import uvicorn
from fastapi.middleware.cors import CORSMiddleware


# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Debate API", description="API for managing debate players and rooms")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=["*"],
    max_age=36000
)
# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = "debate-history"

if(MINIO_ACCESS_KEY is None or MINIO_SECRET_KEY is None):
    raise ValueError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set in the environment variables.")

# Valid genres for debate topics
VALID_GENRES = [
    "sports",
    "cinema",
    "philosophy",
    "music",
    "geopolitics",
    "brainrot"
]

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Ensure bucket exists
if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)
    
player_service = PlayerService(minio_client, MINIO_BUCKET)

debate_rooms: dict[str, dict] = {}

def generate_room_key(length: int = 6) -> str:
    """Generate a random room key"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

#0. Health check
@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "OK", "message": "Debate API is running"}

# 1. Create a new player
@app.post("/players/create")
async def create_player(player: dict):
    """Create a new player"""
    player_name = player["player_name"]
    try:
        player = await player_service.create_player(player_name)
        return {"message": f"Player {player_name} created successfully", "player": player}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Verify user ID
@app.get("/players/{username}")
async def get_player(username: str):
    """Get player details to verify existence"""
    player = await player_service.get_player(username)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

#past match history and rankings
@app.get("/player/history/{username}")
async def get_player_history(username: str):
    """Get player match history and ranking information"""
    player = await player_service.get_player(username)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
   
    all_players = await player_service.get_all_players()
    
    ranked_players = sorted(all_players, key=lambda x: x.total_score, reverse=True)
    player_rank = next((i + 1 for i, p in enumerate(ranked_players) if p.username == username), None)
    
    debate_history = []
    try:
        objects = minio_client.list_objects(MINIO_BUCKET, prefix="debate_", recursive=True)
        for obj in objects:
            try:
                response = minio_client.get_object(MINIO_BUCKET, obj.object_name)
                data = json.loads(response.read().decode('utf-8'))
                
                if data.get("players", {}).get("player1", {}).get("name") == username or \
                   data.get("players", {}).get("player2", {}).get("name") == username:
                    debate_history.append(data)
            except:
                continue
    except Exception as e:
        print(f"Error fetching debate history: {e}")
    
    return {
        "player": player,
        "rank": player_rank,
        "total_players": len(ranked_players),
        "debate_history": debate_history
    }

# 4. Send list of genres
@app.get("/genres")
async def get_genres():
    """Get list of available debate genres"""
    return {"genres": VALID_GENRES}

@app.get("/topics/{genre}", response_model=TopicResponse)
async def get_debate_topics(genre: str):
    """Get three debate topics for a specific genre"""
    if genre.lower() not in VALID_GENRES:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid genre", "valid_genres": VALID_GENRES}
        )

    topics = generate_debate_topics_by_genre(genre)
    return topics

@app.post("/create-room/{player_name}")
async def create_room(player_name: str, topic: str = Query(..., description="Selected debate topic")):
    """Create a new debate room with the selected topic"""
    player = await player_service.get_player(player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Generate room key
    room_key = generate_room_key()

    # Create room
    room = Room(
        room_key=room_key,
        topic=topic.strip(),
        player1_name=player_name,
        arguments={player_name: []}
    )

    debate_rooms[room_key] = room.dict()
    return {"room_key": room_key, "topic": topic}


@app.post("/join-room/{room_key}")
async def join_room(room_key: str, join_request: JoinRoom):
    """Join an existing debate room"""
    
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

#Submit arguments for each round
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

    room["arguments"][player_name].append(argument.argument)
  
    # Determine current round
    player1_arguments = room["arguments"][room["player1_name"]]
    player2_arguments = room["arguments"].get(room["player2_name"], [])
    current_round = min(len(player1_arguments), len(player2_arguments)) + (1 if player_name == room["player1_name"] else 0)
    
    round_result = None
    if len(player1_arguments) == len(player2_arguments):
        # Both players have submitted arguments for this round
        if len(player1_arguments) <= 5:  # Process rounds 1-5
            # Score the current round
            p1_arg = player1_arguments[-1]
            p2_arg = player2_arguments[-1]
            round_result = {
                "round": len(player1_arguments),
                "player1": {
                    "name": room["player1_name"],
                    "argument": p1_arg
                },
                "player2": {
                    "name": room["player2_name"],
                    "argument": p2_arg
                },
                "scores": run_debate(
                    topic=room["topic"],
                    player1_name=room["player1_name"],
                    player1_arguments=[p1_arg],
                    player2_name=room["player2_name"],
                    player2_arguments=[p2_arg],
                    game_id=f"{room_key}_round_{len(player1_arguments)}"
                )["rounds"][0]
            }
    
    # Switch turns
    room["current_turn"] = room["player2_name"] if player_name == room["player1_name"] else room["player1_name"]

    #Check if debate is complete (5 rounds)
    if len(player1_arguments) == 5 and len(player2_arguments) == 5:
        result = run_debate(
            topic=room["topic"],
            player1_name=room["player1_name"],
            player1_arguments=player1_arguments,
            player2_name=room["player2_name"],
            player2_arguments=player2_arguments,
            game_id=room_key
        )

        winner = result["winner"]
        loser = room["player2_name"] if winner == room["player1_name"] else room["player1_name"]
        winner_score = result["players"]["player1" if winner == room["player1_name"] else "player2"]["rounds_won"]
        loser_score = result["players"]["player1" if loser == room["player1_name"] else "player2"]["rounds_won"]

        await player_service.update_scores(winner, loser, winner_score, loser_score)

        debate_data = json.dumps(result).encode('utf-8')
        minio_client.put_object(
            MINIO_BUCKET,
            f"debate_{room_key}.json",
            BytesIO(debate_data),
            length=len(debate_data)
        )

        room["status"] = "completed"
        return {
            "status": "completed", 
            "current_round": current_round,
            "round_result": round_result,
            "final_result": result
        }

    return {
        "status": "in_progress",
        "current_round": current_round,
        "round_result": round_result,
        "next_turn": room["current_turn"]
    }

@app.post("/abort-debate/{room_key}/{player_name}")
async def abort_debate(room_key: str, player_name: str):
    """Allow a player to abort a debate with a score penalty"""
    if room_key not in debate_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = debate_rooms[room_key]
    
    # Check if player is part of this debate
    if player_name != room["player1_name"] and player_name != room["player2_name"]:
        raise HTTPException(status_code=403, detail="Player not in this debate")
    
    # Check if debate is in progress
    if room["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Debate is not in progress")
    
    # Apply penalty to the player who aborted
    await player_service.apply_abort_penalty(player_name)
    
    # Update room status
    room["status"] = "aborted"
    room["aborted_by"] = player_name
    
    return {
        "status": "aborted",
        "message": f"Debate aborted by {player_name}. A 30-point penalty has been applied.",
        "player": player_name
    }


# Get current room status
@app.get("/room-status/{room_key}")
async def get_room_status(room_key: str):
    """Get the current status of a debate room"""
    if room_key not in debate_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    
    room = debate_rooms[room_key]
    # @souze - i dont know if this is logic is ok or not
    # get all arguments in One Array in entry sequence {one by one , p1,p2}
# [ {player:p1, arg:" "}, {player:p2, arg:""} ,{player:p1, arg:" "}, {player:p2, arg:""}]
    all_arguments = []
    for i in range(max(len(room["arguments"][room["player1_name"]]), len(room["arguments"].get(room["player2_name"], [])))):
        if i < len(room["arguments"][room["player1_name"]]):
            all_arguments.append({"player": room["player1_name"], "argument": room["arguments"][room["player1_name"]][i]})
        if i < len(room["arguments"].get(room["player2_name"], [])):
            all_arguments.append({"player": room["player2_name"], "argument": room["arguments"][room["player2_name"]][i]})
    
    return {"room": room, "all_arguments": all_arguments}

if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000,reload=True)
