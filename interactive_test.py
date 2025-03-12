import typer
import requests
import json

app = typer.Typer()

BASE_URL = "http://127.0.0.1:8000"

VALID_GENRES = [
    "sports",
    "cinema",
    "philosophy",
    "music",
    "geopolitics",
    "brainrot"
]


def check_player_exists(username: str) -> bool:
    """Check if a player exists in the system"""
    try:
        response = requests.get(f"{BASE_URL}/room-status/player_{username}")
        return response.status_code == 200
    except:
        return False


@app.command()
def register_player():
    """Register a new player"""
    username = typer.prompt("Enter username")

    # Use the players/create endpoint instead
    response = requests.post(f"{BASE_URL}/players/create",
                             json={"player_name": username})

    if response.status_code == 200:
        typer.echo(f"Player {username} registered successfully!")
        return True
    else:
        typer.echo(f"Error registering player: {response.text}")
        return False


@app.command()
def start_debate():
    """Start a new debate with player registration and invitation code"""
    typer.echo("Welcome to Debate Game!")

    # Player 1 Registration/Login
    player1_name = typer.prompt("Enter Player 1 username")
    if not check_player_exists(player1_name):
        if typer.confirm("Player not found. Would you like to register?"):
            if not register_player():
                return
        else:
            typer.echo("Cannot proceed without registration")
            return

    # Genre selection
    typer.echo("\nAvailable genres:")
    for i, genre in enumerate(VALID_GENRES, 1):
        typer.echo(f"{i}. {genre}")

    genre_choice = typer.prompt("Select genre (1-6)")
    try:
        selected_genre = VALID_GENRES[int(genre_choice) - 1]
    except (ValueError, IndexError):
        typer.echo(
            "Invalid genre selection. Please select a number between 1 and 6.")
        return

    # Create room and get invitation code
    response = requests.post(
        f"{BASE_URL}/create-room/{player1_name}", params={"genre": selected_genre})
    if response.status_code != 200:
        typer.echo(f"Error creating room: {response.text}")
        return

    room_data = response.json()
    room_key = room_data["room_key"]
    topic = room_data["topic"]

    typer.echo(f"\nRoom created successfully!")
    typer.echo(f"Topic: {topic}")
    typer.echo(f"\nShare this invitation code with Player 2: {room_key}")
    typer.echo("\nWaiting for Player 2 to join...")

    # Player 2 Registration/Login
    player2_name = typer.prompt("Enter Player 2 username")
    if not check_player_exists(player2_name):
        if typer.confirm("Player not found. Would you like to register?"):
            if not register_player():
                return
        else:
            typer.echo("Cannot proceed without registration")
            return

    # Join room
    join_payload = {"player_name": player2_name}
    response = requests.post(
        f"{BASE_URL}/join-room/{room_key}", json=join_payload)
    if response.status_code != 200:
        typer.echo(f"Error joining room: {response.text}")
        return

    typer.echo("\nBoth players joined! Starting debate...")

    # Submit arguments alternately
    for round_num in range(1, 6):
        # Player 1's turn
        arg = typer.prompt(f"Player 1 ({player1_name}) Argument {round_num}")
        payload = {"argument": arg}
        response = requests.post(
            f"{BASE_URL}/submit-argument/{room_key}/{player1_name}", json=payload)
        if response.status_code != 200:
            typer.echo(f"Error submitting argument: {response.text}")
            return

        # Player 2's turn
        arg = typer.prompt(f"Player 2 ({player2_name}) Argument {round_num}")
        payload = {"argument": arg}
        response = requests.post(
            f"{BASE_URL}/submit-argument/{room_key}/{player2_name}", json=payload)
        if response.status_code != 200:
            typer.echo(f"Error submitting argument: {response.text}")
            return

        result = response.json()
        if result.get("status") == "completed":
            typer.echo("\nDebate Results:")
            typer.echo(json.dumps(result["result"], indent=4))
            return


@app.command()
def join_debate():
    """Join an existing debate using invitation code"""
    room_key = typer.prompt("Enter invitation code")

    # Player Registration/Login
    username = typer.prompt("Enter your username")
    if not check_player_exists(username):
        if typer.confirm("Player not found. Would you like to register?"):
            if not register_player():
                return
        else:
            typer.echo("Cannot proceed without registration")
            return

    # Join room
    join_payload = {"player_name": username}
    response = requests.post(
        f"{BASE_URL}/join-room/{room_key}", json=join_payload)
    if response.status_code != 200:
        typer.echo(f"Error joining room: {response.text}")
        return

    typer.echo("Successfully joined the debate!")
    return response.json()


if __name__ == "__main__":
    app()
