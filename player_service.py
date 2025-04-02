import json
from typing import Optional, List
from models import Player
from minio import Minio
from fastapi import HTTPException
from io import BytesIO


class PlayerService:
    def __init__(self, minio_client: Minio, bucket_name: str):
        self.minio_client = minio_client
        self.bucket_name = bucket_name

    async def get_player(self, username: str) -> Optional[Player]:
        """Get a player by username"""
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
        """Create a new player"""
        if await self.get_player(username):
            raise HTTPException(
                status_code=400, detail="Username already exists")

        player = Player(username=username)
        await self.save_player(player)
        return player

    async def save_player(self, player: Player):
        """Save player data to MinIO"""
        player_data = player.model_dump_json().encode('utf-8')
        self.minio_client.put_object(
            self.bucket_name,
            f"player_{player.username}.json",
            BytesIO(player_data),  # Wrap in BytesIO
            length=len(player_data)
        )

    async def apply_abort_penalty(self, username: str) -> Player:
        """Apply a -30 penalty to a player's score for aborting a debate"""
        player = await self.get_player(username)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Apply -30 penalty
        player.total_score = max(0, player.total_score - 30)  # Prevent negative scores
        player.games_played += 1

        # Save the updated player data
        await self.save_player(player)

        return player

    async def update_scores(self, winner: str, loser: str, winner_score: int, loser_score: int):
        """Update player scores after a debate"""
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

    async def get_all_players(self) -> List[Player]:
        """Get all players for ranking"""
        players = []
        try:
            # List all objects in the bucket with player_ prefix
            objects = self.minio_client.list_objects(
                self.bucket_name, 
                prefix="player_", 
                recursive=True
            )
            
            for obj in objects:
                try:
                    response = self.minio_client.get_object(
                        self.bucket_name, 
                        obj.object_name
                    )
                    data = response.read()
                    player_data = json.loads(data.decode('utf-8'))
                    players.append(Player(**player_data))
                except Exception as e:
                    print(f"Error loading player data: {e}")
                    continue
        except Exception as e:
            print(f"Error listing players: {e}")
        
        return players