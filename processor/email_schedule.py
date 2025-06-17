import os
import time
import threading
import queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3  # Or your database of choice
import json
import datetime  # For handling date and time operations
import pytz  # For timezone conversions
import imaplib  # For reading emails
import email  # For parsing emails
import re  # For regular expressions

# Replace with your service account details
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

script_dir_os = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir_os)
'''
import config



# Replace with your email credentials (Gmail example)
EMAIL_ADDRESS = config.EMAIL_ADDRESS#"newhorizontalinc@gmail.com"#"your_email@gmail.com"
EMAIL_PASSWORD = config.EMAIL_PASSWORD #"lyae kkvs gdyu kpqq "# "your_password" # Or your App Password

SMTP_SERVER = config.SMTP_SERVER #"smtp.gmail.com" #"your_smtp_server"  # Your SMTP Server details, for Gmail it's smtp.gmail.com
SMTP_PORT = config.SMTP_PORT #587  # Your SMTP Port, for Gmail it's 587
IMAP_SERVER = config.IMAP_SERVER #"imap.gmail.com" #"your_imap_server"  # Your IMAP Server, for Gmail it's imap.gmail.com
IMAP_PORT = config.IMAP_PORT # 993  # Your IMAP Port, for Gmail it's 993

# Define the target timezone
TARGET_TIMEZONE = config.TARGET_TIMEZONE # 'America/Los_Angeles'  # Example Los Angeles

# Regular Expression for Extracting Schedule from Email
TIME_SLOT_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")


# Calendar API
SCOPES = config.SCOPES # ['https://www.googleapis.com/auth/calendar']#.readonly']
SERVICE_ACCOUNT_FILE = config.SERVICE_ACCOUNT_FILE #'apptest-35403-c3944a05a142.json'  # Replace the location or set to environment
'''
TIME_SLOT_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
MEETING_REQUEST_SUBJECT = "Meeting Availability Request"

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'users')  # Table name from env
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'password')  # Table name from env
SMTP_SERVER = os.getenv('SMTP_SERVER', "smtp.gmail.com")  # Table name from env
SMTP_PORT = os.getenv('SMTP_PORT', 587)  # Table name from env
IMAP_SERVER = os.getenv('IMAP_SERVER', "imap.gmail.com")  # Table name from env
IMAP_PORT = os.getenv('IMAP_PORT', 993)  # Table name from env
TARGET_TIMEZONE = os.getenv('TARGET_TIMEZONE', 'America/Los_Angeles')
SCOPES = [os.getenv('SCOPES', 'https://www.googleapis.com/auth/calendar')]
SERVICE_ACCOUNT_FILE =  os.path.join(parent_dir, 'apptest-35403-c3944a05a142.json') #os.getenv('SERVICE_ACCOUNT_FILE',
calendar_id = os.getenv('CALENDAR_ID', 'none')  # Table name from env

