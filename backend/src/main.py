from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from bloggen.main import run  # Import the run function from main.py
import os

#load environment variables
from bloggen.helper import load_env
load_env()

app = Flask(__name__)
CORS(app)

@app.route('/generate-blog', methods=['POST'])
def generate_blog():
    data = request.json
    if not data or 'topic' not in data:
        return jsonify({'error': 'Topic is required'}), 400
    topic = data.get('topic')

    # Prepare inputs for the run function
    inputs = {
        'topic': topic,
        'current_year': str(datetime.now().year)
    }

    try:
        # Call the run function with the specified topic
        content = run(inputs)  # Modify run to accept inputs and return file path

        # Return the generated file path or content
        return jsonify({'message': 'Blog generated successfully', 'blogContent': content}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)