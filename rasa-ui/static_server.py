import http.server
import socketserver
import os
import logging

LOG_DIR = "/app/actions/static/logs"
LOG_FILE = os.path.join(LOG_DIR, "static_server.log")
os.makedirs(LOG_DIR, exist_ok=True)  # Create logs directory if it doesn't exist
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Save to file
        logging.StreamHandler(),  # Keep console output
    ],
)
logger = logging.getLogger(__name__)

# Define the directory to serve
STATIC_DIR = "/app/actions/static/attachments"
PORT = 8000

if __name__ == "__main__":
    # Change to the static directory
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.chdir(STATIC_DIR)

    # Set up the handler
    Handler = http.server.SimpleHTTPRequestHandler

    # Start the server
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            logger.info(f"Serving static files at http://0.0.0.0:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        logger.error(f"Failed to start server: {e}")
        raise
