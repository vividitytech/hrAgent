from flask import Flask, render_template, request, jsonify, session
import openai
import os, sys
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from bs4 import BeautifulSoup
from LLMChatAPI import LLMChat

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from processor.content_extractor import extract_text_from_attachment


from flask import Flask, request, jsonify, render_template
#from flask_cors import CORS
#import google.generativeai as genai
from dotenv import load_dotenv
import uuid  # For generating unique session IDs
import random 

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
#genai.configure(api_key=GOOGLE_API_KEY)
#model = genai.GenerativeModel('gemini-pro')
# In-memory session store (replace with a database or cache in production!)
session_store = {}
model_list = ['gemini-2.0-flash-001', 'gemini-2.0-flash', "gemini-2.0-flash-thinking-exp", "gemini-2.5-pro-exp-03-25", "gemini-2.0-flash-lite", "gemini-1.5-flash"]

app = Flask(__name__)

# OpenAI API Key (Replace with your actual key)
openai.api_key = "YOUR_OPENAI_API_KEY"

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv'}  # Add more as needed
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_file_content(filepath):
    """Reads the content of a text-based file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='latin-1') as f: # try another encoding
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

def fetch_content_from_url(url):
    """Fetches and extracts text content from a URL."""
    try:
        response = requests.get(url, timeout=10)  # add timeout to avoid long waiting
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return text
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"
    except Exception as e:
        return f"Error processing URL: {e}"


def calculate_similarity(text1, text2):
    """Calculates cosine similarity between two texts."""
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([text1, text2])
    similarity = cosine_similarity(vectors)[0][1]
    return similarity

def generate_response(prompt):
    """Generates a response using OpenAI's GPT-3."""
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",  # Or your preferred engine
            prompt=prompt,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error generating response: {e}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file uploads."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'message': 'File uploaded successfully', 'filepath': filepath})
    else:
        return jsonify({'error': 'Invalid file type'})


@app.route('/start_session', methods=['POST'])
def start_session():
    # Generate a session ID (or retrieve an existing one)
    if 'session_id' not in session:  # Check if a session ID exists
        session['session_id'] = str(uuid.uuid4())  # Generate a UUID
        session_id = session['session_id']
        model_id = random.randint(0, len(model_list)-1)
        system_message = """You are expert in career development and you can provide suggestions and guidances to users for job hunting.
    Given a job posted by a compnay, you can understand user's resume, and check whether user is qualified for the job, including education, experience and skills.
    And you need to provide steps to revise user's resume to improve the successful chance for the job application. If possible, please also recommend related resources, such as github projects to users."""

        session_store[session_id] = LLMChat(model_name=model_list[model_id], provider="gemini", system_message=system_message)#'gemini-2.0-flash-001') #model_list[model_id]
    session_id = session['session_id']
    return jsonify({'session_id': session_id})


@app.route('/chat', methods=['POST'])
def chat():
    """Handles user messages and generates chatbot responses."""
    data = request.get_json()
    message = data.get('message')
    filepath = data.get('filepath')  # Optional: Path to uploaded file
    url = data.get('url') # Optional: URL to compare
    session_id = data.get('session_id')#request.form.get('session_id')
    if not message:
        return jsonify({'response': 'Please provide a message.'})


    context = ""
    if not session_id:
        session_id = str(uuid.uuid4())
        model_id = random.randint(0, len(model_list)-1)
        system_message = """You are expert in career development and you can provide suggestions and guidances to users for job hunting.
    Given a job posted by a compnay, you can understand user's resume, and check whether user is qualified for the job, including education, experience and skills.
    And you need to provide steps to revise user's resume to improve the successful chance for the job application. If possible, please also recommend related resources, such as github projects to users."""

        session_store[session_id] = LLMChat(model_name=model_list[model_id], provider="gemini", system_message=system_message)#'gemini-2.0-flash-001') #model_list[model_id]
    

    
    
    elif session_id not in session_store:
        return jsonify({'error': 'Invalid session ID'}), 400

    
    
    if filepath:
        context += f" This is the user's resume: \n: {extract_text_from_attachment(filepath)}.\n\n"

    if url:
        url_content = fetch_content_from_url(url)
        context += f" This is the job posted: {url_content}.\n"

        if filepath:
            file_content = extract_text_from_attachment(filepath)
            similarity = calculate_similarity(file_content, url_content)
            context += f" The similarity between the file and the URL content is: {similarity:.2f}.\n"
        else:
            context += " You can ask questions about the resume content.\n"

    model = session_store[session_id]

    prompt = message #f"{context} User: {message}\n Chatbot:"
    if len(context)>0:
        response = model.chat(prompt, new_system_message=context)
    else:
        response = model.chat(prompt)
    session_store[session_id] = model
    return jsonify({'response': response, 'session_id': session_id})

if __name__ == '__main__':
    app.run(debug=True, port=5005)