# test_debate_flow.py
import pytest
from fastapi.testclient import TestClient
from main import app
import time

client = TestClient(app)

# Global variables
PLAYER1 = "SAYX"
PLAYER2 = "AvinPy"
SELECTED_GENRE = "philosophy"
room_key = None
selected_topic = None


def test_2_get_valid_genres():
    """Test getting valid genres"""
    valid_genres = [
        "sports",
        "cinema",
        "philosophy",
        "music",
        "geopolitics",
        "brainrot"
    ]
    print(f"\nAvailable genres: {', '.join(valid_genres)}")
    assert SELECTED_GENRE in valid_genres
    print(f"✓ Selected genre: {SELECTED_GENRE}")


def test_3_get_debate_topics():
    """Test getting debate topics for selected genre"""
    global selected_topic

    response = client.get(f"/topics/{SELECTED_GENRE}")
    assert response.status_code == 200
    topics = response.json()["topics"]

    print(f"\nGenerated topics for {SELECTED_GENRE}:")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")

    # Select the first topic for this test
    selected_topic = topics[1]
    print(f"\n✓ Selected topic: {selected_topic}")


def test_4_create_debate_room():
    """Test creating a debate room with selected topic"""
    global room_key

    response = client.post(
        f"/create-room/{PLAYER1}",
        params={"genre": SELECTED_GENRE}
    )
    assert response.status_code == 200
    room_data = response.json()
    room_key = room_data["room_key"]

    print(f"\n✓ Room created by {PLAYER1}")
    print(f"✓ Room code: {room_key}")


def test_5_join_room():
    """Test second player joining the room"""
    response = client.post(
        f"/join-room/{room_key}",
        json={"player_name": PLAYER2}
    )
    assert response.status_code == 200
    print(f"\n✓ {PLAYER2} joined room {room_key}")


def test_6_submit_arguments():
    """Test argument submission flow"""
    # Sample arguments for both players
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

    print("\nDebate Arguments:")
    for round_num in range(5):
        # SAYX's turn
        response1 = client.post(
            f"/submit-argument/{room_key}/{PLAYER1}",
            json={"argument": sayx_arguments[round_num]}
        )
        assert response1.status_code == 200
        print(f"\nRound {round_num + 1}:")
        print(f"{PLAYER1}: {sayx_arguments[round_num]}")

        # AvinPy's turn
        response2 = client.post(
            f"/submit-argument/{room_key}/{PLAYER2}",
            json={"argument": avinpy_arguments[round_num]}
        )
        assert response2.status_code == 200
        print(f"{PLAYER2}: {avinpy_arguments[round_num]}")

        if round_num == 4:  # Last round
            result = response2.json()
            print("\nDebate Results:")
            print(f"Winner: {result['result']['winner']}")
            print(f"Reason: {result['result']['reason']}")


def test_7_check_final_scores():
    """Test checking final player scores"""
    # Check SAYX's final score
    response1 = client.get(f"/players/{PLAYER1}")
    assert response1.status_code == 200
    sayx_data = response1.json()

    # Check AvinPy's final score
    response2 = client.get(f"/players/{PLAYER2}")
    assert response2.status_code == 200
    avinpy_data = response2.json()

    print("\nFinal Player Stats:")
    print(f"\n{PLAYER1}:")
    print(f"Total Score: {sayx_data['total_score']}")
    print(f"Games Played: {sayx_data['games_played']}")
    print(f"Wins: {sayx_data['wins']}")
    print(f"Losses: {sayx_data['losses']}")

    print(f"\n{PLAYER2}:")
    print(f"Total Score: {avinpy_data['total_score']}")
    print(f"Games Played: {avinpy_data['games_played']}")
    print(f"Wins: {avinpy_data['wins']}")
    print(f"Losses: {avinpy_data['losses']}")


if __name__ == "__main__":
    pytest.main(["-v", "test.py"])
