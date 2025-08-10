import os
import sys
import yt_dlp
import libsql
import zlib
from youtubesearchpython import VideosSearch
import pygame
import time
from collections import deque
import threading
import keyboard

# --- TURSO DATABASE CONFIGURATION ---
TURSO_DB_URL = os.environ.get("TURSO_DB_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

# --- MUSIC QUEUE ---
music_queue = deque()
current_song = None
is_paused = False

def fetch_and_play_audio(query):
    """
    Fetches the latest audio from the database, decompresses, and plays it.
    Supports pause, resume, and queue functionality.
    """
    global current_song, is_paused
    print("Attempting to connect to the database to fetch audio...")
    try:
        with libsql.connect("nmusic.db", sync_url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN) as conn:
            print("Database connection successful.")

            # Fetch the most recent audio entry matching the query
            result_set = conn.execute(
                "SELECT title, audio_data FROM youtube_audio WHERE title LIKE ? ORDER BY created_at DESC LIMIT 1",
                (f"%{query}%",)
            )
            row = result_set.fetchone()

            if not row:
                print(f"No audio found in the database for query: {query}")
                return False

            title, compressed_audio = row
            print(f"Retrieved '{title}' from the database.")
            current_song = title

            # Decompress the audio data
            print("Decompressing audio data...")
            decompressed_audio = zlib.decompress(compressed_audio)

            # Save the decompressed audio to a temporary file to play it
            temp_audio_path = f"temp_{title.replace(' ', '_')}.mp3"
            with open(temp_audio_path, 'wb') as audio_file:
                audio_file.write(decompressed_audio)

            # Initialize pygame mixer and play the audio
            pygame.init()
            pygame.mixer.init()
            pygame.mixer.music.load(temp_audio_path)
            print(f"\n▶️ Now playing: {title}")
            pygame.mixer.music.play()

            # Playback loop with pause/resume handling
            while pygame.mixer.music.get_busy() or is_paused:
                if is_paused:
                    time.sleep(0.1)  # Reduce CPU usage while paused
                else:
                    pygame.time.Clock().tick(10)

            print("\nPlayback finished.")
            return True

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        return False

    finally:
        # Clean up the temporary file
        if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
            pygame.mixer.music.stop()
            pygame.quit()
            os.remove(temp_audio_path)
            print(f"Cleaned up temporary file: {temp_audio_path}")

def download_audio_from_youtube(video_url, output_path='.'):
    """
    Downloads audio from a YouTube URL as an MP3 file.
    Returns the file path of the downloaded MP3.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
    }

    try:
        print(f"Starting download for URL: {video_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            sanitized_title = ydl.prepare_filename(info_dict).rsplit('.', 1)[0]
            downloaded_file = f"{sanitized_title}.mp3"
            print(f"\nSuccessfully downloaded audio to: {downloaded_file}")
            return downloaded_file
    except Exception as e:
        print(f"\nAn error occurred during download: {e}")
        return None

def upload_to_database(title, audio_data_bytes):
    """
    Connects to the database and uploads the audio data.
    """
    print("\nAttempting to connect to the database and upload...")
    try:
        with libsql.connect("nmusic.db", sync_url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN) as conn:
            print("Database connection successful.")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_audio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    audio_data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            print(f"Inserting '{title}' into the database...")
            conn.execute(
                "INSERT INTO youtube_audio (title, audio_data) VALUES (?, ?);",
                (title, audio_data_bytes)
            )
            
            conn.commit()
            conn.sync()
            print("Upload complete and synced with Turso!")
            return True

    except Exception as e:
        print(f"\nAn error occurred during the database operation: {e}")
        return False

def get_url_from_name(song_name):
    """
    Searches for a song on YouTube and returns the video URL.
    """
    videosSearch = VideosSearch(song_name, limit=1)
    results = videosSearch.result()
    if results['result']:
        return results['result'][0]['link']
    return None

def add_to_queue(song_name):
    """
    Adds a song to the queue by searching and downloading if not in database.
    """
    global music_queue
    print(f"Adding '{song_name}' to queue...")
    music_queue.append(song_name)
    print(f"Current queue: {[song for song in music_queue]}")

def play_queue():
    """
    Plays all songs in the queue sequentially.
    """
    global music_queue, current_song
    while music_queue:
        song = music_queue.popleft()
        print(f"\nPlaying next in queue: {song}")
        if fetch_and_play_audio(song):
            print(f"Finished playing: {song}")
        else:
            print(f"Skipping {song} due to error or not found.")
    current_song = None

def control_playback():
    """
    Handles playback controls (pause, resume, skip) using keyboard input.
    """
    global is_paused
    print("\nControls: [p] Pause, [r] Resume, [s] Skip, [q] Quit")
    while True:
        if keyboard.is_pressed('p'):
            if not is_paused and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                is_paused = True
                print("⏸️ Playback paused.")
                time.sleep(0.3)  # Debounce
        elif keyboard.is_pressed('r'):
            if is_paused and pygame.mixer.get_init():
                pygame.mixer.music.unpause()
                is_paused = False
                print("▶️ Playback resumed.")
                time.sleep(0.3)  # Debounce
        elif keyboard.is_pressed('s'):
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                print("⏭️ Skipped to next song.")
                time.sleep(0.3)  # Debounce
                break
        elif keyboard.is_pressed('q'):
            print("Exiting playback...")
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
            sys.exit(0)
        time.sleep(0.1)

def main():
    """
    Main function to run the music app with queue and controls.
    """
    if TURSO_AUTH_TOKEN == "YOUR_AUTH_TOKEN_HERE":
        print("ERROR: Please replace 'YOUR_AUTH_TOKEN_HERE' with your actual Turso token.")
        sys.exit(1)

    # Start playback control thread
    control_thread = threading.Thread(target=control_playback, daemon=True)
    control_thread.start()

    while True:
        print("\nMusic App Menu:")
        print("1. Add song to queue")
        print("2. View queue")
        print("3. Play queue")
        print("4. Exit")
        print("5. Song From Database")
        choice = input("Enter choice (1-5): ")

        if choice == '1':
            song_name = input("Enter song name: ")
            youtube_url = get_url_from_name(song_name)
            if youtube_url:
                downloaded_mp3_path = download_audio_from_youtube(youtube_url)
                if downloaded_mp3_path and os.path.exists(downloaded_mp3_path):
                    try:
                        video_title = os.path.basename(downloaded_mp3_path).replace('.mp3', '')
                        print(f"\nReading binary data from '{downloaded_mp3_path}'...")
                        with open(downloaded_mp3_path, 'rb') as audio_file:
                            binary_audio_data = audio_file.read()
                            compressed_audio = zlib.compress(binary_audio_data)
                        if upload_to_database(video_title, compressed_audio):
                            add_to_queue(video_title)
                    except Exception as e:
                        print(f"An error occurred while reading the file: {e}")
                    finally:
                        print(f"Cleaning up local file: {downloaded_mp3_path}")
                        os.remove(downloaded_mp3_path)
                else:
                    print("Download failed, song not added to queue.")
            else:
                print("No video found for the song.")
        elif choice == '2':
            print(f"Current queue: {[song for song in music_queue] if music_queue else 'Empty'}")
        elif choice == '3':
            if music_queue:
                play_queue()
            else:
                print("Queue is empty. Add songs first.")
        elif choice == '4':
            print("Exiting app...")
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
            sys.exit(0)

        elif choice == '5':
            songsearch = input("Enter Song:")
            fetch_and_play_audio(songsearch)
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
