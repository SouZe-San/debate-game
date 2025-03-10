import typer
import requests
import json

app = typer.Typer()

BASE_URL = "http://127.0.0.1:8000"  # Change if hosted elsewhere


@app.command()
def start_debate():
    """
    Start a new debate by providing topic, player names, and five arguments each.
    """
    typer.echo("Enter debate details:")

    topic = typer.prompt("Debate Topic")

    # Player 1 Details
    player1_name = typer.prompt("Player 1 Name")
    player1_arg1 = typer.prompt("Player 1 Argument 1")
    player1_arg2 = typer.prompt("Player 1 Argument 2")
    player1_arg3 = typer.prompt("Player 1 Argument 3")
    player1_arg4 = typer.prompt("Player 1 Argument 4")
    player1_arg5 = typer.prompt("Player 1 Argument 5")

    # Player 2 Details
    player2_name = typer.prompt("Player 2 Name")
    player2_arg1 = typer.prompt("Player 2 Argument 1")
    player2_arg2 = typer.prompt("Player 2 Argument 2")
    player2_arg3 = typer.prompt("Player 2 Argument 3")
    player2_arg4 = typer.prompt("Player 2 Argument 4")
    player2_arg5 = typer.prompt("Player 2 Argument 5")

    game_id = typer.prompt("Game ID", type=int)

    payload = {
        "topic": topic,
        "player1_name": player1_name,
        "player1_arguments": [player1_arg1, player1_arg2, player1_arg3, player1_arg4, player1_arg5],
        "player2_name": player2_name,
        "player2_arguments": [player2_arg1, player2_arg2, player2_arg3, player2_arg4, player2_arg5],
        "game_id": game_id
    }

    response = requests.post(f"{BASE_URL}/debate/", json=payload)

    if response.status_code == 200:
        typer.echo("\nDebate Results:")
        typer.echo(json.dumps(response.json(), indent=4))
    else:
        typer.echo(f"\nError: {response.status_code} - {response.text}")



@app.command()
def get_debate():
    """
    Retrieve a debate result using its ID.
    """
    debate_id = typer.prompt("Enter Debate ID", type=int)

    response = requests.get(f"{BASE_URL}/debate/{debate_id}")

    if response.status_code == 200:
        typer.echo("\nDebate Result:")
        typer.echo(json.dumps(response.json(), indent=4))
    else:
        typer.echo(f"\nError: {response.status_code} - {response.text}")


if __name__ == "__main__":
    app()
