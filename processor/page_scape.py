joblink = "https://job-boards.greenhouse.io/pika/jobs/4608197007"

import requests
from bs4 import BeautifulSoup
import re

def extract_job_information2(url):
  """
  Extracts job information from a given URL, trying multiple common patterns.

  Args:
    url: The URL of the job posting.

  Returns:
    A dictionary containing extracted job information, or None if extraction fails.
    The dictionary keys will depend on the structure of the HTML page.
    This version tries to extract:
      - title
      - location
      - description
  """
  try:
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    soup = BeautifulSoup(response.content, 'html.parser')
    job_data = {}

    # --- Title Extraction (Trying multiple strategies) ---
    job_data['title'] = None
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
      title_element = soup.find(tag, class_=re.compile(r'title', re.IGNORECASE))  # Look for classes containing "title"
      if title_element:
        job_data['title'] = title_element.text.strip()
        break  # Stop after finding the first title

    if not job_data['title']:  # If still not found, try just the first h1
      h1 = soup.find('h1')
      if h1:
          job_data['title'] = h1.text.strip()

    # --- Location Extraction (Trying multiple strategies) ---
    job_data['location'] = None
    location_element = soup.find('span', class_=re.compile(r'location|city|country', re.IGNORECASE)) # Look for location in span
    if location_element:
      job_data['location'] = location_element.text.strip()
    else:
      div_location = soup.find('div', class_=re.compile(r'location|city|country', re.IGNORECASE)) # Look for location in div
      if div_location:
         job_data['location'] = div_location.text.strip()

    # --- Description Extraction (Trying multiple strategies) ---
    job_data['description'] = None
    for identifier in ['description', 'content', 'job-detail', 'details', 'job-description']: # Added details and job-description
        description_div = soup.find('div', id=re.compile(identifier, re.IGNORECASE))  # id containing identifier
        if description_div:
           job_data['description'] = description_div.get_text(separator='\n', strip=True)
           break # Stop after finding the first description

    if not job_data['description']:
        article_description = soup.find('article') # Try to find in article tag
        if article_description:
            job_data['description'] = article_description.get_text(separator='\n', strip=True)

    # --- Qualification Extraction (Trying multiple strategies) ---
    job_data['qualification'] = None
    for identifier in ['qualification', 'requirements', 'skills', 'qualifications', 'required-skills']: # Added more common identifiers
        qualification_div = soup.find('div', id=re.compile(identifier, re.IGNORECASE)) # Look for qualification
        if qualification_div:
            job_data['qualification'] = qualification_div.get_text(separator='\n', strip=True)
            break # Stop after finding the first qualification
        qualification_ul = soup.find('ul', id=re.compile(identifier, re.IGNORECASE)) # Check in ul tag
        if qualification_ul:
            job_data['qualification'] = '\n'.join([li.text.strip() for li in qualification_ul.find_all('li')]) # Get text from each li tag in ul
            break # Stop after finding the first qualification

    if not job_data['qualification']: # Try div with class name
        qualification_div_class = soup.find('div', class_=re.compile('qualification|requirements|skills', re.IGNORECASE))
        if qualification_div_class:
           job_data['qualification'] = qualification_div_class.get_text(separator='\n', strip=True)

    # --- Report if extraction failed ---
    if not any(job_data.values()):
      print(f"Warning: No job information could be extracted from {url}.  Inspect the HTML source.")

    return job_data

  except requests.exceptions.RequestException as e:
    print(f"Error fetching URL: {e}")
    return None
  except Exception as e:
    print(f"Error parsing HTML: {e}")
    return None
  
