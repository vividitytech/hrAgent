import datetime
import json
import os
import re
import shutil
import smtplib
from collections import Counter
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import imaplib
import email


from content_extractor import extract_text_from_attachment
from email_schedule import get_availability_from_email, check_email_for_availability, check_my_availability, schedule_meeting
from email_schedule import WorkflowManager

from sqlalchemy import (Boolean, Column, create_engine, inspect, ForeignKey, Integer,Float, String, Enum)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from resume_match import assess_cv_match


Base = declarative_base()

# Products Table
# product_id, product_name, score, attachment_filepath, vendor_name, vendor_email
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String) # Track customer
    product_name = Column(String) # product name
    #product_producer = Column(String) # product company
    product_id = Column(String) # product id
    product_desc = Column(String) # product description
    product_url = Column(String) # product url
    match_score = Column(Float) # score
    attachment_filepath = Column(String)
    vendor_name = Column(String)
    vendor_email = Column(String)
    vendor_phone = Column(String)
    vendor_status = Column(Enum("pending", "accepted", "rejected", "failed"), default="pending")
    approved = Column(Boolean, default=False)
    scheduling_status = Column(Enum("pending", "running", "completed", "failed"), default="pending")
    last_update = Column(String) # Timestamp


class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String) # product name
    customer_email = Column(String) # product description
    customer_password = Column(String) # product description


class Vendors(Base):
    __tablename__ = 'vendors'
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_name = Column(String) # product name
    vendor_email = Column(String) # product description
    vendor_phone = Column(String) # product description

# Jobs Table
class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String) # Track customer
    product_id = Column(Integer, ForeignKey('products.id')) # Link to product
    vendor_email = Column(String)
    job_type = Column(Enum("email_processing", "meeting_scheduling")) # Type of job
    status = Column(Enum("pending", "running", "completed", "failed"), default="pending")
    start_time = Column(String)
    end_time = Column(String)
    log_message = Column(String) #Store the status log

# Helper Functions
def get_db_session(db_filepath="products.db"): #Single DB for all
    """Returns a SQLAlchemy session for the given database filepath."""
    engine = create_engine(f'sqlite:///{db_filepath}')
    Session = sessionmaker(bind=engine)
    return Session()

# Email Retrieval (IMAP) - unchanged
def get_emails(email_address, password, subject_line, unread_only=True):
    imap_server = "imap.gmail.com" # or your email provider's IMAP server
    imap = imaplib.IMAP4_SSL(imap_server)  # Using SSL for security

    try:
        imap.login(email_address, password)
        imap.select('INBOX')  # Select the inbox

        # Calculate the date 24 hours ago
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=12) # default run daily(days=1)
        date_string = yesterday.strftime("%d-%b-%Y") #Format: 01-Mar-2024

        #Create a search string.
        search_criteria = f'(SINCE "{date_string}" SUBJECT "{subject_line}")'

        if unread_only:
            search_criteria += ' UNSEEN'

        # Search for unread emails with the specified subject in the last 24 hours
        status, messages = imap.search(None, search_criteria)
        if status == 'OK':
            message_ids = messages[0].split()
            for msg_id in message_ids:
                try:
                    status, msg_data = imap.fetch(msg_id, '(RFC822)')  # Get full message data
                    if status == 'OK':
                        msg = email.message_from_bytes(msg_data[0][1])
                        yield msg
                        #Mark as read: imap.store(msg_id, '+FLAGS', r'\Seen')
                    else:
                        print(f"Error fetching message {msg_id}: {status}")
                
                except Exception as e:
                    imap.store(msg_id, "-FLAGS", "\\Seen")  #  Adds the UNSEEN flag (marks as unread)
                    print(f"Marked email {msg_id.decode()} as UNREAD due to error.")
        else:
            print(f"Error searching for unread emails: {status}")

    except imaplib.IMAP4.error as e:
        print(f"IMAP login failed: {e}")
    finally:
        try:
            imap.close()
        except:
            pass
        imap.logout()

