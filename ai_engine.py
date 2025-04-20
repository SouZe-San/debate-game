import os
import json
import requests
import datetime
from dotenv import load_dotenv
from minio import Minio
import re
import random

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


# MinIO Configuration
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

# Load API Key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# MinIO Configuration
MINIO_ENDPOINT = "localhost:9000"

BUCKET_NAME = "debate-history"

# Initialize MinIO Client
MINIO_CLIENT = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def create_bucket():
    if not MINIO_CLIENT.bucket_exists(BUCKET_NAME):
        MINIO_CLIENT.make_bucket(BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' created.")
    else:
        print(f"Bucket '{BUCKET_NAME}' already exists.")


def print_full_response(response, label="API Response"):
    print(f"\n--- {label} ---")
    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=2))
    except:
        print("Raw response:", response.text)
    print("-------------------\n")


def generate_debate_topics_by_genre(genre: str) -> dict:
    """
    Generate 3 debate topics for a specific genre using Gemini API
    """
    headers = {
        "Content-Type": "application/json"
    }

    prompt = f"""
    Generate exactly 3 interesting and controversial debate topics related to {genre}.
    The topics should be thought-provoking and suitable for a structured debate.
    Each topic should be a complete question or statement.
    Provide only the 3 topics without any additional text or numbering.
    """

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(
            f"{API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            content = response.json(
            )["candidates"][0]["content"]["parts"][0]["text"]
            topics = [topic.strip()
                      for topic in content.split('\n') if topic.strip()][:3]
            return {"topics": topics}

    except Exception as e:
        print(f"Error generating topics: {e}")

    # Fallback topics based on genres
    fallback_topics = {
        "sports": [
            "Should esports be included in the Olympics?",
            "Should college athletes be paid?",
            "Is VAR improving or ruining football?"
        ],
        "cinema": [
            "Are superhero movies ruining cinema?",
            "Should streaming platforms release all episodes at once?",
            "Are remakes necessary in modern cinema?"
        ],
        "philosophy": [
            "Does free will exist?",
            "Is morality objective or subjective?",
            "Can artificial intelligence be conscious?"
        ],
        "music": [
            "Is streaming helping or hurting musicians?",
            "Has auto-tune ruined modern music?",
            "Should music education be mandatory in schools?"
        ],
        "geopolitics": [
            "Should the UN Security Council be reformed?",
            "Is economic globalization beneficial for all countries?",
            "Should nuclear weapons be globally banned?"
        ],
        "brainrot": [
            "Is cereal a soup?",
            "Do hot dogs qualify as sandwiches?",
            "Should pineapple be allowed on pizza?"
        ]
    }

    return {"topics": fallback_topics.get(genre.lower(), fallback_topics["brainrot"])}


def generate_debate_topic():
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "parts": [{
                "text": "Generate an interesting and controversial debate topic."
            }]
        }]
    }

    try:
        response = requests.post(f"{API_URL}?key={GEMINI_API_KEY}",
                                 headers=headers,
                                 json=payload)
        if response.status_code == 200:
            topic = response.json()[
                "candidates"][0]["content"]["parts"][0]["text"].strip()
            return topic
    except Exception as e:
        print(f"Error generating topic: {e}")

    # Fallback topics
    fallback_topics = [
        "Should social media be regulated by government?",
        "Is universal basic income viable?",
        "Should voting be mandatory?",
        "Is space exploration worth the cost?",
        "Should college education be free?"
    ]
    return random.choice(fallback_topics)

def score_argument_turn(argument, topic, turn_number):
    headers = {
        "Content-Type": "application/json"
    }

    prompt = f"""
    Score this debate argument (Turn {turn_number}/5) on:
    - Logic (0-10)
    - Relevance to topic (0-10)
    - Persuasiveness (0-10)

    Topic: {topic}
    Argument: {argument}

    Respond with only the numerical scores in this format:
    Logic: [score]
    Relevance: [score]
    Persuasiveness: [score]
    """

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(f"{API_URL}?key={GEMINI_API_KEY}",
                                 headers=headers,
                                 json=payload)
        if response.status_code == 200:
            content = response.json(
            )["candidates"][0]["content"]["parts"][0]["text"]
            scores = {
                "logic": float(re.search(r"Logic.*?(\d+(?:\.\d+)?)", content).group(1)),
                "relevance": float(re.search(r"Relevance.*?(\d+(?:\.\d+)?)", content).group(1)),
                "persuasiveness": float(re.search(r"Persuasiveness.*?(\d+(?:\.\d+)?)", content).group(1))
            }
            return scores
    except Exception as e:
        print(f"Error scoring argument: {e}")

    # Return default scores if API fails
    return {"logic": 5.0, "relevance": 5.0, "persuasiveness": 5.0}


