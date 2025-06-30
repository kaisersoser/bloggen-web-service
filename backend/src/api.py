from datetime import datetime
from flask import Flask, request, jsonify
import subprocess
import os
from bloggen.main import run

app = Flask(__name__)

@app.route('/generate-blog', methods=['POST'])
def generate_blog():
    data = request.json
    if not data or 'topic' not in data:
        return jsonify({'error': 'A Topic is required'}), 400
    topic = data.get('topic')

    # if not topic:
    #     return jsonify({'error': 'Topic is required'}), 400

    # Prepare inputs for the run function
    inputs = {
        'topic': topic,
        'current_year': str(datetime.now().year)
    }

    try:
        # Call the run function from main.py
        run(inputs)
        
        # Assuming the generated blog file is saved in a specific location
        generated_file_path = f'path/to/generated/blog/{topic.replace(" ", "_")}.txt'
        
        if os.path.exists(generated_file_path):
            with open(generated_file_path, 'r') as file:
                content = file.read()
            return jsonify({'content': content}), 200
        else:
            return jsonify({'error': 'Generated file not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)