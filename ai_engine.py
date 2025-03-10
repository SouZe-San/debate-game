import os
import json
import requests
import datetime
from dotenv import load_dotenv
from minio import Minio
import re

# Load API Key from .env
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Your MinIO Configuration
MINIO_ENDPOINT = "localhost:9000"  # Change if MinIO is running remotely
ACCESS_KEY = "sayan"
SECRET_KEY = "admin123"
BUCKET_NAME = "debate-history"

# Initialize MinIO Client
MINIO_CLIENT = Minio(
    MINIO_ENDPOINT,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=False  # Set to True if using HTTPS
)

# Ensure the bucket exists
def create_bucket():
    if not MINIO_CLIENT.bucket_exists(BUCKET_NAME):
        MINIO_CLIENT.make_bucket(BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' created.")
    else:
        print(f"Bucket '{BUCKET_NAME}' already exists.")

def print_full_response(response, label="API Response"):
    """Helper function to print full API response for debugging"""
    print(f"\n--- {label} ---")
    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=2))
    except:
        print("Raw response:", response.text)
    print("-------------------\n")

def score_argument(argument, topic):
    """
    Uses OpenRouter API to score an argument based on Logic, Relevance, and Persuasiveness.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://debate-app.example.com"
    }

    # Using GPT-3.5-turbo as it's more commonly available
    payload = {
        "model": "openai/gpt-4o-mini", 
        "messages": [
            {
                "role": "user", 
                "content": f"""
You are a debate judge. Score the following argument based on three criteria (0-10):
- Logic: How well-reasoned is the argument?
- Relevance: How related is the argument to the topic?
- Persuasiveness: How convincing is the argument?
- Deduct points for fallacies, irrelevant points, or lack of evidence. humour can be entertained.

Debate Topic: {topic}
Argument: "{argument}"

Your response must be a valid JSON object with exactly these three numeric fields:
{{
  "logic": 7.5,
  "relevance": 8.0,
  "persuasiveness": 7.0
}}
"""
            }
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}  # Request JSON response format
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        print_full_response(response, "Score Response")
        try:
            response_data = response.json()
            # Extract content from the OpenRouter response structure
            message_content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if message_content:
                try:
                    # Parse the JSON directly
                    scores = json.loads(message_content)
                    # Validate the scores
                    if all(key in scores for key in ["logic", "relevance", "persuasiveness"]):
                        return scores
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON from: {message_content}")
            
            print("Using default scores")
            return {"logic": 5.0, "relevance": 5.0, "persuasiveness": 5.0}
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            return {"logic": 5.0, "relevance": 5.0, "persuasiveness": 5.0}
    else:
        print(f"API Error ({response.status_code}):", response.text)
        return {"logic": 5.0, "relevance": 5.0, "persuasiveness": 5.0}
    
def sanitize_filename(filename):
    """Removes invalid characters from the filename"""
    return re.sub(r'[\/:*?"<>|]', '_', filename)

def generate_judgment(player1, player2, topic):
    """
    Uses OpenRouter API to generate a judgment explaining why one player won.
    """
    # Determine winner based on scores
    player1_total = player1["score"]["total"]
    player2_total = player2["score"]["total"]
    
    if player1_total > player2_total:
        default_winner = player1["nickname"]
        default_reason = f"{player1['nickname']} had a higher overall score ({player1_total:.1f} vs {player2_total:.1f})."
    elif player2_total > player1_total:
        default_winner = player2["nickname"]
        default_reason = f"{player2['nickname']} had a higher overall score ({player2_total:.1f} vs {player1_total:.1f})."
    else:
        default_winner = "Tie"
        default_reason = f"Both players had equal scores of {player1_total:.1f}."
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://debate-app.example.com"
    }

    # Using GPT-3.5-turbo as it's more commonly available
    payload = {
        "model": "openai/gpt-4o-mini", 
        "messages": [
            {
                "role": "user", 
                "content": f"""
You are an expert debate judge. The debate topic was: "{topic}".

Player 1: {player1['nickname']}
- Logic: {player1['score']['logic']}
- Relevance: {player1['score']['relevance']}
- Persuasiveness: {player1['score']['persuasiveness']}
- Total Score: {player1['score']['total']}

Player 2: {player2['nickname']}
- Logic: {player2['score']['logic']}
- Relevance: {player2['score']['relevance']}
- Persuasiveness: {player2['score']['persuasiveness']}
- Total Score: {player2['score']['total']}

Based on the scores, declare the winner and explain the reason.