class WorkflowTask:
    """
    A class representing a generalized multi-stage workflow task with
    status tracking, dependency management, and email notification.
    Uses a dictionary to define phrases.
    """

    def __init__(self, user_id, task_id, friend_email, email_subject, job_title, job_desc, job_url, phrase_definitions, db_path,
                 target_timezone=TARGET_TIMEZONE):
        """
        Initializes the WorkflowTask.
        """
        self.user_id = user_id
        self.task_id = task_id
        self.friend_email = friend_email  # Email sent out
        self.email_subject = email_subject
        self.job_title = job_title
        self.job_desc = job_desc
        self.job_url = job_url
        self.phrase_definitions = phrase_definitions
        self.db_path = db_path
        self.target_timezone = target_timezone  # Timezone
        self.status = {phrase: "pending" for phrase in phrase_definitions}  # all phrases will have status pending
        self.status["overall"] = "pending"
        self.results = {}  # Store results of each phrase
        self.lock = threading.Lock()  # Threading lock for status updates
        self.email_replied_event = threading.Event()  # use a thread safe event to know friend email replied
        self.email_check_complete = False  # Flag
        self.error_message = None
        self.dependency_events = {phrase: threading.Event() for phrase in phrase_definitions if
                                  phrase != list(phrase_definitions.keys())[
                                      0]}  # Event for dependency. Except first
        self._create_task_entry_in_db()  # Create the task entry in DB

    def _get_connection(self):
        """Helper to get the database connection."""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return None

    def _create_task_entry_in_db(self):
        """Creates an entry in the database for this task."""
        conn = self._get_connection()
        if conn is None:
            return  # Exit if connection fails

        try:
            cursor = conn.cursor()
            # Store task_id, user_id, initial status as JSON
            initial_status_json = json.dumps(self.status)

            cursor.execute("""
                INSERT INTO tasks (task_id, user_id, status, create_time)
                VALUES (?, ?, ?, ?)
            """, (self.task_id, self.user_id, initial_status_json, int(time.time())))

            conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating task entry in DB: {e}")
        finally:
            conn.close()

    def _update_task_status_in_db(self):
        """Update the task status in the database with a json format"""
        conn = self._get_connection()
        if conn is None:
            return  # Exit if connection fails

        try:
            cursor = conn.cursor()
            status_json = json.dumps(self.status)

            cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (status_json, self.task_id))
            conn.commit()

        except sqlite3.Error as e:
            print(f"Error creating task entry in DB: {e}")
        finally:
            conn.close()

    def run(self):
        """
        Executes the workflow task in a separate thread.
        """
        try:
            phrase_results = {}  # Store results to pass dependencies
            phrase_names = list(self.phrase_definitions.keys())  # ordered phrases

            for i, phrase_name in enumerate(phrase_names):
                phrase_def = self.phrase_definitions[phrase_name]
                depends_on = phrase_def.get("depends_on")
                phrase_func = phrase_def["function"]

                if depends_on:
                    print(f"{phrase_name} is awaiting for {depends_on} to finish")
                    self.dependency_events[phrase_name].wait()  # Wait for dependency
                    dependency_result = phrase_results[depends_on]  # after, await get the dependency
                else:
                    dependency_result = None

                result = self._run_phrase(phrase_name, phrase_func, dependency_result)
                phrase_results[phrase_name] = result  # Save to phrases result for next phrase use
                if i + 1 < len(phrase_names):
                    if phrase_names[i + 1] in self.dependency_events:
                        print(f"set Event for {phrase_names[i + 1]} for {phrase_name} finished")
                        self.dependency_events[phrase_names[i + 1]].set()  # release the event to next one.

            self._set_overall_status("completed")
            self._update_task_status_in_db()  # After the jobs are complete, update the DB

        except Exception as e:
            self._set_overall_status("failed")
            self.error_message = str(e)
            self._update_task_status_in_db()
            print(f"Task {self.task_id} failed: {e}")

        finally:
            self.send_completion_email()

    def _run_phrase(self, phrase_name, phrase_func, dependency_result):
        """
        Executes a single phrase of the workflow.
        """
        with self.lock:
            self.status[phrase_name] = "running"
            self._update_task_status_in_db()

        try:
            if dependency_result is not None:
                result = phrase_func(self.task_id, dependency_result,
                                     self.target_timezone, self.friend_email, self.email_subject, self)  # Pass target timezone
            else:
                result = phrase_func(self.task_id, self.friend_email, self.target_timezone,
                                     self.email_replied_event,
                                     self)  # Pass all arguments

            with self.lock:
                self.status[phrase_name] = "completed"
                self.results[phrase_name] = result
                self._update_task_status_in_db()
            return result

        except Exception as e:
            with self.lock:
                self.status[phrase_name] = "failed"
                self.error_message = str(e)
                self._update_task_status_in_db()
            raise  # Re-raise to stop workflow

    def _set_overall_status(self, status):
        """Sets the overall status of the workflow."""
        with self.lock:
            self.status["overall"] = status
            self._update_task_status_in_db()

    def get_status(self):
        """Returns the current status of the workflow."""
        with self.lock:
            return self.status.copy()

    def get_results(self):
        """Returns the results of the completed phrases."""
        with self.lock:
            return self.results.copy()

    def send_completion_email(self):
        """Sends an email notification to the user."""
        try:
            # Implement your email sending logic here (using smtplib, etc.)
            subject = f"Task {self.task_id} Completion Notification"
            body = f"Task {self.task_id} for user {self.user_id} has {self.status['overall']}."
            if self.status['overall'] == "failed":
                body += f" Error message: {self.error_message}"
                body += "\n\n\nPlease check your availability and add more time slots, thanks!"
            body += f"\n\nStatus: {self.get_status()}"
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = EMAIL_ADDRESS  # Replace with your email address
            msg['To'] = self.friend_email

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:  # Replace with your SMTP server details
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)  # Replace with your email credentials
                server.sendmail(EMAIL_ADDRESS, self.friend_email, msg.as_string())

            print(f"Email sent to {self.friend_email} for task {self.task_id}")
        except Exception as e:
            print(f"Error sending email for task {self.task_id}: {e}")
            # Consider logging the email sending failure for later retry


