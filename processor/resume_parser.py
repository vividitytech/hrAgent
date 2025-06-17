import re
from datetime import datetime

def parse_resume(resume_text):
    """
    Parses a resume text to extract education with degree/major/year and
    experience with company/years.

    Args:
        resume_text (str): The text content of the resume.

    Returns:
        dict: A dictionary containing the extracted information.  Returns None if parsing fails.
    """

    try:
        #resume_text = resume_text.lower()
        resume_text = re.sub(r'\n+', '\n', resume_text)
        resume_text = re.sub(r'\s+', ' ', resume_text)

        sections = {}


        # --- Name Extraction ---
        name_match = re.search(r"([a-z]+(?: [a-z]+)+)", resume_text)  # Basic name regex (two or more lowercase words)
        sections['name'] = name_match.group(1).strip() if name_match else None

        # --- Email Extraction ---
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", resume_text)
        sections['email'] = email_match.group(0) if email_match else None
        
        # --- Education Section ---
        education_keywords = r"(education|qualifications|academic qualifications|academic history)"
        education_match = re.search(education_keywords, resume_text, re.IGNORECASE)
        sections['education'] = []  # Initialize education list

        if education_match:
            start_edu = education_match.start()
            next_section_keywords = r"(experience|skills|projects|certifications|summary|objective|work history)"
            next_section_match = re.search(next_section_keywords, resume_text[start_edu + len(education_match.group(0)):], re.IGNORECASE)

            if next_section_match:
                end_edu = start_edu + len(education_match.group(0)) + next_section_match.start()
            else:
                end_edu = len(resume_text)

            education_section = resume_text[start_edu:end_edu].strip()

            # Updated regex to more reliably capture the year
            degree_pattern = r"(ph\.?d\.?|master|m\.?s\.?|bachelor|b\.?s\.?)\s+in\s+([\w\s&]+)(?:,\s*|,\s*university of .*\s*)?(?:,?\s*(\d{4}))?"
            for match in re.finditer(degree_pattern, education_section, re.IGNORECASE):
                degree = match.group(1).strip()
                major = match.group(2).strip()
                year = match.group(3)

                education_entry = {
                    'degree': degree,
                    'major': major,
                    'year': year if year else None  # Handle missing year
                }
                sections['education'].append(education_entry)

        # --- Experience Section ---
        experience_keywords = r"(Experience|EXPERIENCE|[Ww]ork experience|professional experience|employment history|work history)"
        experience_match = re.search(experience_keywords, resume_text)#, re.IGNORECASE)
        sections['experience'] = [] # Initialize experience list

        if experience_match:
            start_exp = experience_match.start()
            next_section_keywords = r"(education|skills|projects|certifications|summary|objective)"
            next_section_match = re.search(next_section_keywords, resume_text[start_exp + len(experience_match.group(0)):], re.IGNORECASE)

            if next_section_match:
                end_exp = start_exp + len(experience_match.group(0)) + next_section_match.start()
            else:
                end_exp = len(resume_text)
            experience_section = resume_text[start_exp:end_exp].strip()

            # Split experience section into individual entries
            experience_entries = re.split(r'\n(?=[A-Za-z])', experience_section)

            for entry in experience_entries:
                # Regex to find company and date range on the same line
                match = re.search(r'([\w\s&]+?)\s*,\s*((?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\s*\d{4}\s*-\s*(?:present|current|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\s*\d{4})', entry, re.IGNORECASE)
                if match:
                    company = match.group(1).strip()
                    date_range_str = match.group(2).strip()

                    # Extract start and end dates from the date range string
                    date_match = re.search(r'((?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\s*\d{4})\s*-\s*((?:present|current|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\s*\d{4})', date_range_str, re.IGNORECASE)

                    if date_match:
                        start_date_str = date_match.group(1)
                        end_date_str = date_match.group(2)

                        try:
                            start_date = datetime.strptime(start_date_str, '%B %Y')  # e.g., "January 2020"
                        except ValueError:
                            try:
                                start_date = datetime.strptime(start_date_str, '%b %Y')  # e.g., "Jan 2020"
                            except ValueError:
                                start_date = None
                                print(f"Warning: Could not parse start date: {start_date_str}")

                        if end_date_str.lower() in ("present", "current"):
                            end_date = datetime.now()
                        else:
                            try:
                                end_date = datetime.strptime(end_date_str, '%B %Y')
                            except ValueError:
                                try:
                                    end_date = datetime.strptime(end_date_str, '%b %Y')
                                except ValueError:
                                    end_date = None
                                    print(f"Warning: Could not parse end date: {end_date_str}")

                        if start_date and end_date:
                            experience_duration = (end_date - start_date).days / 365.25
                            experience_years = round(experience_duration, 2)
                        else:
                            experience_years = None
                            print("Could not get the experience years")

                        experience_entry = {
                            'company': company,
                            'years': experience_years
                        }
                        sections['experience'].append(experience_entry)

        # --- Skills Section (remaining sections...) ---
        skills_keywords = r"(skills|technical skills|key skills|skills and abilities)"
        skills_match = re.search(skills_keywords, resume_text, re.IGNORECASE)
        if skills_match:
            start_skills = skills_match.start()
            next_section_keywords = r"(education|experience|projects|certifications|summary|objective)"
            next_section_match = re.search(next_section_keywords, resume_text[start_skills + len(skills_match.group(0)):], re.IGNORECASE)

            if next_section_match:
                end_skills = start_skills + len(skills_match.group(0)) + next_section_match.start()
            else:
                end_skills = len(resume_text)

            sections['skills'] = resume_text[start_skills:end_skills].strip()
        else:
             sections['skills'] = []

        projects_keywords = r"(projects|personal projects|technical projects)"
        projects_match = re.search(projects_keywords, resume_text, re.IGNORECASE)

        if projects_match:
            start_proj = projects_match.start()
            next_section_keywords = r"(education|experience|skills|certifications|summary|objective)"
            next_section_match = re.search(next_section_keywords, resume_text[start_proj + len(projects_match.group(0)):], re.IGNORECASE)

            if next_section_match:
                end_proj = start_proj + len(projects_match.group(0)) + next_section_match.start()
            else:
                end_proj = len(resume_text)
            sections['projects'] = resume_text[start_proj:end_proj].strip()
        else:
            sections['projects'] = []

        return sections

    except Exception as e:
        print(f"An error occurred during parsing: {e}")
        return None

# Example Usage:
if __name__ == '__main__':
    # Example Usage
    resume_text = """
    John Doe
    john.doe@example.com
    (123) 456-7890

    Summary
    Highly motivated software engineer with 5+ years of experience.

    Education
    Ph.D. in Computer Science, University of Example, 2023
    M.S. in Electrical Engineering, Another University, 2020
    B.S. in Computer Science, University of Example, 2018

    Experience
    Software Engineer, Acme Corp, January 2018-Present
    * Developed and maintained web applications.
    Senior Software Engineer, Beta Corp, June 2022-December 2023
    * Led a team of developers.
    Skills
    Python, Java, JavaScript, SQL, AWS
    Projects
    Personal Website: Developed a personal website using React.
    """

    parsed_data = parse_resume(resume_text)

    if parsed_data:
        print("--- Parsed Resume Data ---")
        for section, content in parsed_data.items():
            print(f"\n--- {section.upper()} ---")
            if section == 'education':
                for edu in content:
                    print(f"  Degree: {edu['degree']}, Major: {edu['major']}, Year: {edu['year']}")
            elif section == 'experience':
                for exp in content:
                    print(f"  Company: {exp['company']}, Years: {exp['years']}")
            else:
                print(content)
    else:
        print("Resume parsing failed.")