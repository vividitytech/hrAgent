import re
import nltk #Needs to be downloaded
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
# Download necessary NLTK resources (run this once)
nltk.download('stopwords')
nltk.download('punkt')

def preprocess_text(text):
    """Preprocesses the text by lowercasing, removing punctuation, and removing stop words."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(text)
    filtered_text = [w for w in word_tokens if not w in stop_words]
    return " ".join(filtered_text) #Return back a single string

import spacy
#Load the Default Model.  This is huge
nlp = spacy.load("en_core_web_sm") # Small Model
#nlp = spacy.load("en_core_web_lg") # Large Model
def extract_skills3(text):
    """Extracts skills from the text using spaCy's NER."""
    doc = nlp(text)
    extracted_skills = []
    for ent in doc.ents:
        if ent.label_ in ["SKILL", "ORG", "PRODUCT", "TECHNOLOGY"]: #Add more label options, use test data.
            extracted_skills.append(ent.text)
    return extracted_skills

def extract_skills2(text, industry="it"):
    """Extracts skills from the text based on the specified industry."""
    skill_lists = {
        "it": "it_skills.json",
        "finance": "finance_skills.json",
        "chemistry": "chemistry_skills.json",
        "itc": "itc_skills.json"  #Example telecommunication
    }

    if industry not in skill_lists:
        print(f"Warning: No skill list found for industry '{industry}'. Using default IT skills.")
        industry = "it"

    skill_file = skill_lists[industry]

    try:
        with open(skill_file, "r") as f:
            skill_keywords = json.load(f) #Assumes that skills are an array.
    except FileNotFoundError:
        print(f"Error: Skill file '{skill_file}' not found. Using default IT skills.")
        industry = "it"
        skill_keywords = ["python", "java", "javascript", "sql"]  #Fallback skills

    extracted_skills = [skill for skill in skill_keywords if skill in text]
    return extracted_skills

def extract_skills(text):
    """Extracts skills from the text (using a simple keyword-based approach)."""
    # Expand this list with more skills relevant to your domain
    skill_keywords = ["python", "java", "c++", "javascript", "sql", "project management",
                      "communication", "leadership", "teamwork", "analysis", "machine learning",
                      "deep learning", "data analysis", "cloud computing", "aws", "azure", "docker",
                      "kubernetes"]
    extracted_skills = [skill for skill in skill_keywords if skill in text]
    return extracted_skills

def calculate_experience_score(cv_experience, job_experience):
    """Calculates an experience score based on similarity between CV and job experience."""
    # This is a simplified example. In a real application, you would need more sophisticated NLP techniques
    # to compare the descriptions of responsibilities and experience levels.
    cv_experience = preprocess_text(cv_experience)
    job_experience = preprocess_text(job_experience)
    if not cv_experience or not job_experience: #If not empty
        return 0 #Or skip and keep score.

    # Use TF-IDF to vectorize the text and calculate cosine similarity
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([cv_experience, job_experience])
    similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    return similarity_score

def check_education_match(cv_education, job_education):
    """Checks if the education section of the CV matches the job requirements."""
    cv_education = preprocess_text(cv_education)
    job_education = preprocess_text(job_education)
    if not cv_education or not job_education: #If not empty
        return 0
    #For a better check, check the degree levels instead.
    if cv_education in job_education:
        return 1.0
    return 0.0 #Match Failed


def calculate_keyword_score(cv_text, job_keywords):
  cv_text = preprocess_text(cv_text)
  job_keywords = preprocess_text(job_keywords)
  num_matches = 0
  for word in job_keywords.split():
    if word in cv_text:
      num_matches += 1
  return num_matches / len(job_keywords.split()) if len(job_keywords) > 0 else 0 #Return 0 if job is not specified

def assess_cv_match(cv_text, job_description):
    """Assesses the CV match based on skills, experience, education, and keywords."""

    # Extract features from CV and job description
    cv_skills = extract_skills(cv_text)
    job_skills = extract_skills(job_description)
    cv_experience = " ".join(re.findall(r"(?s)(?:Experience:)(.*?)(?:Education:|$)", cv_text))#Grab everything between Experience and Education.
    job_experience = "Detail Oriented, Self Motivated, Python, Java" #Example job experience - will need to read in from file.
    cv_education = " ".join(re.findall(r"(?s)(?:Education:)(.*)", cv_text))#Grab everything after education
    job_education = "Bachelors Degree" #Example job requirement - will need to read in from file
    job_keywords = "python, data analysis, data science" #Example Job Keywords - will need to read in from file.

    # Calculate matching scores
    skill_score = len(set(cv_skills) & set(job_skills)) / len(job_skills) if job_skills else 0 #If job skills empty, then value is 0
    experience_score = calculate_experience_score(cv_experience, job_experience)
    education_score = check_education_match(cv_education, job_education)
    keyword_score = calculate_keyword_score(cv_text, job_keywords)

    # Combine scores (adjust weights as needed)
    overall_score = (0.4 * skill_score +
                     0.3 * experience_score +
                     0.1 * education_score +
                     0.2 * keyword_score)

    return overall_score


# Main Function (Example Usage)
if __name__ == "__main__":
    # Example CV text (replace with your actual CV parsing logic)
    cv_text = """
    John Doe
    johndoe@example.com
    Summary:
    Highly motivated data scientist with 5+ years of experience in machine learning and data analysis.
    Skills:
    Python, Java, SQL, Machine Learning, Deep Learning, Data Analysis, Communication, Leadership
    Experience:
    Data Scientist, ABC Company (2018-Present)
    Responsibilities: Developed machine learning models, performed data analysis, led a team of data scientists.
    Education:
    Master of Science in Computer Science, XYZ University
    """

    # Example job description (replace with your actual job description)
    job_description = """
    Data Scientist
    ABC Company
    Job Description:
    We are seeking a data scientist with experience in machine learning and data analysis.
    Requirements:
    - 3+ years of experience in data science
    - Proficiency in Python and SQL
    - Master's degree in Computer Science or related field
    Responsibilities:
    - Develop machine learning models
    - Perform data analysis
    Skills:
    Python, SQL, Machine Learning, Deep Learning, Java
    """

    overall_score = assess_cv_match(cv_text, job_description)
    print(f"Overall CV Match Score: {overall_score:.2f}")