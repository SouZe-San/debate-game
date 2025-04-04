from minio import Minio
import json
import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


# MinIO Configuration
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

# MinIO Configuration
MINIO_ENDPOINT = "localhost:9000"  # Change if MinIO is running remotely
BUCKET_NAME = "debate-history"

# Initialize MinIO Client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Set to True if using HTTPS
)

print("*********** this is From minio-bucket.py **********")
# Ensure the bucket exists
def create_bucket():
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' created.")
    else:
        print(f"Bucket '{BUCKET_NAME}' already exists.")

# Save debate history as a JSON file in MinIO
def save_debate_history(game_id, player1, player2, topic, arguments, winner):
    filename = f"debate_{game_id}.json"
    
    # Create JSON data
    debate_data = {
        "game_id": game_id,
        "player_1": player1,
        "player_2": player2,
        "topic": topic,
        "arguments": arguments,
        "winner": winner,
        "timestamp": str(datetime.datetime.utcnow())
    }
    
    # Convert JSON to string
    json_data = json.dumps(debate_data, indent=4)

    # Save to a temporary file and upload
    temp_file = f"tmp/{filename}"
    with open(temp_file, "w") as file:
        file.write(json_data)

    # Upload to MinIO
    minio_client.fput_object(BUCKET_NAME, filename, temp_file)
    print(f"[INFO] Debate history saved as {filename} in MinIO.")

# Retrieve debate history from MinIO
def get_debate_history(game_id):
    filename = f"debate_{game_id}.json"

    try:
        # Download file
        minio_client.fget_object(BUCKET_NAME, filename, f"/tmp/{filename}")

        # Read and parse JSON
        with open(f"/tmp/{filename}", "r") as file:
            data = json.load(file)
            return data
    except Exception as e:
        print(f"[ERROR] Could not retrieve debate history: {str(e)}")
        return None
    
# Function to list all objects in a bucket


def list_bucket_contents(bucket_name=BUCKET_NAME):
    try:
        # List all objects in the bucket
        objects = minio_client.list_objects(bucket_name, recursive=True)

        print(f"\nContents of bucket '{bucket_name}':")
        print("-" * 50)

        # Iterate through objects and print details
        found = False
        for obj in objects:
            found = True
            print(f"Object: {obj.object_name}")
            print(f"Size: {obj.size} bytes")
            print(f"Last Modified: {obj.last_modified}")
            print("-" * 50)

        if not found:
            print("Bucket is empty.")

        return objects
    except Exception as e:
        print(f"[ERROR] Could not list bucket contents: {str(e)}")
        return None

# Example usage
if __name__ == "__main__":
    try:
        create_bucket()

        # Example arguments
        arguments = [
            {"player": "Debater1", "round": 1, "argument": "AI judges are more objective."},
            {"player": "Debater2", "round": 1, "argument": "Human judges understand context better."}
        ]

        # Save a sample debate history
        save_debate_history(game_id=1, player1="Debater1", player2="Debater2", topic="Should AI replace human judges?", arguments=arguments, winner="Debater1")

        # Retrieve and print debate history
        history = get_debate_history(1)
        print(list_bucket_contents())
    except Exception as e:
        print(f"[ERROR] An error occurred: {str(e)}")