# Attachment Extraction - unchanged
def download_attachments(msg, customer_id, date_str): #The code will be the same
    """Downloads attachments from an email message."""
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue  # Skip multipart containers
        if part.get('Content-Disposition') is None:
            continue  # Skip non-attachment parts

        filename = part.get_filename()
        if filename:
            #Decode the filename
            filename = decode_header(filename)[0][0]
            if isinstance(filename, bytes):
              filename = filename.decode()

            filepath = os.path.join("temp_attachments", customer_id, date_str, filename) # Ensure the directory exists

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))

            print(f"Downloaded attachment: {filename} to {filepath}")

            return filepath

# Product Identification - unchanged
def identify_top_products(text, product_keywords, num_products=20): #The code will be the same
    """
    Identifies the top products mentioned in the text.
    """

    # Simple keyword-based counting (replace with your actual algorithm)
    product_counts = Counter()
    for keyword in product_keywords:
        count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text.lower()))  # Word boundary matching
        product_counts[keyword] = count

    top_products = product_counts.most_common(num_products)
    return top_products

# Emailing - unchanged
def send_email(sender_email, sender_password, recipient_email, recipient_name, subject, body): #The code will be the same
    """Sends an email."""
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"{subject}"

    body = f"Hi {recipient_name}\n\n" + body
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:  # Or your SMTP server
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Email sending failed: {e}")

def invite_vendors(vendor_emails, meeting_link): #The code will be the same
    """Invites selected vendors to a meeting."""
    subject = "Meeting Invitation"
    body = f"We would like to schedule a meeting with you. Please use the following link to schedule a time that works for you: {meeting_link}"
    for vendor_email, vendor_name in vendor_emails:
        send_email(sender_email, sender_password, vendor_email, vendor_name, subject, body)

def extract_vendor_emails(text): #The code will be the same
    """Extract emails from the email text"""
    # Basic email regex (improve as needed)
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_regex, text)
    return list(set(emails)) #Remove duplicates

def extract_vendor_name(text):
    # --- Name Extraction ---
    #name_match = re.search(r"([a-z]+(?: [a-z]+)+)", text)  # Basic name regex (two or more lowercase words)
    #return name_match.group(1).strip() if name_match else None
    name_pattern = r"(?:Dr\.|Mr\.|Ms\.|Mrs\.)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?=\n|$)" # ?= is a lookahead assertion
    names = re.findall(name_pattern, text)
    return names[0].strip() if len(names)>0 else None

def extract_phone_number(text):
    """
    Extracts phone numbers from a given text using regular expressions.

    Args:
        text: The text to extract phone numbers from.

    Returns:
        A list of phone numbers found in the text.  Returns an empty list if no phone numbers are found.
    """

    # Regular expression to match phone numbers
    # This is a simplified regex, you might need to adjust it based on the typical format of phone numbers in your resumes.
    phone_regex = re.compile(r'''
        (\+\d{1,2}\s)?    # Optional country code (e.g., +1 or +44) and a space
        (\d{3}|\(\d{3}\))?  # Area code (either 3 digits or enclosed in parentheses)
        (\s|-|\.)?          # Separator (space, hyphen, or period)
        (\d{3})            # First 3 digits
        (\s|-|\.)?          # Separator (space, hyphen, or period)
        (\d{4})            # Last 4 digits
    ''', re.VERBOSE)

    phone_numbers = phone_regex.findall(text)

    # Combine the parts of the phone number into a single string
    formatted_numbers = []
    for number_tuple in phone_numbers:
        # Example Number Tuple: ('+1 ', '212', ' ', '555', '-', '1212')
        # We want to stitch them together to something like +1 212 555-1212 or 212 555-1212

        # Join the relevant parts, stripping any whitespace
        formatted_number = "".join(part.strip() for part in number_tuple if part.strip())
        formatted_numbers.append(formatted_number)


    #Filter out false positives like dates (1999-2000) that might match the regex
    filtered_numbers = []
    for number in formatted_numbers:
        if len(number) >= 7: #Reasonable minimum length for a phone number
            filtered_numbers.append(number)

    #return filtered_numbers
    return filtered_numbers[0].strip() if len(filtered_numbers)>0 else None

def create_job(product_id, job_type, session):
    """Creates a new job."""
    now = datetime.datetime.now().isoformat()
    new_job = Job(
        product_id=product_id,
        job_type=job_type,
        status="running", # Set the status to running
        start_time=now,
        log_message=f"{job_type} started at {now}"  # Initial log message
    )
    session.add(new_job)
    session.commit()
    return new_job

