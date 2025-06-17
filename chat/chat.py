import os, sys
sys.path.append("/home/gangchen/Downloads/project/generative_model/python-genai/")
from google import genai
from google.genai import types
from flask import Flask, request, jsonify, render_template
#from flask_cors import CORS
#import google.generativeai as genai
from dotenv import load_dotenv
import uuid  # For generating unique session IDs
from PIL import Image  # Install Pillow: pip install Pillow
import random 

load_dotenv()

# app = Flask(__name__, static_folder='static', template_folder='templates')
#CORS(app)
from flask import Blueprint
#chat_bp = Blueprint('chatservice', __name__, template_folder='templates', url_prefix='/chat')
chat_bp = Flask(__name__, static_folder='static', template_folder='templates')

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
#genai.configure(api_key=GOOGLE_API_KEY)
#model = genai.GenerativeModel('gemini-pro')
client = genai.Client(api_key=GOOGLE_API_KEY)
# In-memory session store (replace with a database or cache in production!)
session_store = {}
model_list = ['gemini-2.0-flash-001', 'gemini-2.0-flash', "gemini-2.0-flash-thinking-exp", "gemini-2.5-pro-exp-03-25", "gemini-2.0-flash-lite", "gemini-1.5-flash"]

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    try:
        message = request.form.get('message')  # Get text message from FormData
        file = request.files.get('file')  # Get file from FormData
        session_id = request.form.get('session_id')

        if not message and not file:
            return jsonify({'error': 'No message or file provided'}), 400

        if not session_id:
            session_id = str(uuid.uuid4())
            model_id = random.randint(0, len(model_list)-1)
            session_store[session_id] = client.chats.create(model=model_list[model_id])#'gemini-2.0-flash-001') #model_list[model_id]
        elif session_id not in session_store:
            return jsonify({'error': 'Invalid session ID'}), 400

        chat = session_store[session_id]

        # Process the file (if any)
        if file:
            # Save the file (for demonstration purposes)
            filename = file.filename
            file_path = os.path.join('uploads', filename)  # Create an 'uploads' directory
            os.makedirs('uploads', exist_ok=True)  # Ensure directory exists
            file.save(file_path)

            #  Use Gemini-pro-vision (multimodal model) if there is a file
            if 'gemini-pro-vision' in genai.list_models():
                # Load the image for Gemini-pro-vision
                try:
                    img = Image.open(file_path)
                except Exception as e:
                    print(f"Error processing image: {e}")
                    return jsonify({'error': f"Error processing image: {e}"}), 400

                response = chat.send_message(content=[message, img]) # Use the image in prompt

            else:
                response = chat.send_message(message)

        else:
             response = chat.send_message(message)

        response_text = response.text

        session_store[session_id] = chat
        return jsonify({'response': response_text, 'session_id': session_id})

    except Exception as e:
        print(f"Error processing chat request: {e}")
        return jsonify({'error': str(e)}), 500



@chat_bp.route('/chat')
def index():
    return render_template('chat.html')

if __name__ == '__main__':
    chat_bp.run(debug=True, port=5001)