class WorkflowManager:
    """
    Manages the execution and status tracking of multiple WorkflowTasks,
    persisting task status in a database.
    """

    def __init__(self, db_path="workflow.db"):
        """
        Initializes the WorkflowManager.
        """
        self.db_path = db_path
        self.tasks = {}  # task_id: task_object
        self.lock = threading.Lock()  # Threadsafe task management
        self._create_tables()

    def _get_connection(self):
        """Helper to get the database connection."""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return None

    def _create_tables(self):
        """Creates the tasks table if it doesn't exist."""
        conn = self._get_connection()
        if conn is None:
            return  # Exit if connection fails

        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    create_time INTEGER NOT NULL
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tasks table: {e}")
        finally:
            conn.close()

    def submit_task(self, user_id, friend_email, email_title, job_title, job_desc, job_url, phrase_definitions):
        """Submits a new workflow task. Generates a unique task ID."""

        task_id = f"{user_id}_{int(time.time())}"  # Simple task ID (can be improved)
        task = WorkflowTask(user_id, task_id, friend_email, email_title, job_title, job_desc, job_url, phrase_definitions, self.db_path)
        with self.lock:
            self.tasks[task_id] = task
        thread = threading.Thread(target=task.run)
        thread.start()
        return task_id

    def get_task_status(self, task_id):
        """Returns the status of a given task."""
        conn = self._get_connection()
        if conn is None:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM tasks WHERE task_id = ?", (task_id,))
            result = cursor.fetchone()

            if result:
                # Load the status from JSON
                status = json.loads(result[0])
                return status
            else:
                return None  # Task not found
        except sqlite3.Error as e:
            print(f"Error getting task status from DB: {e}")
            return None
        finally:
            conn.close()

    def get_task_results(self, task_id):
        """Due to complexity, not implemented for user can pull results from DB
          Can be implemented if needed
          Need a database structure to store all the phrases results as well
        """
        return None


