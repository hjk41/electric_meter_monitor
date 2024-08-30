from waitress import serve
from app import app
import logging

# Set up logging to a file
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    serve(app, host="0.0.0.0", port=5000)

