# --- CHANGE 1: Remove the pydub import ---
from flask import Flask, request, render_template, jsonify, Response
import yt_dlp
import zlib
import os
# from pydub import AudioSegment <-- REMOVED
import io
from libsql import connect
import base64
from functools import wraps

app = Flask(__name__,template_folder="templates")

# Hardcoded credentials for authentication
USERNAME = "admin"
PASSWORD = "nikhil123"

# Database configuration
TURSO_DB_URL = "libsql://nmusic-nickocracker.aws-ap-south-1.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3NjIzNTcwODUsImlhdCI6MTc1NDU4MTA4NSwiaWQiOiIyYzdmYzNmNi1hMGIwLTQxYWQtOTg0OS04M2Y3ODdkNmJjNzgiLCJyaWQiOiI4ZDRjY2FjMi1hZmM2LTQzYjItOWUwMS05NmY1YTNmMjE4MTUifQ.ywoSztW44QEIUYsmWyL60gCmRDuftLDiRKu5wTymG-t5pQxFd_8VrVEytVxwz2kbnkj_klSEOQBpbPY090BNBg"

# Authentication decorator
def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Please provide valid credentials.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Initialize Turso database with local sync
def init_db():
    conn = connect("nmusic.db", sync_url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS youtube_audio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            audio_data BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

# Download single audio from YouTube using yt-dlp
def download_single_audio(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        return 'temp_audio.mp3', info['title']

# Download playlist from YouTube using yt-dlp
def download_playlist(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio_%(playlist_index)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'yes_playlist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        return [(f"temp_audio_{i+1}.mp3", video['title']) for i, video in enumerate(info['entries'])]

# --- CHANGE 2: Replace the pydub function with a simpler one ---
# This new function reads the file's binary content directly and compresses it.
def read_and_compress_audio(file_path):
    with open(file_path, 'rb') as f:
        audio_data = f.read()
    compressed_data = zlib.compress(audio_data)
    return compressed_data

# Insert song into Turso database if it doesn't already exist
def insert_song(conn, title, compressed_data):
    result = conn.execute(
        "SELECT id FROM youtube_audio WHERE title = ?",
        (title,)
    )
    if result.fetchone():
        return False, f"Song '{title}' already exists in the database."
    
    conn.execute(
        "INSERT INTO youtube_audio (title, audio_data) VALUES (?, ?);",
        (title, compressed_data)
    )
    conn.commit()
    return True, f"Inserted song '{title}' into database."

# Fetch the most recent song matching a query
def fetch_recent_song(conn, query):
    result_set = conn.execute(
        "SELECT title, audio_data FROM youtube_audio WHERE title LIKE ? ORDER BY created_at DESC LIMIT 1",
        (f"%{query}%",)
    )
    row = result_set.fetchone()
    if row:
        title, audio_data = row
        # Decompress the data before sending it
        decompressed_data = zlib.decompress(audio_data)
        return title, decompressed_data
    return None, None

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/process_audio', methods=['POST'])
@requires_auth
def process_audio():
    youtube_url = request.form['youtube_url']
    download_type = request.form['download_type']
    
    conn = init_db()
    files_to_delete = []
    try:
        if download_type == 'single':
            file_path, title = download_single_audio(youtube_url)
            # --- CHANGE 3: Call the new function ---
            compressed_data = read_and_compress_audio(file_path)
            success, message = insert_song(conn, title, compressed_data)
            files_to_delete = [file_path]
            if not success:
                return jsonify({
                    'status': 'skipped', 'message': message,
                    'fetched_title': None, 'audio_data': None
                })
            fetched_title, audio_data = fetch_recent_song(conn, title)
        else:
            audio_files = download_playlist(youtube_url)
            titles = []
            for file_path, title in audio_files:
                # --- CHANGE 4: Call the new function in the loop ---
                compressed_data = read_and_compress_audio(file_path)
                success, msg = insert_song(conn, title, compressed_data)
                files_to_delete.append(file_path)
                if success:
                    titles.append(title)
            message = f"Inserted {len(titles)} new songs from playlist: {', '.join(titles)}" if titles else "No new songs inserted; all songs already exist."
            fetched_title, audio_data = fetch_recent_song(conn, titles[0] if titles else "")

        response = {
            'status': 'success',
            'message': message,
            'fetched_title': fetched_title,
            'audio_data': base64.b64encode(audio_data).decode('utf-8') if audio_data else None
        }
    except Exception as e:
        response = { 'status': 'error', 'message': f"An error occurred: {str(e)}" }
    finally:
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
        conn.close()
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)