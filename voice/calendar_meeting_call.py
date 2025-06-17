import datetime
import time
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from twilio.rest import Client
from ai_server import TwilioAIAssistant

from ai_client_test import system_instruct

current_dir = os.path.abspath(__file__)  # Get absolute path of current file
parent_dir = os.path.dirname(current_dir) 
# --- Configuration ---
# Google Calendar API Credentials (Service Account)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']  # Read-only access
SERVICE_ACCOUNT_FILE = os.path.join( os.path.dirname(parent_dir), 'apptest-35403-c3944a05a142.json')  # Replace with the actual path

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')  # Get from environment variable for security
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')  # Get from environment variable for security
TWILIO_PHONE_NUMBER =  os.environ.get('TWILIO_PHONE_NUMBER')#'+1XXXXXXXXXX'  # Replace with your Twilio phone number

REMOTE_HOST=os.environ.get("NGROK_REMOTE_HOST", "cc3b-74-94-77-238.ngrok-free.app")

CALENDAR_ID = os.environ.get("CALENDAR_ID", "newhorizontalinc@gmail.com" )
# Recipient Phone Numbers
RECIPIENT_NUMBERS = ['+1425647****', '+1XXXXXXXXXX', '+1YYYYYYYYYY']  # List of phone numbers to call


import zoneinfo

def convert_datetime_to_timezone(datetime_str, target_timezone_str, output_format="%Y-%m-%d %H:%M:%S"):
    """
    Converts a datetime string with timezone information to a specified timezone.

    Args:
        datetime_str: The datetime string in ISO format (e.g., "2025-03-28 12:30:00-07:00").
        target_timezone_str: The IANA timezone name (e.g., "America/Los_Angeles", "UTC").

    Returns:
        A tuple containing:
            - A datetime object in the target timezone.
            - The time in the target timezone as a string (HH:MM:SS).
        Returns None, None if an error occurs.
    """
    try:
        # Parse the datetime string, handling the offset.
        dt_object = datetime.datetime.fromisoformat(datetime_str)

        # Get the target timezone.
        target_timezone = zoneinfo.ZoneInfo(target_timezone_str)

        # Convert to the target timezone.
        dt_in_target_tz = dt_object.astimezone(target_timezone)

        # Extract the time as a string.
        time_str = dt_in_target_tz.strftime(output_format) #("%H:%M:%S")  # Format as HH:MM:SS

        return dt_in_target_tz, time_str

    except ValueError as e:
        print(f"Error parsing datetime string or timezone: {e}")
        return None, None
    except zoneinfo.ZoneInfoNotFoundError as e:
        print(f"Error: Timezone not found: {e}")
        return None, None


# --- Helper Functions ---

def get_calendar_service():
    """Builds and returns the Google Calendar API service object."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None


def get_todays_events(service, calendar_id='primary'):
    """
    Retrieves today's events from the specified Google Calendar.

    Args:
        service: The Google Calendar API service object.
        calendar_id: The ID of the calendar to retrieve events from (default: 'primary').

    Returns:
        A list of events for today, or None if an error occurs.
    """
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    today_end = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + 'Z'

    try:
        events_result = service.events().list(calendarId=calendar_id, timeMin=now,
                                              timeMax=today_end, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        return events
    except Exception as e:
        print(f"Error retrieving events: {e}")
        return None


def make_phone_call(phone_number, sys_instruct, job_description):
    """
    Makes a phone call using Twilio.

    Args:
        phone_number: The phone number to call.
    """
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        call = client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml='<Response><Say>Hello! This is an automated call to remind you of your meeting.</Say></Response>' # Replace with your TwiML instructions
        )
        print(f"Call initiated to {phone_number}. SID: {call.sid}")
    except Exception as e:
        print(f"Error making call to {phone_number}: {e}")


def ai_phone_call(phone_number, system_instruct, job_description):
    tws.start_call(phone_number, system_message=system_instruct, job_description=job_description)



# start the twilio voice api
tws = TwilioAIAssistant(remote_host=REMOTE_HOST, port=8080)
tws.start()

# --- Main Loop ---
def main():

    """Main function to loop, check events, and make calls."""
    service = get_calendar_service()
    if not service:
        print("Failed to initialize Google Calendar service. Exiting.")
        return

    while True:
        
        events = get_todays_events(service, calendar_id = CALENDAR_ID)  # Ensure 'service' is passed
        
        if events:
            while events:

                event = events.pop(0)

                title = event['summary']
                description = event['description']
                start = event['start'].get('dateTime', event['start'].get('date'))
                #event_start_time = datetime.datetime.fromisoformat(start[:-1])  # Remove 'Z' and parse
                event_start_time = datetime.datetime.fromisoformat(start)
                time_zone = event['start'].get('timeZone')
                dt_in_target_tz, dt_in_tg_str = convert_datetime_to_timezone(start, time_zone)
                dt_in_target_tz.isoformat()
                
                now = datetime.datetime.now(zoneinfo.ZoneInfo(time_zone))

                if now.date() == event_start_time.date():  # Only process events for today
                    time_difference = event_start_time - now
                    seconds_until_event = time_difference.total_seconds()

                    if seconds_until_event>60:
                        time.sleep(seconds_until_event-60)

                        #if 0 <= seconds_until_event <= 60:  # Call within the next minute
                        print(f"Meeting: {event['summary']} starting now.")

                        for recipient_number in RECIPIENT_NUMBERS:
                            ai_phone_call(recipient_number,system_instruct, description)

        else:
            print("No upcoming events found for today.")

        # Wait before checking again (e.g., every minute)
        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    main()