# --- Helper functions ---
def send_email(recipient_email, subject, body):
    """Sends an email."""
    try:
        sender_email = EMAIL_ADDRESS  # Use global variable
        sender_password = EMAIL_PASSWORD

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        msg.attach(MIMEText(body, 'plain'))  # add body

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:  # Use global
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        print(f"Email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def get_availability_from_email(task_id, friend_email, target_timezone, email_replied_event, workflow_task, phrase_name="get_friend_availability"):
    """
    Sends email, and starts another thread to periodically check if the
    friend has replied. A flag ensures we don't check the email repeatedly
    after a reply is received.
    """
    if not workflow_task.email_check_complete:  # to check if the task is finished. prevent duplicated call
        check_email_thread = threading.Thread(target=periodic_check_email,
                                              args=(task_id, friend_email, target_timezone,
                                                    email_replied_event, workflow_task,phrase_name))  # pass the whole task to notify

        try:
            send_email(friend_email,  workflow_task.email_subject, #MEETING_REQUEST_SUBJECT,
                       "Hi,\n\nI'm trying to schedule a meeting with you. Please let me know what times you're available.\nFormat: YYYY-MM-DD HH:MM - YYYY-MM-DD HH:MM\n\nThanks!")  # send email
            check_email_thread.start()  # call the thread
        except Exception as e:
            print(f"Error sending meeting request email: {e}")
            workflow_task.email_replied_event.set() # Set the event to allow next stage

    print(f"get_availability_from_email awaiting {task_id}")
    email_replied_event.wait()
    print(f"get_availability_from_email finished waiting for{task_id}")
    email_replied_event.clear()  # clear for potential reuse (though unlikely in this design)
    workflow_task.email_check_complete = True
    if workflow_task.results[phrase_name]:
        return workflow_task.results[phrase_name]
    return None  # doesn't return the times, the info can be retrived from result

def periodic_check_email(task_id, friend_email, target_timezone, email_replied_event, workflow_task, phrase_name):
    """
    Periodically checks the inbox for a reply from the friend, setting
    the email_replied_event when a reply is found and parsed.
    """
    try:
        while not workflow_task.email_check_complete:  # check if has result
            try:
                availability = check_email_for_availability(task_id, EMAIL_ADDRESS, EMAIL_PASSWORD, friend_email,
                                                             workflow_task.email_subject)#MEETING_REQUEST_SUBJECT)

                if availability:
                    # workflow_task.results["friend_availability"] = availability  # Store availability
                    workflow_task.results[phrase_name] = availability  # Store availability
                    email_replied_event.set()
                    print(f"Found and setting event for the meeting! {task_id}")  # to know that this has been setted before
                    break
            except Exception as e:
                print(f"Error during check_email_for_availability: {e}")
            finally:
                time.sleep(10)  # pull email every 10 seconds
        print(f"quiting finding emails with flag is True   {task_id}")  # check if there is duplicate
    except Exception as e:
        print(f"Error in periodic_check_email: {e}")

def check_email_for_availability(task_id, email_address, email_password, friend_email, subject, unread_only=True):
    """
    Checks the inbox for an email containing availability slots from friend.
    Will need subject and friend email to check to make sure it from your friend.
    """
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(email_address, email_password)
        mail.select('inbox')

        # Build the filter to select only the email with particular subject and friend email
        search_criteria = f'(FROM "{friend_email}" SUBJECT "{subject}")'
        if unread_only:
            search_criteria += ' UNSEEN'

        result, data = mail.search(None, search_criteria)
        mail_ids = data[0]

        if not mail_ids:
            print("No emails found in inbox with the given criteria.")
            return None

        mail_id_list = mail_ids.split()
        latest_email_id = mail_id_list[-1]

        try:
            result, data = mail.fetch(latest_email_id, "(RFC822)")  # Fetch the email

            raw_email = data[0][1]
            raw_email_string = raw_email.decode('utf-8')
            email_message = email.message_from_string(raw_email_string)

            # Extract the body of the email
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()  # decode body of the email
                    # Extract dates and times from the email body
                    time_slots = TIME_SLOT_PATTERN.findall(body)  # find the time slot from regular expression
                    availability = []
                    target_tz = pytz.timezone(TARGET_TIMEZONE)

                    for start_str, end_str in time_slots:
                        try:
                            start_time = datetime.datetime.strptime(start_str, '%Y-%m-%d %H:%M')
                            end_time = datetime.datetime.strptime(end_str, '%Y-%m-%d %H:%M')
                            # localize time
                            start_time = target_tz.localize(start_time)
                            end_time = target_tz.localize(end_time)
                            availability.append((start_time, end_time))

                        except ValueError as e:
                            print(f"Error parsing time string: {e}")
                            continue

                    # Clean up (optional - mark email as read)
                    # mail.store(latest_email_id, '+FLAGS', '\\Seen')
                    mail.close()
                    mail.logout()

                    return availability
        except Exception as e:
            print(f"Error processing email {latest_email_id.decode()}: {e}")
            #import traceback, traceback.print_exc()  # Print the full exception traceback for debugging
            # Mark as UNREAD (add "UNSEEN" flag) upon exception
            mail.store(latest_email_id, "-FLAGS", "\\Seen")  #  Adds the UNSEEN flag (marks as unread)
            print(f"Marked email {latest_email_id.decode()} as UNREAD due to error.")

    except Exception as e:
        print(f"Error checking email: {e}")
        return None

def check_my_availability(task_id, friend_availability, target_timezone, friend_email, subject, workflow_task):
    """
    Checks user's calendar availability for each slot in friend's availability
    and adds the available slot to the available slots.

    This part requires Google Calendar API setup.
    """
    print(f"Checking calendar for overlapping availability for task {task_id} with friend's availability: {friend_availability}")

    # Authenticate and build the Google Calendar API service
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        service = build('calendar', 'v3', credentials=creds)

        # Get the calendar ID (replace with your calendar ID)
        # calendar_id = 'newhorizontalinc@gmail.com'# 'your_calendar_id@group.calendar.google.com'  # Example Calendar ID

        # Get timezone info, you can cache this
        target_tz = pytz.timezone(target_timezone)

        my_availability = []
        for friend_start, friend_end in friend_availability:
            #Set the timezone to Z
            start_time_utc = friend_start.isoformat() #+ 'Z'
            end_time_utc = friend_end.isoformat() #+ 'Z'
            # Query for events in the period, now time zone aware
            events_result = service.events().list(calendarId=calendar_id, timeMin=start_time_utc,
                                                  timeMax=end_time_utc,
                                                  maxResults=10, singleEvents=True, orderBy='startTime').execute()

            events = events_result.get('items', [])

            # If no events are in that period, then add the available period
            if not events:
                my_availability.append((friend_start, friend_end))  # Timezone aware

        print(f"My Available Time: {my_availability}")
        if my_availability:
            suggested_time = my_availability[0]
            print(f"Found overlapping slots for task {task_id}: {suggested_time}")
            return suggested_time
        else:
            print(f"No overlapping slots found for task {task_id}.")
            return None  # or "No suitable time found"
    except Exception as e:
        print(f"Error checking calendar: {e}")
        return None

def find_overlapping_slots(my_availability, friend_availability):
    """Finds overlapping time slots between two lists of availability."""
    overlapping_slots = []
    for my_start, my_end in my_availability:
        for friend_start, friend_end in friend_availability:
            latest_start = max(my_start, friend_start)
            earliest_end = min(my_end, friend_end)
            delta = (earliest_end - latest_start).total_seconds()
            if delta > 0:  # There is an overlap
                overlapping_slots.append((latest_start, earliest_end))

    return overlapping_slots

def schedule_meeting(task_id, overlapping_slot, target_timezone, friend_email, subject, workflow_task):
    """Placeholder: Sends a meeting invite."""
    if overlapping_slot:
        start_time, end_time = overlapping_slot
        print(f"Simulating sending meeting invite for task {task_id} at {start_time} to {end_time}...")
        time.sleep(2)
        print(f"Meeting invite sent for task {task_id}!")

        # send confirmation email
        send_email(friend_email, subject + " schedule confirmation", f"Hi {workflow_task.user_id}, \nWe are glad to to move forward with your {workflow_task.job_title} application with us. \nWe will have a call from {start_time} to {end_time}, and I am looking forward to chatting with you soon!\nThank you!")
        
        creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        # Get the calendar ID (replace with your calendar ID)
        # calendar_id = 'newhorizontalinc@gmail.com'# 'your_calendar_id@group.calendar.google.com'  # Example Calendar ID

        create_event(service, calendar_id, start_time, end_time, workflow_task.job_title, workflow_task.job_desc, workflow_task.job_url)
        
        return f"Meeting scheduled at {start_time} to {end_time}"
    else:
        print(f"No suitable time found for task {task_id}, cannot schedule the meeting")
        return "No suitable time found, meeting not scheduled"


def create_event(service, calendar_id, start_time, end_time, summary, description=None, job_url=None, attendees=None):
    """
    Creates an event in the specified Google Calendar.

    Args:
        service:  The Google Calendar API service object.
        calendar_id: The ID of the calendar to create the event in (usually 'primary' for the user's main calendar).
        start_time:  A datetime object representing the start time of the event (in UTC).
        end_time:  A datetime object representing the end time of the event (in UTC).
        summary:  The title of the event.
        description: (Optional) A description of the event.
        attendees: (Optional) A list of dictionaries, where each dictionary represents an attendee.  Example:
                  `[{'email': 'attendee1@example.com'}, {'email': 'attendee2@example.com'}]`
    Returns:
        The ID of the created event, or None if an error occurred.
    """
    event = {
        'summary': summary,
        'description': job_url + '\n\n' + description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC', # Important to specify the timezone.
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC', # Important to specify the timezone.
        },
        'attendees': attendees or [],  # Use an empty list if attendees is None
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    try:
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
        return event.get('id')
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None
    
# Dummy 2nd phrase call
def phrase2(task_id, a, target_timezone):
    print(f"calling phrase2 {task_id}")
    return "OK"


'''
Okay, to provide a truly runnable check_my_availability function that integrates with Google Calendar API, I'll need to provide a more complete example that includes authentication and access to your calendar data. This is more involved, so I'll break it down.

Important Notes Before You Start:

    Google Cloud Project: You'll need a Google Cloud Project. If you don't have one, create one at https://console.cloud.google.com/.

    Enable Google Calendar API: In your Google Cloud Project, enable the Google Calendar API. Search for "Google Calendar API" in the API Library and enable it.

    Service Account: Create a service account in your Google Cloud Project. This is a special type of account used by applications to access Google APIs.

        Go to "IAM & Admin" -> "Service Accounts" in the Google Cloud Console.

        Click "+ Create Service Account".

        Give it a name and description.

        Grant this service account the "Project" -> "Viewer" role to enable read access

        (Important!) Create a JSON key file for the service account. Download this key file and store it securely. You'll need the path to this file in your code.

    Share Your Calendar (Important): You need to explicitly share your Google Calendar with the service account. Find the service account's email address (it will look like your-service-account-name@your-project-id.iam.gserviceaccount.com) and add it as a "See all event details" or "See only free/busy (hide details)" under your calendar sharing settings.

Here's the updated check_my_availability function:
'''

def schedule_via_email(manager, user_id, user_email, subject):

    # Define the workflow tasks as a dictionary
    phrase_definitions = {
        "get_friend_availability": {"function": get_availability_from_email},
        "check_my_availability": {"function": check_my_availability, "depends_on": "get_friend_availability"},
        "schedule_meeting": {"function": schedule_meeting, "depends_on": "check_my_availability"},
    }

    job_title = "software engineer"
    job_desc = "bala bala"
    job_url = "https://www.metacareers.com/jobs/804955741151464/"
    
    task_id = manager.submit_task(user_id, user_email, subject,job_title, job_desc, job_url, phrase_definitions)
    print(f"Submitted task with ID: {task_id}")

    # Simulate checking task status
    time.sleep(1)
    status = manager.get_task_status(task_id)
    print(f"Task {task_id} status: {status}")
    return task_id


if __name__ == "__main__":
    manager = WorkflowManager(db_path="workflow.db")

    user_id = "test_user"
    friend_email = "chenricher@gmail.com"  # Add a friend to schedule meeting

    # Define the workflow tasks as a dictionary
    phrase_definitions = {
        "get_friend_availability": {"function": get_availability_from_email},
        "check_my_availability": {"function": check_my_availability, "depends_on": "get_friend_availability"},
        "schedule_meeting": {"function": schedule_meeting, "depends_on": "check_my_availability"},
    }

    job_title = "software engineer"
    job_desc = "bala bala"
    job_url = "https://www.metacareers.com/jobs/804955741151464/"

    MEETING_REQUEST_SUBJECT = "Meeting request: machine learning engineer"

    task_id = manager.submit_task(user_id, friend_email, MEETING_REQUEST_SUBJECT, job_title, job_desc, job_url, phrase_definitions)
    print(f"Submitted task with ID: {task_id}")

    # Simulate checking task status
    time.sleep(1)
    status = manager.get_task_status(task_id)
    print(f"Task {task_id} status: {status}")

    time.sleep(15)  # Let it finish

    status = manager.get_task_status(task_id)
    print(f"Task {task_id} status: {status}")