'''
def extract_job_information3(url):
    """
    Extracts job information from a given URL, using a multi-pronged approach.

    Args:
        url: The URL of the job posting.

    Returns:
        A dictionary containing extracted job information, or None if extraction fails.
        This version prioritizes finding content sections using keywords.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for successful request
        soup = BeautifulSoup(response.content, 'html.parser')
        job_data = {}

        # --- Title Extraction ---
        job_data['title'] = extract_title(soup)

        # --- Location Extraction ---
        job_data['location'] = extract_location(soup)

        # --- Description, Requirements, Qualifications (Combined Extraction) ---
        combined_text = extract_combined_content(soup)  # Extract all relevant text

        job_data['description'] = extract_section(combined_text, "Description")
        job_data['qualification'] = extract_section(combined_text, "Qualifications|Requirements")
        job_data['Skills'] = extract_section(combined_text, "Skills|skill") #Added duplicate requirements to make it more likely to find requirements in general


        # --- Report if extraction is poor ---
        if not any(job_data.values()):
            print(f"Warning: Could not extract any information from {url}. Examine HTML.")
        elif not job_data['description'] and not job_data['qualification'] and not job_data['Skills']:
            print(f"Warning: Limited information extracted from {url}. Inspect HTML for description/qualifications.")

        return job_data

    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None


def extract_title(soup):
    """Extracts the job title from the BeautifulSoup object."""
    for tag in ['h1', 'h2', 'h3']:
        title_element = soup.find(tag, class_=re.compile(r'title', re.IGNORECASE))
        if title_element:
            return title_element.text.strip()
    h1 = soup.find('h1')
    return h1.text.strip() if h1 else None


def extract_location(soup):
    """Extracts the job location from the BeautifulSoup object."""
    location_element = soup.find('span', class_=re.compile(r'location|city|country', re.IGNORECASE))
    if location_element:
        return location_element.text.strip()
    div_location = soup.find('div', class_=re.compile(r'location|city|country', re.IGNORECASE))
    return div_location.text.strip() if div_location else None

def extract_combined_content(soup):
    """Extracts and combines all potentially relevant text content from the page."""
    # Find all divs, articles, sections, and main tags
    elements = soup.find_all(['div', 'article', 'section', 'main'])
    combined_text = "\n".join([element.get_text(separator="\n", strip=True) for element in elements])
    return combined_text

def extract_section(text, section_name):
    """Extracts a specific section (e.g., Description, Qualifications) from the combined text.
    It looks for the section name as a heading and extracts all text until the next heading.
    """
    pattern = re.compile(rf"({section_name}:?)\s*\n(.*?)(?=\n[A-Z][a-z]+\s*:?|\Z)", re.DOTALL | re.IGNORECASE)  # Match section name and content
    match = pattern.search(text)

    if match:
        return match.group(2).strip()  # Return the captured content
    else:
        return None

'''

