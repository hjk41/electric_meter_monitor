import sys
from waitress import serve
from app import app
import logging
import time

# Set up logging to the console, print time, log level and message
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Set up logging to a file
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler('c:\\mine\\electric_log.txt'),
    logging.StreamHandler(sys.stdout)
])

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    while True:
        try:
            serve(app, host="0.0.0.0", port=5000)
        except Exception as e:
            logging.error(f"Error starting server: {str(e)}")
            time.sleep(5)