def score_debate(player1_arguments, player2_arguments, topic):
    rounds = []
    player1_rounds_won = 0
    player2_rounds_won = 0

    for round_num in range(5):
        print(f"\nScoring Round {round_num + 1}...")

        # Score both arguments for this round
        p1_score = score_argument_turn(
            player1_arguments[round_num], topic, round_num + 1)
        p2_score = score_argument_turn(
            player2_arguments[round_num], topic, round_num + 1)

        # Calculate total scores for this round
        p1_total = sum(p1_score.values())
        p2_total = sum(p2_score.values())

        # Determine round winner
        if p1_total > p2_total:
            round_winner = "Player 1"
            player1_rounds_won += 1
        elif p2_total > p1_total:
            round_winner = "Player 2"
            player2_rounds_won += 1
        else:
            round_winner = "Tie"

        rounds.append({
            "round": round_num + 1,
            "player1_score": p1_score,
            "player2_score": p2_score,
            "round_winner": round_winner
        })

    return {
        "rounds": rounds,
        "player1_rounds_won": player1_rounds_won,
        "player2_rounds_won": player2_rounds_won,
        "overall_winner": "Player 1" if player1_rounds_won > player2_rounds_won else "Player 2" if player2_rounds_won > player1_rounds_won else "Tie"
    }


def run_debate(topic=None, player1_name="Player 1", player1_arguments=None,
               player2_name="Player 2", player2_arguments=None, game_id=None):

    if topic is None:
        topic = generate_debate_topic()

    if not all([len(player1_arguments) == 5, len(player2_arguments) == 5]):
        raise ValueError("Both players must complete all 5 arguments")

    # Score the debate
    scoring_results = score_debate(player1_arguments, player2_arguments, topic)

    # Prepare debate data
    debate_data = {
        "game_id": game_id or int(datetime.datetime.now().timestamp()),
        "topic": topic,
        "players": {
            "player1": {
                "name": player1_name,
                "arguments": player1_arguments,
                "rounds_won": scoring_results["player1_rounds_won"]
            },
            "player2": {
                "name": player2_name,
                "arguments": player2_arguments,
                "rounds_won": scoring_results["player2_rounds_won"]
            }
        },
        "rounds": scoring_results["rounds"],
        "winner": player1_name if scoring_results["overall_winner"] == "Player 1" else player2_name if scoring_results["overall_winner"] == "Player 2" else "Tie",
        "reason": f"Won {scoring_results['player1_rounds_won' if scoring_results['overall_winner'] == 'Player 1' else 'player2_rounds_won']} rounds out of 5",
        "timestamp": str(datetime.datetime.utcnow())
    }

    # Store results
    store_debate_result(debate_data)
    return debate_data


def store_debate_result(debate_data):
    filename = f"debate_{debate_data['game_id']}.json"

    # Create tmp directory if it doesn't exist
    os.makedirs("tmp", exist_ok=True)

    # Save to temporary file
    temp_file = f"tmp/{filename}"
    with open(temp_file, "w") as file:
        json.dump(debate_data, file, indent=4)

    try:
        MINIO_CLIENT.fput_object(BUCKET_NAME, filename, temp_file)
        print(f"[INFO] Debate history saved as {filename} in MinIO.")
    except Exception as e:
        print(f"[ERROR] MinIO storage error: {e}")
        print(f"Results saved locally at: {temp_file}")


if __name__ == "__main__":
    # Example usage
    topic = "Should artificial intelligence be given legal rights?"

    player1_arguments = [
        "AI systems deserve legal protection as they become more sophisticated.",
        "Legal rights would ensure responsible AI development.",
        "AI can make decisions that affect human lives.",
        "Rights come with responsibilities that would benefit society.",
        "Legal framework is needed for AI accountability."
    ]

    player2_arguments = [
        "AI are tools, not conscious beings deserving rights.",
        "Legal rights should be reserved for sentient beings.",
        "AI cannot truly understand moral responsibility.",
        "Giving AI rights could limit human control over technology.",
        "Current legal frameworks are sufficient for AI regulation."
    ]

    results = run_debate(
        topic=topic,
        player1_name="AI Rights Advocate",
        player1_arguments=player1_arguments,
        player2_name="Human Rights First",
        player2_arguments=player2_arguments
    )

    print("\nDebate Results:")
    print(json.dumps(results, indent=2))
