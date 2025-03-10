import os
import json
import requests
import datetime
from dotenv import load_dotenv
from minio import Minio
import re
import random

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


def generate_debate_topic():
    """
    Generates a random debate topic using OpenRouter API.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://debate-app.example.com"
    }

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": """
Generate an interesting and controversial debate topic that would lead to good arguments on both sides.
The topic should be concise and framed as a clear proposition or question.

Your response must be a valid JSON object with exactly this field:
{
  "topic": "Should artificial intelligence be given legal personhood?"
}
"""
            }
        ],
        "temperature": 0.9,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        try:
            response_data = response.json()
            message_content = response_data.get("choices", [{}])[
                0].get("message", {}).get("content", "")

            if message_content:
                try:
                    topic_data = json.loads(message_content)
                    if "topic" in topic_data:
                        return topic_data["topic"]
                except json.JSONDecodeError:
                    print(f"Failed to parse topic JSON: {message_content}")

            # Fallback topics if API fails
            fallback_topics = [
                "Should social media be regulated by government?",
                "Is universal basic income a viable economic policy?",
                "Should voting be mandatory?",
                "Is space exploration worth the cost?",
                "Should college education be free?",
                "Is genetic engineering ethical?",
                "Should artificial intelligence be regulated?",
                "Is nuclear energy the solution to climate change?",
                "Should the death penalty be abolished?",
                "Is democracy the best form of government?"
            ]
            return random.choice(fallback_topics)
        except Exception as e:
            print(f"Error parsing topic response: {str(e)}")
            return "Should AI replace human jobs?"
    else:
        print(f"API Error ({response.status_code}):", response.text)
        return "Should AI replace human jobs?"


def score_argument_turn(argument, topic, turn_number):
    """
    Uses OpenRouter API to score a single turn of argument based on Logic, Relevance, and Persuasiveness.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://debate-app.example.com"
    }

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": f"""
You are a debate judge. Score the following argument (Turn {turn_number}/5) based on three criteria (0-10):
- Logic: How well-reasoned is the argument?
- Relevance: How related is the argument to the topic?
- Persuasiveness: How convincing is the argument?
- Deduct points for fallacies, irrelevant points, or lack of evidence. Humor can be entertained.

Debate Topic: {topic}
Argument (Turn {turn_number}): "{argument}"

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
        "response_format": {"type": "json_object"}
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        print_full_response(response, f"Score Response - Turn {turn_number}")
        try:
            response_data = response.json()
            message_content = response_data.get("choices", [{}])[
                0].get("message", {}).get("content", "")

            if message_content:
                try:
                    scores = json.loads(message_content)
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


def score_player_arguments(player_arguments, topic):
    """
    Scores all 5 turns of a player's arguments and calculates totals
    """
    turn_scores = []
    overall_scores = {"logic": 0, "relevance": 0, "persuasiveness": 0}

    for turn_num, argument in enumerate(player_arguments, 1):
        print(f"Scoring Turn {turn_num}...")
        score = score_argument_turn(argument, topic, turn_num)
        turn_scores.append(score)

        # Add to overall scores
        overall_scores["logic"] += score["logic"]
        overall_scores["relevance"] += score["relevance"]
        overall_scores["persuasiveness"] += score["persuasiveness"]

    # Calculate averages for the overall scores
    for key in overall_scores:
        overall_scores[key] = overall_scores[key] / len(player_arguments)

    overall_scores["total"] = sum(overall_scores.values())

    return {
        "turn_scores": turn_scores,
        "overall_score": overall_scores
    }


def sanitize_filename(filename):
    """Removes invalid characters from the filename"""
    return re.sub(r'[\/:*?"<>|]', '_', filename)


