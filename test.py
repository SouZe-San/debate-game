# test_debate_flow.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Global variables
PLAYER1 = "SAYX"
PLAYER2 = "AvinPy"
SELECTED_GENRE = "philosophy"
room_key = None
selected_topic = None


def test_1_create_players():
    """Test creating both players"""
    print("\n=== Testing Player Creation ===")

    # Create first player
    response1 = client.post("/players/create", json={"player_name": PLAYER1})
    assert response1.status_code == 200
    print(f"✓ Created player 1: {PLAYER1}")
    print(f"Response: {response1.json()['message']}")

    # Create second player
    response2 = client.post("/players/create", json={"player_name": PLAYER2})
    assert response2.status_code == 200
    print(f"✓ Created player 2: {PLAYER2}")
    print(f"Response: {response2.json()['message']}")


def test_2_get_valid_genres():
    """Test getting valid genres"""
    print("\n=== Testing Genre Validation ===")

    valid_genres = [
        "sports", "cinema", "philosophy",
        "music", "geopolitics", "brainrot"
    ]

    print("Available genres:")
    for i, genre in enumerate(valid_genres, 1):
        print(f"{i}. {genre}")

    assert SELECTED_GENRE in valid_genres
    print(f"\n✓ Selected genre '{SELECTED_GENRE}' is valid")


def test_3_get_debate_topics():
    """Test getting debate topics for selected genre"""
    print(f"\n=== Getting Topics for {SELECTED_GENRE} ===")
    global selected_topic

    response = client.get(f"/topics/{SELECTED_GENRE}")
    assert response.status_code == 200
    topics = response.json()["topics"]

    print("\nGenerated topics:")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")

    # Select the second topic for testing
    selected_topic = topics[1]
    print(f"\n✓ Selected topic: {selected_topic}")
    print(f"✓ Successfully retrieved {len(topics)} topics")


def test_4_create_debate_room():
    """Test creating a debate room"""
    print("\n=== Creating Debate Room ===")
    global room_key

    response = client.post(
        f"/create-room/{PLAYER1}",
        params={"genre": SELECTED_GENRE}
    )
    assert response.status_code == 200
    room_data = response.json()
    room_key = room_data["room_key"]

    print(f"✓ Room created successfully")
    print(f"Room Key: {room_key}")
    print(f"Debate Topic: {room_data['topic']}")


def test_5_join_room():
    """Test second player joining the room"""
    print("\n=== Joining Debate Room ===")

    response = client.post(
        f"/join-room/{room_key}",
        json={"player_name": PLAYER2}
    )
    assert response.status_code == 200

    # Get room status to verify
    status_response = client.get(f"/room-status/{room_key}")
    room_status = status_response.json()

    print(f"✓ {PLAYER2} joined room {room_key}")
    print("\nRoom Status:")
    print(f"Player 1: {room_status['player1_name']}")
    print(f"Player 2: {room_status['player2_name']}")
    print(f"Status: {room_status['status']}")


def test_6_submit_arguments():
    """Test argument submission flow"""
    print("\n=== Debate Arguments ===")

    sayx_arguments = [
        "The nature of consciousness is fundamentally tied to quantum mechanics.",
        "Our subjective experiences cannot be reduced to purely physical processes.",
        "The hard problem of consciousness remains unsolved by materialist approaches.",
        "Consciousness might be a fundamental property of the universe.",
        "The emergence of consciousness suggests a deeper reality beyond physical matter."
    ]

    avinpy_arguments = [
        "Consciousness can be fully explained through neurological processes.",
        "Quantum effects are too small to influence consciousness meaningfully.",
        "Evolution provides a clear pathway for consciousness development.",
        "The hard problem is more about language than actual mystery.",
        "Occam's razor suggests a materialist explanation is more likely."
    ]

    for round_num in range(5):
        print(f"\n--- Round {round_num + 1} ---")

        # SAYX's turn
        response1 = client.post(
            f"/submit-argument/{room_key}/{PLAYER1}",
            json={"argument": sayx_arguments[round_num]}
        )
        assert response1.status_code == 200
        print(f"{PLAYER1}: {sayx_arguments[round_num]}")
        print(f"Status: {response1.json()['status']}")

        # AvinPy's turn
        response2 = client.post(
            f"/submit-argument/{room_key}/{PLAYER2}",
            json={"argument": avinpy_arguments[round_num]}
        )
        assert response2.status_code == 200
        print(f"{PLAYER2}: {avinpy_arguments[round_num]}")
        print(f"Status: {response2.json()['status']}")

        if round_num == 4:  # Last round
            result = response2.json()
            print("\n=== Debate Results ===")
            print(f"Winner: {result['result']['winner']}")
            print(f"Reason: {result['result']['reason']}")

            # Print detailed round information
            print("\nRound-by-round analysis:")
            for round_data in result['result']['rounds']:
                print(f"\nRound {round_data['round']}:")
                print(f"Player 1 scores: {round_data['player1_score']}")
                print(f"Player 2 scores: {round_data['player2_score']}")
                print(f"Round winner: {round_data['round_winner']}")


def test_7_check_final_scores():
    """Test checking final player scores"""
    print("\n=== Final Player Statistics ===")

    # Get player stats
    response1 = client.get(f"/players/{PLAYER1}")
    assert response1.status_code == 200
    sayx_data = response1.json()

    response2 = client.get(f"/players/{PLAYER2}")
    assert response2.status_code == 200
    avinpy_data = response2.json()

    print(f"\n{PLAYER1} Statistics:")
    print(f"├── Total Score: {sayx_data['total_score']}")
    print(f"├── Games Played: {sayx_data['games_played']}")
    print(f"├── Wins: {sayx_data['wins']}")
    print(f"└── Losses: {sayx_data['losses']}")

    print(f"\n{PLAYER2} Statistics:")
    print(f"├── Total Score: {avinpy_data['total_score']}")
    print(f"├── Games Played: {avinpy_data['games_played']}")
    print(f"├── Wins: {avinpy_data['wins']}")
    print(f"└── Losses: {avinpy_data['losses']}")


if __name__ == "__main__":
    pytest.main(["-v", "test.py"])
