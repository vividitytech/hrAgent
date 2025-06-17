## Resume screening and Meeting scheduling

resume screening: match the resume with job description, rank and return the top candidates
meeting scheduling: automatically send out email request to canddidates and setup the event on Google calendar 


## Pre-requisites
we use gmail and google calendar APIs to process incoming emails and schedule meetings. 

### Set google cloud config .json and Google Calendar
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



After you setup google cloud and calendar, add SCOPES and CALENDAR_ID to your .env


### Enable the Gmail API

Enable the Gmail API: Within your project, enable the Gmail API

refer to [Create & use app passwords](https://support.google.com/accounts/answer/185833?hl=en#zippy=%2Cwhy-you-may-need-an-app-password)


Important: To create an app password, you need 2-Step Verification on your Google Account.

If you use 2-Step-Verification and get a "password incorrect" error when you sign in, you can try to use an app password.

Create and manage your app passwords. You may need to sign in to your Google Account.

If you’ve set up 2-Step Verification but can’t find the option to add an app password, it might be because:

    Your Google Account has 2-Step Verification set up only for security keys.
    You’re logged into a work, school, or another organization account.
    Your Google Account has Advanced Protection.


After you create the app password, please add your EMAIL_ADDRESS and EMAIL_PASSWORD to .env

## Test each piple line

### scheduling with email
debug wtih vscode `python email_schedule.py`

### resume matching
debug wtih vscode `python resume_match.py`


## Run the whole processor

Run `python resume_processor.py`