Your response must be a valid JSON object with exactly these two fields:
{{
  "winner": "{default_winner}",
  "reason": "Explanation for why this player won"
}}
"""
            }
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}  # Request JSON response format
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        print_full_response(response, "Judgment Response")
        try:
            response_data = response.json()
            message_content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if message_content:
                try:
                    # Parse the JSON directly
                    judgment = json.loads(message_content)
                    # Validate the judgment
                    if all(key in judgment for key in ["winner", "reason"]):
                        return judgment
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON from: {message_content}")
            
            print("Using default judgment")
            return {"winner": default_winner, "reason": default_reason}
        except Exception as e:
            print(f"Error parsing judgment: {str(e)}")
            return {"winner": default_winner, "reason": default_reason}
    else:
        print(f"API Error ({response.status_code}):", response.text)
        return {"winner": default_winner, "reason": default_reason}

def store_debate_result(debate_data, game_id=None):
    """
    Stores debate results in MinIO using your format.
    """
    if game_id is None:
        # Generate a timestamp-based ID if none provided
        game_id = int(datetime.datetime.now().timestamp())
    
    # Format for your MinIO setup
    arguments = [
        {"player": debate_data["player1"]["nickname"], "argument": debate_data["player1"]["argument"]},
        {"player": debate_data["player2"]["nickname"], "argument": debate_data["player2"]["argument"]}
    ]
    
    # Create the JSON data structure that matches your format
    formatted_data = {
        "game_id": game_id,
        "player_1": debate_data["player1"]["nickname"],
        "player_2": debate_data["player2"]["nickname"],
        "topic": debate_data["topic"],
        "arguments": arguments,
        "winner": debate_data["winner"],
        "scores": {
            debate_data["player1"]["nickname"]: debate_data["player1"]["score"],
            debate_data["player2"]["nickname"]: debate_data["player2"]["score"]
        },
        "reason": debate_data["reason"],
        "timestamp": str(datetime.datetime.utcnow())
    }
    
    filename = f"debate_{game_id}.json"
    
    # Create tmp directory if it doesn't exist
    os.makedirs("tmp", exist_ok=True)
    
    # Save to a temporary file
    temp_file = f"tmp/{filename}"
    with open(temp_file, "w") as file:
        json.dump(formatted_data, file, indent=4)
    
    try:
        # Upload to MinIO
        MINIO_CLIENT.fput_object(BUCKET_NAME, filename, temp_file)
        print(f"[INFO] Debate history saved as {filename} in MinIO.")
    except Exception as e:
        print(f"[ERROR] MinIO storage error: {e}")
        print(f"Results saved locally at: {temp_file}")

def run_debate(topic, player1_name, player1_argument, player2_name, player2_argument, game_id=None):
    """
    Runs a debate, scores arguments, determines the winner, and stores results.
    """
    print(f"Starting debate on topic: {topic}")
    
    # Ensure bucket exists
    create_bucket()
    
    player1 = {"nickname": player1_name, "argument": player1_argument}
    player2 = {"nickname": player2_name, "argument": player2_argument}

    print(f"Scoring {player1_name}'s argument...")
    player1["score"] = score_argument(player1["argument"], topic)
    
    print(f"Scoring {player2_name}'s argument...")
    player2["score"] = score_argument(player2["argument"], topic)

    player1["score"]["total"] = sum(player1["score"].values())
    player2["score"]["total"] = sum(player2["score"].values())

    print("Generating final judgment...")
    judgment = generate_judgment(player1, player2, topic)

    debate_data = {
        "topic": topic,
        "player1": player1,
        "player2": player2,
        "winner": judgment["winner"],
        "reason": judgment["reason"]
    }

    print("Storing debate results...")
    store_debate_result(debate_data, game_id)
    return debate_data

if __name__ == "__main__":
    # Example Debate
    topic = "Should AI replace human judges?"
    player1_name = "DebateMasterX"
    player1_argument = "AI systems can analyze legal precedents and case details with perfect recall and consistency, eliminating human biases that often affect judgments. They can process vast amounts of data quickly, ensuring that all relevant information is considered. AI judges would apply the law uniformly across similar cases, addressing the issue of sentencing disparities that plague our current system."
    player2_name = "LogicWarrior"
    player2_argument = "Justice requires understanding human context and nuance that AI cannot grasp. Judges must weigh complex ethical considerations, show compassion, and understand unspoken cultural contexts. While AI may appear unbiased, it inherits biases from its training data and lacks the critical human ability to recognize when established precedent should be challenged for moral progress in society."

    # Use game_id=1 to match your example
    results = run_debate(topic, player1_name, player1_argument, player2_name, player2_argument, game_id=1)

    print("\nFinal Debate Results:")
    print(json.dumps(results, indent=4))