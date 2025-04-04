The Debate Game backend is a FastAPI application that allows users to create players, generate debate topics, create/join debate rooms, submit arguments, and automatically score debates using an AI engine and MinIO-based history storage.


# Table of Contents

* [Prerequisites](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#prerequisites)
* [Installation](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#installation)
* [Configuration](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#configuration)
  * [.env Configuration](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#env-configuration)
  * [MinIO Setup](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#minio-setup)
* [Running the Server](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#running-the-server)
* [API Endpoints Overview](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#api-endpoints-overview)
* [Testing the Backend](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#testing-the-backend)
* [Additional Modules](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#additional-modules)
* [Troubleshooting](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#troubleshooting)
* [License](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#license)

---

# Prerequisites

Before getting started, ensure you have the following installed on your system:

* **Python 3.8+**
* **pip** (Python package installer)
* **MinIO server:** Used for storing debate history. You can download and run MinIO from the [MinIO official website](https://min.io/).
* **Environment variables:** You might need to set environment variables (see [.env Configuration](https://app.greptile.com/chat/8ab54913-7cfd-40c4-8f4b-2b061f75b787#env-configuration)).

---

# Installation

## 1. Clone the Repository

```
git clone https://github.com/sayan-does/debate-game.git
cd debate-game
```

## 2. Create a Virtual Environment (Recommended)

### On macOS/Linux:

```
python3 -m venv venv
source venv/bin/activate
```

### On Windows:

```
python -m venv venv
venv\Scripts\activate
```

## 3. Install Dependencies

Ensure you have the latest `<span>pip</span>` version and install dependencies from `<span>requirements.txt</span>`:

```
pip install --upgrade pip
pip install -r requirements.txt
```


# Configuration

# .env Configuration

The application relies on several environment variables to configure the AI engine and MinIO access. Create a `.env` file in the root directory of the repository and set the following (adjust values as needed):

<pre><span class="linenumber react-syntax-highlighter-line-number">1</span><span># MinIO Configuration
</span><span class="linenumber react-syntax-highlighter-line-number">2</span>MINIO_ENDPOINT=localhost:9000
<span class="linenumber react-syntax-highlighter-line-number">3</span>MINIO_ACCESS_KEY=sayan
<span class="linenumber react-syntax-highlighter-line-number">4</span>MINIO_SECRET_KEY=admin123
<span class="linenumber react-syntax-highlighter-line-number">5</span>
<span class="linenumber react-syntax-highlighter-line-number">6</span># Gemini API Key for the AI engine
<span class="linenumber react-syntax-highlighter-line-number">7</span>GEMINI_API_KEY=your_gemini_api_key_here</code></div></div></pre>

> **Important:** The `GEMINI_API_KEY` is required for generating debate topics and scoring arguments using the Gemini API. If the key is not provided, the application will fall back to default topics and scores.

# MinIO Setup

1. **Download and Run MinIO:**
   Follow the instructions on the [MinIO website](https://min.io/docs/minio/container/index.html) if you do not already have it installed.
2. **Start the Server:**
   For local development, you can start MinIO with a command such as:``docker run-p9000:9000-p 9001:9001 --nameminio1-v D:\minio\data:/data-e"MINIO_ROOT_USER=ROOTUSER"-e"MINIO_ROOT_PASSWORD=CHANGEME123"quay.io/minio/minioserver/data--console-address":9001"``
3. **Bucket Configuration:**
   The backend is configured to use a bucket called `debate-history`. Upon startup, the application (or the helper script in `minio-bucket.py`) will verify the existence of the bucket and create it if necessary.


---

# Running the Server

Once the dependencies are installed and your environment is configured:

1. **Run the Application Using Uvicorn**

   * The `--reload` flag is useful during development as it will auto-reload the server on code changes.
   * The server will start on [http://127.0.0.1:8000](http://127.0.0.1:8000/) by default.
2. **Access Interactive API Documentation**
   Open your browser and navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to view and test the API endpoints using the automatically generated Swagger UI.

---

# API Endpoints Overview

Below is a brief overview of some of the available endpoints. For further details, check the endpoint documentation available via Swagger UI.

1. **Player Endpoints**
   * **Create a Player:** `POST /players/create`
   * **Get Player Details:** `GET /players/{username}`
   * **Player History and Rankings:** `GET /player/history/{username}`
2. **Genre and Topic Endpoints**
   * **Get Available Genres:** `GET /genres`
   * **Get Debate Topics by Genre:** `GET /topics/{genre}`
3. **Debate Room Endpoints**
   * **Create a Room:** `POST /create-room/{player_name}`
     *Requires query parameter:* `topic`
   * **Join a Room:** `POST /join-room/{room_key}`
   * **Submit an Argument:** `POST /submit-argument/{room_key}/{player_name}`
   * **Abort a Debate:** `POST /abort-debate/{room_key}/{player_name}`
   * **Check Room Status:** `GET /room-status/{room_key}`
