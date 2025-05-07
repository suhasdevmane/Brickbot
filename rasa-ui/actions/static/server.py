from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)

# Configure logging


# Define the path to the attachments folder (same directory as server.py)
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attachments")


@app.route("/attachments/<path:filename>")
def serve_static(filename):
    try:
        return send_from_directory(STATIC_FOLDER, filename)
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        abort(500)


# Health check endpoint
@app.route("/health")
def health():
    logger.info("Health check requested")
    return {"status": "healthy"}, 200