def extract_job_information(url):
    """Extracts job information from a given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        job_data = {}

        job_data['title'] = extract_title(soup)
        job_data['location'] = extract_location(soup)

        # First, attempt extraction based on <p><strong>Qualifications</strong></p><ul> structure
        qualifications = extract_qualifications_from_heading_list(soup)
        if qualifications:
            job_data['qualifications'] = qualifications
        else:
            # Fallback to the combined text and regex approach if the above fails
            combined_text = extract_combined_content(soup)
            job_data['qualifications'] = extract_qualifications(soup, combined_text)  # Using the existing function
        requirements = extract_requirements_from_heading_list(soup)
        if requirements:
            job_data['requirements'] = requirements
        else:
            # Fallback to the combined text and regex approach if the above fails
            combined_text = extract_combined_content(soup)
            job_data['requirements'] = extract_requirements(soup, combined_text) # Using the existing function
        combined_text = extract_combined_content(soup)
        job_data['description'] = extract_section(combined_text, "Description")

        # --- Report if extraction is poor ---
        if not any(job_data.values()):
            print(f"Warning: Could not extract any information from {url}. Examine HTML.")
        elif not job_data['description'] and not job_data['qualifications'] and not job_data['requirements']:
            print(f"Warning: Limited information extracted from {url}. Inspect HTML.")

        return job_data

    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None

def extract_qualifications_from_paragraph_list(soup):
    """Extracts qualifications specifically from <p>Qualifications/Requirements</p><ul> structure."""
    # qualifications_paragraph = soup.find('p', string=re.compile(r'Qualifications|Requirements|Qualification', re.IGNORECASE)) #finding p tag with qualification, requirement, or skills text
    qualifications_paragraph = soup.find('p', string=re.compile(r'.*(Qualifications|Requirements|Qualification).*', re.IGNORECASE))
    if qualifications_paragraph:  # Removed the strong tag check. Now checking if the p tag exists
        ul_element = qualifications_paragraph.find_next(['ul', 'ol'])  # Find the next <ul> or <ol> tag 

        if ul_element:
            qualifications = [li.text.strip() for li in ul_element.find_all('li')]  # Extract all list items
            return "\n".join(qualifications)  # Join them into a single string

    return None #Return none if qualifications are not found

def extract_requirements_from_paragraph_list(soup):
    """Extracts requirements specifically from <p>Qualifications/Requirements</p><ul> structure."""
    requirements_paragraph = soup.find('p', string=re.compile(r'.*(Skills|skill).*', re.IGNORECASE))
    if requirements_paragraph:  #Check if there is a paragraph
        ul_element = requirements_paragraph.find_next(['ul', 'ol']) 

        if ul_element:
            requirements = [li.text.strip() for li in ul_element.find_all('li')]
            return "\n".join(requirements)
    return None


def extract_qualifications_from_heading_list(soup):
    """Extracts qualifications specifically from <h*>Qualifications/Requirements</h*>(<ul> or <ol>) structure."""
    heading_tag = soup.find(
        ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'strong'], # Added more heading elements and p and strong
        string=re.compile(r'.*(Qualifications|Requirements).*', re.IGNORECASE)
    )

    if heading_tag:
        list_element = heading_tag.find_next(['ul', 'ol'])

        if list_element:
            qualifications = [li.text.strip() for li in list_element.find_all('li')]
            return "\n".join(qualifications)
        else:
            # Extract the text of the list item directly
            qualifications = [li.text.strip() for li in heading_tag.find_all('li')]
            return "\n".join(qualifications)

    return None

def extract_requirements_from_heading_list(soup):
    """Extracts requirements specifically from <h*>Requirements/Qualifications</h*>(<ul> or <ol>) structure."""
    heading_tag = soup.find(
        ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'strong'],  # Added more heading elements
        string=re.compile(r'.*(skill|Skills).*', re.IGNORECASE)
    )

    if heading_tag:
        list_element = heading_tag.find_next(['ul', 'ol'])

        if list_element:
            requirements = [li.text.strip() for li in list_element.find_all('li')]
            return "\n".join(requirements)
        else:
            # Extract the text of the list item directly
            requirements = [li.text.strip() for li in heading_tag.find_all('li')]
            return "\n".join(requirements)

    return None

def extract_title(soup):
    """Extracts the job title from the BeautifulSoup object."""
    for tag in ['h1', 'h2', 'h3']:
        title_element = soup.find(tag, class_=re.compile(r'title', re.IGNORECASE))
        if title_element:
            return title_element.text.strip()
    h1 = soup.find('h1')
    return h1.text.strip() if h1 else None


def extract_location(soup):
    """Extracts the job location from the BeautifulSoup object."""
    location_element = soup.find('span', class_=re.compile(r'location|city|country', re.IGNORECASE))
    if location_element:
        return location_element.text.strip()
    div_location = soup.find('div', class_=re.compile(r'location|city|country', re.IGNORECASE))
    return div_location.text.strip() if div_location else None


def extract_combined_content(soup):
    """Extracts and combines all potentially relevant text content."""
    elements = soup.find_all(['div', 'article', 'section', 'main'])
    combined_text = "\n".join([element.get_text(separator="\n", strip=True) for element in elements])
    return combined_text

def extract_section(text, section_name):
    """Extracts a section from the combined text."""
    pattern = re.compile(rf"({section_name}:?)\s*\n(.*?)(?=\n(?:[A-Z][a-z]+)\s*:?|\Z)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)

    if match:
        return match.group(2).strip()
    else:
        return None

def extract_qualifications(soup, combined_text):
    """Extracts qualifications, prioritizing list extraction."""
    # First, try to extract as a list:
    qualifications_list = extract_list_content(soup, "qualifications|requirements")
    if qualifications_list:
        return "\n".join(qualifications_list)

    # If not a list, use the section extraction method:
    return extract_section(combined_text, "Qualifications|Requirements|Skills")

def extract_requirements(soup, combined_text):
    """Extracts requirements, prioritizing list extraction."""
    # First, try to extract as a list:
    requirements_list = extract_list_content(soup, "requirements|qualifications|skills")
    if requirements_list:
        return "\n".join(requirements_list)

    # If not a list, use the section extraction method:
    return extract_section(combined_text, "Requirements|Qualifications|Skills")

def extract_list_content(soup, identifier):
    """Extracts content from list items (<li>) within a <ul> or <ol>."""
    list_items = []
    for list_tag in ['ul', 'ol']:
        list_element = soup.find(list_tag, id=re.compile(identifier, re.IGNORECASE))
        if list_element:
            for li in list_element.find_all('li'):
                list_items.append(li.text.strip())
            return list_items
    return None



text_to_test = "<p>Required Skills</p>"
pattern = re.compile(r'.*(Qualifications|Requirements|Skills).*', re.IGNORECASE)
match = pattern.search(text_to_test)
if match:
    print("Match found!")
    print(match.group(0))  # Print the entire match
else:
    print("No match found.")


'''
# Example usage
job_url = "https://job-boards.greenhouse.io/pika/jobs/4608197007"
#job_info = extract_job_information(job_url)


job_url = "https://jobs.lever.co/metabase/85f454d8-e795-4978-8a2b-4b8bfa7d7c37"
job_info = extract_job_information(job_url)

if job_info:
  print("Job Information:")
  for key, value in job_info.items():
    print(f"  {key}: {value}")
else:
  print("Failed to extract job information.")
'''