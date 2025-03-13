import json
from typing import Optional
from models import Player
from minio import Minio
from fastapi import HTTPException
from io import BytesIO


class PlayerService:
    def __init__(self, minio_client: Minio, bucket_name: str):
        self.minio_client = minio_client
        self.bucket_name = bucket_name

    async def get_player(self, username: str) -> Optional[Player]:
        try:
            response = self.minio_client.get_object(
                self.bucket_name,
                f"player_{username}.json"
            )
            data = response.read()  # Properly read the MinIO response
            player_data = json.loads(data.decode('utf-8'))
            return Player(**player_data)
        except Exception as e:
            return None

    async def create_player(self, username: str) -> Player:
        if await self.get_player(username):
            raise HTTPException(
                status_code=400, detail="Username already exists")

        player = Player(username=username)
        await self.save_player(player)
        return player

    async def save_player(self, player: Player):
        # Use model_dump_json() instead of json() for Pydantic v2
        # And wrap the bytes in BytesIO for MinIO

        player_data = player.model_dump_json().encode('utf-8')
        self.minio_client.put_object(
        self.bucket_name,
        f"player_{player.username}.json",
        BytesIO(player_data),  # Wrap in BytesIO
        length=len(player_data)
    )

    async def update_scores(self, winner: str, loser: str, winner_score: int, loser_score: int):
        winner_profile = await self.get_player(winner)
        loser_profile = await self.get_player(loser)

        if not winner_profile or not loser_profile:
            raise HTTPException(status_code=404, detail="Player not found")

        score_diff = abs(winner_score - loser_score)

        winner_profile.total_score += score_diff
        winner_profile.wins += 1
        winner_profile.games_played += 1

        loser_profile.total_score -= score_diff
        loser_profile.losses += 1
        loser_profile.games_played += 1

        await self.save_player(winner_profile)
        await self.save_player(loser_profile)