def update_job_status(job_id, status, log_message, session):
    """Updates the status of a job."""
    job = session.query(Job).get(job_id)
    if job:
        now = datetime.datetime.now().isoformat()
        job.status = status
        job.end_time = now # Add the end time for the job
        job.log_message = log_message
        session.commit()
    else:
        print(f"Job with ID {job_id} not found")


def find_top_percent_and_threshold(data, percentage=0.20, min_items=10, index = 2):
    """
    Finds the top X percent of items with the highest scores from a list of triples (id, score, description)
    and returns both the top items and the threshold score value.  If the number of items in the top X
    percent is less than min_items, it returns up to min_items items.

    Args:
        data (list): A list of triples (id, score, description).
        percentage (float): The percentage of items to return (default: 0.20 = 20%).  Must be between 0 and 1.
        min_items (int): The minimum number of items to return (default: 10).

    Returns:
        tuple: A tuple containing:
            - list: A list containing the top items (up to min_items).
            - float: The threshold score value. Returns None if input is invalid.
        None: If the percentage is invalid.
        (None, None): If the data is empty
    """

    if not 0 < percentage < 1:
        print("Error: Percentage must be between 0 and 1.")
        return None

    if not data:
        return (None, None)  # Handle empty list case

    # Sort the data by score in descending order
    sorted_data = sorted(data, key=lambda x: x[index], reverse=True)

    # Calculate the number of items to include in the top X percent
    num_items = int(len(sorted_data) * percentage)

    # Ensure we return at least min_items, but not more than the total number of items
    num_items = max(num_items, min_items)  # Get the larger between num_items and min_items
    num_items = min(num_items, len(sorted_data)) # Get the smaller between num_items and the total

    # Get the threshold score
    if num_items > 0:
        threshold = sorted_data[num_items - 1][3]
    else:
        threshold = float('inf')

    # Return the top items and the threshold
    return sorted_data[:num_items], threshold

