# models.py
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class Player(BaseModel):
    username: str
    total_score: int = 0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    created_at: datetime = datetime.now()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Room(BaseModel):
    room_key: str
    topic: str
    player1_name: str
    player2_name: Optional[str] = None
    current_round: int = 1
    status: str = "waiting"  # waiting, pending_acceptance, in_progress, completed
    arguments: Dict[str, List[str]] = {}
    current_turn: Optional[str] = None
    created_at: datetime = datetime.now()
    invitation_accepted: bool = False


class JoinRoom(BaseModel):
    player_name: str


class TopicResponse(BaseModel):
    topics: List[str]

class Argument(BaseModel):
    argument: str
