import os
import sys
import yt_dlp
import libsql
import zlib
from youtubesearchpython import VideosSearch
import pygame

# --- TURSO DATABASE CONFIGURATION ---
TURSO_DB_URL = os.environ.get("TURSO_DB_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")


def fetch_and_play_audio(query):
    """
    Fetches the latest audio from the database, decompresses, and plays it.
    """
    print("Attempting to connect to the database to fetch audio...")
    try:
        with libsql.connect("nmusic.db", sync_url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN) as conn:
            print("Database connection successful.")

            # Fetch the most recent audio entry
            result_set = conn.execute(
                "SELECT title, audio_data FROM youtube_audio WHERE title LIKE ? ORDER BY created_at DESC LIMIT 1", 
                (f"%{query}%",)
            )
            row = result_set.fetchone()

            if not row:
                print("No audio found in the database.")
                return

            title, compressed_audio = row
            print(f"Retrieved '{title}' from the database.")

            # Decompress the audio data
            print("Decompressing audio data...")
            decompressed_audio = zlib.decompress(compressed_audio)

            # --- PLAY AUDIO ---
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

            # Keep the script running while the music plays
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            print("\nPlayback finished.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

    finally:
        # Clean up the temporary file
        if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
            # Ensure the mixer is stopped before deleting the file
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
        # CRITICAL FIX: Connect to the database right before you use it.
        # The 'with' statement ensures the connection is properly closed.
        with libsql.connect("nmusic.db", sync_url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN) as conn:
            print("Database connection successful.")
            
            # Create the table if it doesn't exist (safe to run every time)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_audio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    audio_data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Insert the new data
            print(f"Inserting '{title}' into the database...")
            conn.execute(
                "INSERT INTO youtube_audio (title, audio_data) VALUES (?, ?);",
                (title, audio_data_bytes)
            )
            
            # Commit and sync the changes
            conn.commit()
            conn.sync()
            print("Upload complete and synced with Turso!")
            return True

    except Exception as e:
        # This will now catch database-specific errors
        print(f"\nAn error occurred during the database operation: {e}")
        return False
    

    
def get_url_from_name(song_name):
    videosSearch = VideosSearch(song_name, limit=1)
    results = videosSearch.result()
    if results['result']:
        return results['result'][0]['link']
    return "❌ No video found."

if __name__ == "__main__":
    if TURSO_AUTH_TOKEN == "YOUR_AUTH_TOKEN_HERE":
        print("ERROR: Please replace 'YOUR_AUTH_TOKEN_HERE' with your actual Turso token.")
        sys.exit(1)

    song_name = input("Enter Name:")
    youtube_url = get_url_from_name(song_name)    

    # 2. Perform the long task: Download the audio file FIRST
    downloaded_mp3_path = download_audio_from_youtube(youtube_url)

    # 3. Only if download is successful, proceed to the database part
    if downloaded_mp3_path and os.path.exists(downloaded_mp3_path):
        try:
            # Prepare data for insertion
            video_title = os.path.basename(downloaded_mp3_path).replace('.mp3', '')
            
            print(f"\nReading binary data from '{downloaded_mp3_path}'...")
            with open(downloaded_mp3_path, 'rb') as audio_file:
                binary_audio_data = audio_file.read()
                compressed_audio = zlib.compress(binary_audio_data)

            # 4. NOW, perform the short task: connect and upload
            upload_to_database(video_title, compressed_audio)

        except Exception as e:
            print(f"An error occurred while reading the file: {e}")
        finally:
            # 5. Clean up the downloaded file
            print(f"Cleaning up local file: {downloaded_mp3_path}")
            os.remove(downloaded_mp3_path)
    else:
        print("\nDatabase upload skipped because the audio download failed.")

    
    songsearch = input("Enter Song to be Played:")
    fetch_and_play_audio(songsearch)
