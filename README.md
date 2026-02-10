# Spotify AI Music Discovery

A desktop app that learns your music taste in real time. Rate songs with thumbs up/down and the AI adapts to recommend tracks you'll like.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)

## Setup

### 1. Clone the repo

```
git clone https://github.com/Morticuss/Spotify-AI.git
cd Spotify-AI
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Create a Spotify Developer App

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Log in and click **Create App**
3. Fill in any name and description
4. Set the **Redirect URI** to `http://127.0.0.1:8080/callback`
5. Click **Save**
6. On your app's page, click **Settings** and copy the **Client ID** and **Client Secret**

### 4. Configure .env

Edit the `.env` file in the project folder:

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

### 5. Run

```
python main.py
```

A browser window will open for Spotify login on first run. Make sure Spotify is open on a device (phone, desktop, or web player) so it can control playback.

## Controls

| Key | Action |
|-----|--------|
| Up Arrow | Like |
| Down Arrow | Dislike |
| Right Arrow | Skip |
| Left Arrow | Back |

## Features

- AI learns from your likes/dislikes using Thompson sampling
- Genre leaderboard shows what the AI thinks you like
- **Update Playlist** button creates a Spotify playlist with the AI's top 25 picks
- Back button to revisit previous tracks and change ratings
- All progress saves between sessions
