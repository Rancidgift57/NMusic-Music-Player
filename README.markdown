# NMusic - A Music Player

NMusic is a complete music streaming solution featuring a modern, installable Progressive Web App (PWA) for listening, a robust backend API for serving audio and managing queues, and a simple utility for populating the music database.

<img width="528" height="761" alt="image" src="https://github.com/user-attachments/assets/825c94fe-6aa0-45be-82b8-e5d2f78f9185" />


## Features

- **Progressive Web App (PWA):** A mobile-first, installable web app that works offline, providing a native app-like experience.
- **Streaming Audio:** Songs are streamed directly from a cloud database, ensuring efficient playback.
- **Dynamic Queue Management:** Add, remove, reorder, and clear the song queue in real-time.
- **Offline Capability:** The PWA caches the app interface and queue data, allowing it to load instantly and function without an internet connection.
- **Cloud Database:** Utilizes Turso (a distributed version of libSQL/SQLite) for fast and reliable data storage.
- **Multiple Clients:** Includes both a modern web interface and a command-line Python player for versatility.

## Project Architecture

The project is divided into several key components that work together:

- **FastAPI Backend (/APIFiles):** The core of the application. This API connects to the Turso database to fetch song data, serves the audio files for streaming, and manages the in-memory song queue.
- **PWA Frontend (/WebAppFiles):** The user-facing client. This is a static web application built with HTML, Tailwind CSS, and vanilla JavaScript. A Service Worker (sw.js) handles caching for offline functionality, and a Manifest file (manifest.json) makes the app installable.
- **Database Uploader (app.py):** A simple Flask-based utility used to add new songs to the Turso database. This is treated as an internal admin tool.
- **Python CLI Player:** A command-line interface for interacting with the music player, demonstrating an alternative client to the PWA.

```
[User's Phone/Desktop]         [Web Server]         [API Server]           [Database]
      |                            |                      |                      |
   (PWA Client) <-------------- (WebAppFiles)            |                      |
      |                                                   |                      |
      +-----------------------> (APIFiles) <-----------> (Turso DB)
      |         (API Calls)          |                      |
      |                              |                      |
(Python CLI Player) ---------------->+                      |
      |                                                     |
      |                                                     |
  [Admin] -> (Flask Uploader) ----------------------------->+
             (app.py)
```

## Folder Structure

```
.
├── APIFiles/               # Contains the main FastAPI backend code
│   └── main.py
├── WebAppFiles/            # Contains all files for the PWA frontend
│   ├── index.html
│   ├── manifest.json
│   └── sw.js
├── templates/              # HTML templates for the Flask database uploader
│   └── ...
├── app.py                  # Flask app for adding songs to the database
├── NmusicVer1.2.py               # Command-line Python music player
└── README.md               # This file
```

## Setup and Installation

### Prerequisites

- Python 3.8+
- Turso CLI
- An account on a hosting service like Render for deploying the API and static site.

### 1. Turso Database Setup
This project uses Turso as its database. First, you need to install and log in to the Turso CLI.

**Install the Turso CLI:**

```bash
# On macOS or Linux
curl -sSfL https://get.tur.so/install.sh | bash

# On Windows (using PowerShell)
irm https://get.tur.so/install.ps1 | iex
```

**Log in and Create a Database:**
Authenticate with your GitHub account:

```bash
turso auth login
```
Create a new database (e.g., nmusic-db):
```bash
turso db create nmusic-db
```
Get the database URL:
```bash
turso db show nmusic-db --url
```
 - Output will be something like: libsql://nmusic-db-yourusername.turso.io

Create an authentication token for your app:
```bash
turso db tokens create nmusic-db
```
# This will output a long token string.

Create a Table for Songs:
Connect to the database shell to create a table for storing song data:
```bash
turso db shell nmusic-db
```

In the Turso SQL shell, run the following command to create a songs table:
```sql
      CREATE TABLE IF NOT EXISTS youtube_audio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    audio_data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
```

Exit the shell by typing:
```sql
.quit
```
Important: Save the database URL and the auth token. You will need them for the next step.

CONNECT

**Authenticate with your GitHub account:**

```bash
turso auth login
```

**Create a new database (e.g., nmusic-db):**

```bash
turso db create nmusic-db
```

**Get the database URL:**

```bash
turso db show nmusic-db --url
# Output will be something like: libsql://nmusic-db-yourusername.turso.io
```