def generate_judgment(player1, player2, topic):
    """
    Uses OpenRouter API to generate a judgment explaining why one player won based on all 5 turns.
    """
    # Determine winner based on overall scores
    player1_total = player1["score"]["overall_score"]["total"]
    player2_total = player2["score"]["overall_score"]["total"]

    if player1_total > player2_total:
        default_winner = player1["nickname"]
        default_reason = f"{player1['nickname']} had a higher overall score ({player1_total:.1f} vs {player2_total:.1f})."
    elif player2_total > player1_total:
        default_winner = player2["nickname"]
        default_reason = f"{player2['nickname']} had a higher overall score ({player2_total:.1f} vs {player1_total:.1f})."
    else:
        default_winner = "Tie"
        default_reason = f"Both players had equal scores of {player1_total:.1f}."

    # Create a summary of all turn scores for the judgment
    p1_turn_summaries = []
    p2_turn_summaries = []

    for i in range(5):
        p1_turn = player1["score"]["turn_scores"][i]
        p2_turn = player2["score"]["turn_scores"][i]

        p1_turn_summaries.append(
            f"Turn {i+1}: Logic: {p1_turn['logic']}, Relevance: {p1_turn['relevance']}, Persuasiveness: {p1_turn['persuasiveness']}")
        p2_turn_summaries.append(
            f"Turn {i+1}: Logic: {p2_turn['logic']}, Relevance: {p2_turn['relevance']}, Persuasiveness: {p2_turn['persuasiveness']}")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://debate-app.example.com"
    }

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": f"""
You are an expert debate judge. The debate topic was: "{topic}".

Player 1: {player1['nickname']}
Scores across 5 turns:
{chr(10).join(p1_turn_summaries)}
Overall scores:
- Logic: {player1['score']['overall_score']['logic']:.1f}
- Relevance: {player1['score']['overall_score']['relevance']:.1f}
- Persuasiveness: {player1['score']['overall_score']['persuasiveness']:.1f}
- Total Score: {player1['score']['overall_score']['total']:.1f}

Player 2: {player2['nickname']}
Scores across 5 turns:
{chr(10).join(p2_turn_summaries)}
Overall scores:
- Logic: {player2['score']['overall_score']['logic']:.1f}
- Relevance: {player2['score']['overall_score']['relevance']:.1f}
- Persuasiveness: {player2['score']['overall_score']['persuasiveness']:.1f}
- Total Score: {player2['score']['overall_score']['total']:.1f}

Based on all 5 turns and overall scores, declare the winner and provide a detailed explanation of why they won, 
highlighting key moments and strengths across the debate. Consider the entire debate trajectory, improvements 
or declines in quality, and how well each player responded to the other's arguments.