def email_processing_job(customer_id, customer_email, customer_password, products):
    """
    Retrieves emails, extracts products, and updates the Products and Jobs tables.
    """
    session = get_db_session()
    try:
        while True: #infinite running loop, can be improve with break if need to stop.
            # 1. Find approved and not-yet-scheduled products

            # Identify Products
            for product in products:
                subject_line = product['product_name'] # email title to search 
                # 1. Email Retrieval
                emails = get_emails(customer_email, customer_password, subject_line)

                customer_name = customer_email.split('@')[0]
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")

                # 2. Attachment Extraction and Text Processing
                attachment_filepaths = []
                product_vendor_data = []  # List to store product, filepath, vendor data

                # 3. Attachment Extraction and Text Processing
                for msg in emails:
                    filepath = download_attachments(msg, customer_name, date_str)
                    if filepath:
                        attachment_filepaths.append(filepath)  # store the filepaths
                        text = extract_text_from_attachment(filepath)
                        vendor_emails = extract_vendor_emails(text)  # Extract all vendor emails from the text
                        vendor_name = extract_vendor_name(text)
                        vendor_phone = extract_phone_number(text)

                        
                        score = assess_cv_match(text, product['product_desc'])
                        # identified_products = identify_top_products(text, product['prod_desc'])
                        # Store (Product Name, Filepath, Vendor Email)
                        product_name = product['product_name']
                        product_id = product['product_id']
                        for vendor_email in vendor_emails:  # associate the product with the vendor

                            product_vendor_data.append((product_id, product_name, product['product_desc'], score, filepath, vendor_name, vendor_email, vendor_phone))  # append a tuple of product, filepath and vendor email.

                # select the top 20%, or top 10 resumes
                _, threshold = find_top_percent_and_threshold(product_vendor_data, percentage=0.20, min_items=10, index = 2)
                # 4. Update/Create Products in Database > threshold
                for product_id, product_name, product_desc, score, attachment_filepath, vendor_name, vendor_email, vendor_phone  in product_vendor_data:

                    try:
                        if score <threshold: # reject applicants who are not matched well to the job

                            product = Product(
                                customer_id=customer_id,
                                product_id = product_id,
                                product_name=product_name,
                                product_desc = product_desc,
                                match_score = score,
                                attachment_filepath=attachment_filepath,
                                vendor_email=vendor_email,
                                vendor_name = vendor_name,
                                vendor_phone= vendor_phone,
                                vendor_status = "rejected",
                                last_update = now
                            )
                            
                            session.add(product)
                            session.commit() #Need to flush out the session to have a product id.

                            # send reject email
                            body = """sorry to inform you that we cannot move forward, and best wishes to you.
                            """
                            subject_line  = f"Update with your application for {product_name}"
                            send_email(customer_email, customer_password, vendor_email, vendor_name, subject_line, body)
                            continue
                        # Check if the product already exists for this customer
                        product = session.query(Product).filter_by(customer_id=customer_id, product_id=product_id, vendor_email=vendor_email).first()
                        now = datetime.datetime.now().isoformat()

                        if product:
                            # Update existing product
                            product.attachment_filepath = attachment_filepath
                            product.vendor_email = vendor_email
                            product.match_score = score
                            # product.vendor_status = "pending" # no more processing for the previous application
                            product.last_update = now
                            '''
                            # Create Email Job (Email processing job)
                            job = create_job(product.id, "email_processing", session)

                            update_job_status(job.id, "completed", "Email process completed", session) #add to the db
                            '''
                        else:
                            # Create a new product
                            product = Product(
                                customer_id=customer_id,
                                product_id = product_id,
                                product_name=product_name,
                                product_desc=product_desc,
                                match_score = score,
                                attachment_filepath=attachment_filepath,
                                vendor_email=vendor_email,
                                vendor_name = vendor_name,
                                vendor_phone= vendor_phone,
                                last_update = now
                            )
                            session.add(product)
                            session.commit() #Need to flush out the session to have a product id.
                            '''
                            # Create Email Job (Email processing job)
                            job = create_job(product.id, "email_processing", session)

                            update_job_status(job.id, "completed", "Email process completed", session)  # add to the db
                            '''
                        session.commit() #Commit all jobs.

                    except Exception as e:
                        print(f"Error in email processing: {e}")
                        #Update status as failed
                        job = create_job(product['product_id'], "email_processing", session)
                        update_job_status(job.id, "failed", f"Email process failed with error: {e}", session)  # add to the db

                    finally:
                        print("addition processsing?")
            
            
            time.sleep(5*60)  # Check every 5*60 seconds
    
    except Exception as e:
        print(f"Error in email processing: {e}")
        #Update status as failed
        job = create_job(customer_id, "customer's email_processing", session)
        update_job_status(job.id, "failed", f"Email process failed with error: {e}", session)  # add to the db

    finally:
        session.close()

def clean_up_files(): #Clean up files
    folder = 'temp_attachments'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def scheduling_job(engine, manager):
    """
    Monitors the Products table for approved products and schedules meetings.
    """
    session = get_db_session()
    try:
        while True: #infinite running loop, can be improve with break if need to stop.
            # 1. Find approved and not-yet-scheduled products

            if not table_exists(engine, "products"):
                continue

            products_to_schedule = session.query(Product).filter(
                Product.approved == False, # True,
                Product.vendor_status == "pending"
            ).all()

            # 2. Schedule meetings for each product
            for product in products_to_schedule:
                try:
                    product.vendor_status = "accepted"
                    session.commit()

                    #invite_vendors([product.vendor_email], "Your Scheduling Link")

                        # Define the workflow tasks as a dictionary
                    phrase_definitions = {
                        "get_friend_availability": {"function": get_availability_from_email},
                        "check_my_availability": {"function": check_my_availability, "depends_on": "get_friend_availability"},
                        "schedule_meeting": {"function": schedule_meeting, "depends_on": "check_my_availability"},
                    }
                    email_title = "Meeting request: " + product.product_name
                    task_id = manager.submit_task(product.customer_id, product.vendor_email, email_title, product.product_name, product.product_desc, product.product_url, phrase_definitions)
                    print(f"Submitted task with ID: {task_id}")

                    # Simulate checking task status
                    time.sleep(1)
                    status = manager.get_task_status(task_id)
                    
                    #product.scheduling_status = "completed"
                except Exception as e:
                    print(f"Error scheduling meeting for product {product.id}: {e}")
                    product.vendor_status = "failed"
                finally:
                    product.last_update = datetime.datetime.now().isoformat()
                    session.commit()

            # 3. Wait for a while before checking again (adjust as needed)
            time.sleep(60)  # Check every 60 seconds

    except KeyboardInterrupt:
        print("Scheduling job stopped.")
    finally:
        session.close()




