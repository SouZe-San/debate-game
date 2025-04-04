from minio import Minio
import json
from datetime import datetime
from models import Player  # Import the Player model
from io import BytesIO
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


# MinIO Configuration
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
# Initialize MinIO client
minio_client = Minio(
    "localhost:9000",
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Test player creation
try:
    # Create a Player instance using the model
    test_player = Player(
        username="test_user",
        total_score=0,
        games_played=0,
        wins=0,
        losses=0,
        created_at=datetime.now()
    )

    # Convert player data to JSON string and encode to bytes using model_dump_json()
    player_data = test_player.model_dump_json().encode('utf-8')

    # Upload player data to MinIO
    minio_client.put_object(
        "debate-history",
        f"player_test_user.json",
        BytesIO(player_data),  # Wrap the bytes in BytesIO
        len(player_data)
    )
    print("Player created successfully")

    # Try to read back the player data
    response = minio_client.get_object(
        "debate-history", "player_test_user.json")
    data = response.read().decode('utf-8')  # Read and decode the bytes
    player_dict = json.loads(data)  # Parse JSON string to dict
    print("Retrieved player data:", player_dict)

except Exception as e:
    print(f"Error: {e}")
