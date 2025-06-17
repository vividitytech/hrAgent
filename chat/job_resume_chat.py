import os, sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from processor.content_extractor import extract_text_with_formatting, get_text_from_url

from LLMChatAPI import LLMChat
def is_http_or_https(url_string):
  """
  Checks if a string starts with "http://" or "https://".

  Args:
    url_string: The string to check.

  Returns:
    True if the string starts with "http://" or "https://", False otherwise.
  """
  return url_string.startswith("http://") or url_string.startswith("https://")



def chat(pdfpath, job_info):
    if(is_http_or_https(job_info)):
       job_description = get_text_from_url(job_info)
    else:
       job_description = job_info
    resume = extract_text_with_formatting(pdfpath, default_pages=1)

    system_message = """You are expert in career development and you can provide suggestions and guidances to users for job hunting.
    Given a job posted by a compnay, you can understand user's resume, and check whether user is qualified for the job, including education, experience and skills.
    And you need to provide steps to revise user's resume to improve the successful chance for the job application. If possible, please also recommend related resources, such as github projects to users."""

    model = LLMChat(model_name="gemini-1.5-flash", provider="gemini", system_message=system_message)

    prompt = "This is the user's resume: \n" + resume + "\n\n"
    prompt = prompt + "This is the job posted: \n" + job_description
    
    response = model.chat(prompt)


if __name__ == "__main__":
   reponse = chat("resume/ComputerScienceResumedocx.pdf", "https://job-boards.greenhouse.io/pika/jobs/4608197007")
   print(reponse)