#Flask App, the code is not complete, but only gives a basic overview
from flask import Flask, render_template, request, jsonify
import threading
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Directory to store uploaded files

customer_email = os.getenv('EMAIL_ADDRESS', 'users')  # Table name from env
customer_password = os.getenv('EMAIL_PASSWORD', 'password')  # Table name from env


@app.route('/')
def index():
    """Serves the main page with the product list."""
    # customer_email = config.EMAIL_ADDRESS # "your_customer_email@gmail.com" #get the customer_email
    session = get_db_session() #start session with customer db

    products = session.query(Product).filter_by(customer_id = customer_email)#.split('@')[0]).all() #Get product for customer

    session.close()
    return render_template('index1.html', products=products) # Create an index.html template

@app.route('/approve_product/<int:product_id>', methods=['POST'])
def approve_product(product_id):
    """Approves a product."""
    session = get_db_session() #start session with customer db
    product = session.query(Product).get(product_id)

    if product:
        product.approved = True
        session.commit()
        session.close()

        return jsonify({'message': f'Product {product_id} approved.'})
    else:
        session.close()
        return jsonify({'error': 'Product not found.'}, 404)

@app.route('/view_attachment/<int:product_id>')
def view_attachment(product_id):
    """Serves the attachment for a product."""
    session = get_db_session() #start session with customer db
    product = session.query(Product).get(product_id)
    session.close()

    if product:
        #Assuming the uploads folder is in the same directory as your app.py file
        filepath = os.path.join(app.root_path, product.attachment_filepath)

        # Dynamically determine content type based on file extension
        if filepath.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        elif filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
            content_type = 'image/jpeg'  # Or image/png
        else:
            content_type = 'application/octet-stream' # Default to generic binary
        #Ensure file exists:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    file_content = f.read()
                response = Flask.response_class(
                    response=file_content,
                    status=200,
                    mimetype=content_type
                )
                return response
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")
                return f"Error: Could not read file: {e}", 500 # Internal Server Error

        else:
          return "File not found.", 404 # Not Found

    else:
        return "Product not found", 404 # Not Found

def initialize_database(): #Run once to start
    engine = create_engine('sqlite:///products.db')  # SQLite database file
    Base.metadata.create_all(engine)  # Create tables
    print("Database initialized")
    return engine

def table_exists(engine, table_name):
    """
    Checks if a table exists in the database.

    Args:
        engine: SQLAlchemy engine object.
        table_name: Name of the table to check.

    Returns:
        True if the table exists, False otherwise.
    """
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


if __name__ == '__main__':
    engine = initialize_database()
    #Example running a workflow
    customer_email = os.getenv('EMAIL_ADDRESS', 'users')  # Table name from env
    customer_password = os.getenv('EMAIL_PASSWORD', 'password')  # Table name from env

    product_keywords = ["Product A", "Product B", "Product C", "Product D"]
    sender_email = "your_email@gmail.com"  # Your email address for sending notifications
    sender_password = "your_email_password"

    subject_line = "machine learning engineer" #"Vendor Product Update" #The new subject email

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
    products = [{"product_id":"prod_id", "product_name":subject_line, "product_desc":job_description, "product_url": None}]
    #email_processing_job(customer_email, customer_password, product_keywords, subject_line) #Pass in the customer email and password
    #scheduling_job(sender_email, sender_password) #Also do the scheduling daily

    
    #Thread 1 to run the email process.
    email_thread = threading.Thread(target=email_processing_job, args=(customer_email, customer_email, customer_password, products))

    #Thread 2 to run the scheduling job, infinite loop with checking for the scheduling
    manager = WorkflowManager(db_path="workflow.db")
    scheduling_thread = threading.Thread(target=scheduling_job, args=(engine, manager))

    #Start the threads
    email_thread.start()
    scheduling_thread.start()
    
    app.run(debug=True)