Your response must be a valid JSON object with exactly these two fields:
{{
  "winner": "{default_winner}",
  "reason": "Comprehensive explanation for why this player won across all 5 turns"
}}
"""
            }
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        print_full_response(response, "Judgment Response")
        try:
            response_data = response.json()
            message_content = response_data.get("choices", [{}])[
                0].get("message", {}).get("content", "")

            if message_content:
                try:
                    judgment = json.loads(message_content)
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

    # Format for your MinIO setup - now with all 5 turns
    arguments = []

    # Zip together the turns from both players to create the arguments array
    for i in range(5):
        arguments.append({
            "player": debate_data["player1"]["nickname"],
            "argument": debate_data["player1"]["arguments"][i],
            "turn": i+1
        })
        arguments.append({
            "player": debate_data["player2"]["nickname"],
            "argument": debate_data["player2"]["arguments"][i],
            "turn": i+1
        })

    # Create the JSON data structure that matches your format
    formatted_data = {
        "game_id": game_id,
        "player_1": debate_data["player1"]["nickname"],
        "player_2": debate_data["player2"]["nickname"],
        "topic": debate_data["topic"],
        "arguments": arguments,
        "winner": debate_data["winner"],
        "scores": {
            debate_data["player1"]["nickname"]: debate_data["player1"]["score"]["overall_score"],
            debate_data["player2"]["nickname"]: debate_data["player2"]["score"]["overall_score"]
        },
        "turn_scores": {
            debate_data["player1"]["nickname"]: debate_data["player1"]["score"]["turn_scores"],
            debate_data["player2"]["nickname"]: debate_data["player2"]["score"]["turn_scores"]
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


def run_debate(topic=None, player1_name="Player1", player1_arguments=None, player2_name="Player2", player2_arguments=None, game_id=None):
    """
    Runs a debate with 5 turns, scores arguments, determines the winner, and stores results.
    
    Arguments should be a list of 5 strings for each player.
    If no topic is provided, one will be generated.
    """
    # Generate a debate topic if none provided
    if topic is None:
        topic = generate_debate_topic()

    print(f"Starting debate on topic: {topic}")

    # Ensure bucket exists
    create_bucket()

    # Set default arguments if none provided (for testing)
    if player1_arguments is None:
        player1_arguments = [
            "I believe this is true because of reason A.",
            "Furthermore, evidence B supports my position.",
            "My opponent's claim about C is flawed because of D.",
            "Historical examples like E demonstrate my point.",
            "In conclusion, F proves that my stance is correct."
        ]

    if player2_arguments is None:
        player2_arguments = [
            "I disagree because of reason X.",
            "Studies show that Y contradicts my opponent's position.",
            "The logical fallacy in their argument is Z.",
            "Real-world applications show that my approach works better.",
            "Therefore, the evidence clearly supports my position."
        ]

    # Ensure we have exactly 5 arguments per player
    if len(player1_arguments) != 5 or len(player2_arguments) != 5:
        raise ValueError("Both players must have exactly 5 arguments")

    player1 = {
        "nickname": player1_name,
        "arguments": player1_arguments
    }

    player2 = {
        "nickname": player2_name,
        "arguments": player2_arguments
    }

    print(f"Scoring {player1_name}'s arguments...")
    player1["score"] = score_player_arguments(player1["arguments"], topic)

    print(f"Scoring {player2_name}'s arguments...")
    player2["score"] = score_player_arguments(player2["arguments"], topic)

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
    # Example Debate with 5 turns
    topic = None  # Will generate a random topic

    player1_name = "DebateMasterX"
    player1_arguments = [
        "AI systems can analyze legal precedents and case details with perfect recall and consistency, eliminating human biases that often affect judgments. They can process vast amounts of data quickly, ensuring that all relevant information is considered.",
        "Studies show that human judges are influenced by factors like hunger, fatigue, and personal experiences, leading to inconsistent rulings. AI systems would eliminate these inconsistencies, ensuring equal treatment under the law.",
        "The cost of our current judicial system is enormous. AI judges would reduce court backlogs and provide faster resolutions, making justice more accessible to everyone regardless of economic status.",
        "My opponent claims AI lacks empathy, but this is precisely why they'd be more fair. Human empathy often leads to preferential treatment based on appearance, background, or emotional appeal rather than facts and law.",
        "We already trust algorithms with life-or-death decisions in medicine, transportation, and other fields. The judicial system should embrace this technology to become more efficient, consistent, and truly blind in its application of justice."
    ]

    player2_name = "LogicWarrior"
    player2_arguments = [
        "Justice requires understanding human context and nuance that AI cannot grasp. Judges must weigh complex ethical considerations, show compassion, and understand unspoken cultural contexts that algorithms simply cannot comprehend.",
        "While AI may appear unbiased, it inherits biases from its training data. Historical court decisions contain systemic prejudices that would be amplified, not eliminated, by AI judges learning from this tainted data.",
        "The law evolves through judicial interpretation and precedent-setting decisions that require moral courage and human judgment. Would we have civil rights advances if machines were simply applying existing laws without questioning their fundamental fairness?",
        "The appearance of judicial neutrality is essential for public trust. Citizens would never accept life-altering decisions from black-box algorithms they cannot question or appeal to on human terms.",
        "The purpose of punishment isn't just enforcement but rehabilitation, which requires understanding human potential for change. AI cannot assess remorse, personal growth, or the complex social factors that should inform sentencing decisions."
    ]

    # Run debate with random topic generation
    results = run_debate(topic, player1_name,
                         player1_arguments, player2_name, player2_arguments)

    print("\nFinal Debate Results:")
    print(json.dumps(results, indent=4))
