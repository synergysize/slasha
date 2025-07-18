import os
import sys
from app import app

if __name__ == '__main__':
    # Set environment variable to indicate we're running locally
    os.environ['FLASK_ENV'] = 'development'
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=8080, debug=True)