**Create an authentication token for your app:**

```bash
turso db tokens create nmusic-db
# This will output a long token string.
```

**Important:** Save the database URL and the auth token. You will need them for the next step.

### 2. Environment Variables

To keep your credentials secure, we use environment variables. Create a file named `.env` in the root directory of your project.

**.env file:**

```
TURSO_DB_URL="your-turso-database-url-here"
TURSO_AUTH_TOKEN="your-turso-auth-token-here"
```

Replace the placeholder values with the actual URL and token you got from the Turso CLI. Your Python applications (`app.py` and `APIFiles/main.py`) are configured to read from this file for local development.

### 3. API Deployment

The core API is built with FastAPI and is located in the `APIFiles` directory.

**Deploy to a Host:** Deploy the `APIFiles/main.py` application to a web service like Render.

- **Service Type:** Web Service
- **Build Command:** `pip install -r requirements.txt` (You will need to create a `requirements.txt` file with `fastapi`, `uvicorn`, `libsql`, `python-dotenv`, etc.)
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Add Environment Variables on Render:** In your Render service settings, go to the "Environment" section and add the `TURSO_DB_URL` and `TURSO_AUTH_TOKEN` with the same values from your `.env` file. This is how the deployed API will access the database.

### 4. Web App (PWA) Deployment

The frontend is a static site located in `WebAppFiles`.

- **Update API URL (if necessary):** Ensure the `API_BASE_URL` constant in `WebAppFiles/index.html` points to your deployed FastAPI server URL.
- **Deploy as a Static Site:** Deploy the `WebAppFiles` folder to a static site hosting service (Render, Netlify, Vercel, etc.).
- **Publish Directory:** `WebAppFiles`
- **Build Command:** (Leave this blank)

## Usage

### Using the Web App

- Navigate to the URL of your deployed static site on a desktop or mobile browser.
- The browser should prompt you to "Install App" or "Add to Home Screen".
- Once installed, you can launch it like a native app from your home screen or app drawer.
- Use the input field to add songs to the queue and the playback controls to listen.

### Using the Python Player

- Ensure the `NmusicVer1.2.py` script is configured with the correct API URL.
- Run the script from your terminal: `python NmusicVer1.2.py`
- Follow the on-screen prompts to play music.

 **Contributing**
 - We welcome contributions to NMusic! To contribute, please follow these steps:
 - Fork the Repository: Create a fork of the NMusic repository on your GitHub account.
 - Clone the Fork: Clone your forked repository to your local machine.
 - Create a Branch: Create a new branch for your feature or bug fix (git checkout -b feature/your-feature-name).
 - Make Changes: Implement your changes, ensuring to follow the existing code style and include tests where applicable.
 - Commit Changes: Commit your changes with a clear and descriptive commit message.
 - Push to GitHub: Push your branch to your forked repository (git push origin feature/your-feature-name).
 - Create a Pull Request: Open a pull request against the main repository's main branch, providing a detailed description of your changes.

Please ensure your code adheres to the project's coding standards and includes appropriate documentation. For major changes, open an issue first to discuss your proposed changes.

### API Auto-Pinger
This project includes an automated script that runs on a schedule to keep the nmusic API alive and prevent it from "sleeping" due to inactivity on Render's free hosting tier.
**How It Works**
The keep-alive mechanism uses GitHub Actions to run a Python script on a regular schedule.
 - Scheduled Trigger: A GitHub Actions workflow, defined in .github/workflows/pinger.yml, is scheduled to run automatically every 5 minutes.
 - Python Script Execution: When the workflow runs, it executes the pinger.py script.
 - Continuous Pinging: This script runs in a loop for about 4.5 minutes, sending an HTTP GET request to the API endpoint (Your Deployed API URL) every 50 seconds.
This ensures that the Render service receives traffic consistently, preventing it from spinning down.

**Monitoring the Pinger**
You can easily check if the pinger is working correctly:
 - Navigate to the Actions tab in this GitHub repository.
 - Click on the "API Pinger" workflow in the left sidebar.
 - You will see a history of all the workflow runs. A green checkmark (✅) indicates a successful run.
 - Click on any successful run to view the detailed logs and see the "SUCCESS" messages from the Python script.
No manual intervention is needed. The workflow is fully automated.

**Contact**
 - For questions, suggestions, or support, please reach out to the NMusic team:
 - Email: nnair7598@gmail.com


### Thank you🙏
