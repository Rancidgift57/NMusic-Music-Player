import os
import sys
import zlib
import libsql
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import tempfile
from contextlib import asynccontextmanager
from uuid import uuid4
from urllib.parse import quote
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware

# --- TURSO DATABASE CONFIGURATION ---
TURSO_DB_URL = os.environ.get("TURSO_DB_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

# List to track temporary files for cleanup
temp_files = []

# In-memory queue storage (session_id -> list of song titles)
# FIX: Your API uses a simple in-memory dictionary for queues.
# This means the queue will be lost every time the server restarts on Render.
# For a real app, you would want to store this queue data in your Turso database.
queues: Dict[str, List[Dict[str, str]]] = {} # Storing dicts with id and name now

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: No specific startup tasks needed
    yield
    # Shutdown: Clean up temporary files
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Cleaned up temporary file: {temp_file}")
        except Exception as e:
            print(f"Error cleaning up {temp_file}: {e}")
    temp_files.clear()

app = FastAPI(title="Audio Database API", lifespan=lifespan)

# --- CORS MIDDLEWARE SETUP ---
# This is the key change to fix the "Failed to fetch" error.
# It tells the browser that requests from any origin are allowed.
origins = ["*"] # Allow all origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"], # Allow all headers
)

# Pydantic models for request validation
class Song(BaseModel):
    id: str
    name: str

class AddSongRequest(BaseModel):
    name: str

class QueueResponse(BaseModel):
    queue: List[Song]

class ReorderQueueRequest(BaseModel):
    order: List[str] # List of song IDs representing the new order

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Audio Database API",
        "endpoints": {
            "/play/{song_name}": "GET - Stream audio from database",
            "/queue/add": "POST - Add a song to the queue",
            "/queue": "GET - Get the current queue",
            "/queue/{song_id}": "DELETE - Remove a song from the queue",
            "/queue/clear": "POST - Clear the queue",
            "/queue/reorder": "POST - Reorder songs in the queue"
        }
    }

@app.get("/play/{song_name}")
async def play_audio(song_name: str):
    try:
        with libsql.connect("nmusic.db", sync_url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN) as conn:
            result_set = conn.execute(
                "SELECT title, audio_data FROM youtube_audio WHERE title LIKE ? ORDER BY created_at DESC LIMIT 1",
                (f"%{song_name}%",)
            )
            row = result_set.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="No audio found in the database")

            title, compressed_audio = row
            decompressed_audio = zlib.decompress(compressed_audio)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_file.write(decompressed_audio)
                temp_file_path = temp_file.name
                temp_files.append(temp_file_path)

            return FileResponse(
                temp_file_path,
                media_type="audio/mpeg",
                filename=f"{title}.mp3",
                headers={"X-Song-Title": quote(title)}
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playback error: {str(e)}")

# --- REVISED QUEUE LOGIC ---
# Using a single, global queue for simplicity. For multiple users, you'd use session IDs.
GLOBAL_QUEUE_ID = "global_queue"

@app.post("/queue/add", response_model=Song)
async def add_to_queue(request: AddSongRequest):
    try:
        with libsql.connect("nmusic.db", sync_url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN) as conn:
            result = conn.execute(
                "SELECT title FROM youtube_audio WHERE title LIKE ? LIMIT 1",
                (f"%{request.name}%",)
            ).fetchone()
            if not result:
                raise HTTPException(status_code=404, detail=f"Song '{request.name}' not found in database")
            song_title = result[0]

        if GLOBAL_QUEUE_ID not in queues:
            queues[GLOBAL_QUEUE_ID] = []

        new_song = {"id": str(uuid4()), "name": song_title}
        queues[GLOBAL_QUEUE_ID].append(new_song)
        return new_song
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue add error: {str(e)}")

@app.get("/queue", response_model=QueueResponse)
async def get_queue():
    queue_items = queues.get(GLOBAL_QUEUE_ID, [])
    return QueueResponse(queue=queue_items)

@app.delete("/queue/{song_id}")
async def remove_from_queue(song_id: str):
    try:
        queue = queues.get(GLOBAL_QUEUE_ID)
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")

        song_to_remove = next((song for song in queue if song["id"] == song_id), None)
        if not song_to_remove:
            raise HTTPException(status_code=404, detail="Song not found in queue")

        queues[GLOBAL_QUEUE_ID] = [s for s in queue if s["id"] != song_id]
        return {"message": f"Removed '{song_to_remove['name']}' from queue"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue remove error: {str(e)}")

@app.post("/queue/clear")
async def clear_queue():
    if GLOBAL_QUEUE_ID in queues:
        queues[GLOBAL_QUEUE_ID].clear()
    return {"message": "Queue cleared"}

@app.post("/queue/reorder")
async def reorder_queue(request: ReorderQueueRequest):
    try:
        new_order_ids = request.order
        queue = queues.get(GLOBAL_QUEUE_ID)

        if not queue:
            raise HTTPException(status_code=404, detail="Queue is empty")

        # Create a map of the current songs by ID for quick lookup
        song_map = {song['id']: song for song in queue}
        
        # Check if all new IDs are valid
        if any(song_id not in song_map for song_id in new_order_ids):
             raise HTTPException(status_code=400, detail="Invalid song ID in reorder list.")

        new_queue = [song_map[song_id] for song_id in new_order_ids]
        queues[GLOBAL_QUEUE_ID] = new_queue

        return {"message": "Queue reordered successfully", "queue": new_queue}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue reorder error: {str(e)}")


if __name__ == "__main__":
    if not TURSO_AUTH_TOKEN or TURSO_AUTH_TOKEN == "YOUR_AUTH_TOKEN_HERE":
        print("ERROR: Please set the TURSO_AUTH_TOKEN environment variable.")
        sys.exit(1)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
