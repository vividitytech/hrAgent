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

import openpyxl
import pdfplumber
import pytesseract
from PIL import Image
from sqlalchemy import (Boolean, Column, create_engine, ForeignKey, Integer,
                        String, Enum)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

#Flask Library
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import threading
import time
import schedule
import functools
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Boolean, Column, create_engine, ForeignKey, Integer,
                        String, Enum)
from datetime import datetime, timedelta

Base = declarative_base()

# Customers Table
class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True, autoincrement=True) #Customer Id
    email = Column(String)
    password = Column(String)
    # Add name, address or other details

# Products Table
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))  # Customer relationship
    customer = relationship("Customer", backref="products")  #one to many

    name = Column(String)
    attachment_filepath = Column(String)
    vendor_email = Column(String)
    approved = Column(Boolean, default=False)
    last_update = Column(String) # Timestamp

# Jobs Table
class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id')) #Customer relationship
    customer = relationship("Customer", backref = "jobs_list") #Customer can access to the job list.
    job_type = Column(Enum("email_processing", "meeting_scheduling")) # Type of job
    status = Column(Enum("pending", "running", "completed", "failed", "cancelling", "cancelled"), default="pending")
    start_time = Column(String)
    end_time = Column(String)
    log_message = Column(String) #Store the status log
    email_processing_job_id = Column(String) #Store the email processing job id, each job can have multiple products.
    subject_line = Column(String) #Store the subject line for the email processing, each job can only have a subject

# Helper Functions
def get_db_session(db_filepath="products.db"): #Single DB for all
    """Returns a SQLAlchemy session for the given database filepath."""
    engine = create_engine(f'sqlite:///{db_filepath}')
    Session = sessionmaker(bind=engine)
    return Session()

# Email Retrieval (IMAP) - unchanged
def get_emails(email_address, password, subject_line):
    imap_server = "imap.gmail.com" # or your email provider's IMAP server
    imap = imaplib.IMAP4_SSL(imap_server)  # Using SSL for security

    try:
        imap.login(email_address, password)
        imap.select('INBOX')  # Select the inbox

        # Calculate the date 24 hours ago
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        date_string = yesterday.strftime("%d-%b-%Y") #Format: 01-Mar-2024

        #Create a search string.
        search_criteria = f'(SINCE "{date_string}" SUBJECT "{subject_line}")'

        # Search for unread emails with the specified subject in the last 24 hours
        status, messages = imap.search(None, search_criteria)
        if status == 'OK':
            message_ids = messages[0].split()
            for msg_id in message_ids:
                status, msg_data = imap.fetch(msg_id, '(RFC822)')  # Get full message data
                if status == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    yield msg
                    #Mark as read: imap.store(msg_id, '+FLAGS', r'\Seen')
                else:
                    print(f"Error fetching message {msg_id}: {status}")
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

# Text Extraction - unchanged
def extract_text_from_attachment(filepath): #The code will be the same
    """Extracts text from different file types."""
    try:
        if filepath.lower().endswith('.pdf'):
            with pdfplumber.open(filepath) as pdf:
                text = "\n".join([page.extract_text() for page in pdf.pages])
            return text
        elif filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img) # Requires Tesseract OCR installed
                return text
            except Exception as e:
                print(f"OCR Error: {e}")
                return ""

        elif filepath.lower().endswith(('.xlsx', '.xls')):
            try:
                workbook = openpyxl.load_workbook(filepath)
                text = ""
                for sheet in workbook:
                    for row in sheet.iter_rows():
                        text += " ".join(str(cell.value) for cell in row if cell.value is not None) + "\n"
                return text
            except Exception as e:
                print(f"Excel read error: {e}")
                return ""
        else:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:  # Try UTF-8 encoding
                    return f.read()
            except UnicodeDecodeError:
                 try:
                    with open(filepath, 'r', encoding='latin-1') as f: #Try latin-1 encoding
                        return f.read()
                 except Exception as e:
                    print(f"Text file read error: {e}")
                    return ""
    except Exception as e:
        print(f"File processing error: {e}")
        return ""

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
def send_email(sender_email, sender_password, recipient_email, subject, body): #The code will be the same
    """Sends an email."""
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

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
    for vendor_email in vendor_emails:
        send_email(sender_email, sender_password, vendor_email, subject, body)

def extract_vendor_emails(text): #The code will be the same
    """Extract emails from the email text"""
    # Basic email regex (improve as needed)
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_regex, text)
    return list(set(emails)) #Remove duplicates

def create_job(product_id, job_type, session, customer_id, email_processing_job_id=None, subject_line=None):
    """Creates a new job."""
    now = datetime.now().isoformat()
    new_job = Job(
        product_id=product_id,
        customer_id = customer_id, #Add the customer to the session
        job_type=job_type,
        status="running", # Set the status to running
        start_time=now,
        log_message=f"{job_type} started at {now}",  # Initial log message
        email_processing_job_id=email_processing_job_id, #Add the Job id, for filtering purpose
        subject_line = subject_line #Add the subject line.
    )
    session.add(new_job)
    session.commit()
    return new_job

def update_job_status(job_id, status, log_message, session):
    """Updates the status of a job."""
    job = session.query(Job).get(job_id)
    if job:
        now = datetime.now().isoformat()
        job.status = status
        job.end_time = now # Add the end time for the job
        job.log_message = log_message
        session.commit()
    else:
        print(f"Job with ID {job_id} not found")

#Add a global dictionary to check, since schedule will only run once and does not allow pass in parameter.

def email_processing_job(customer_id, customer_email, customer_password, product_keywords, subject_line, job_id):
    """
    Retrieves emails, extracts products, and updates the Products and Jobs tables.
    """
    session = get_db_session()

    try:
        # 1. Email Retrieval
        emails = get_emails(customer_email, customer_password, subject_line)
        if emails == None:
            raise Exception("Email login failed. ")

        date_str = datetime.now().strftime("%Y-%m-%d")

        # 2. Attachment Extraction and Text Processing
        attachment_filepaths = []
        product_vendor_data = []  # List to store product, filepath, vendor data

        # 3. Attachment Extraction and Text Processing
        for msg in emails:
            filepath = download_attachments(msg, customer_email.split('@')[0], date_str)
            if filepath:
                attachment_filepaths.append(filepath)  # store the filepaths
                text = extract_text_from_attachment(filepath)
                vendor_emails = extract_vendor_emails(text)  # Extract all vendor emails from the text

                # Identify Products
                identified_products = identify_top_products(text, product_keywords)
                # Store (Product Name, Filepath, Vendor Email)
                for product_name, _ in identified_products:
                    for vendor_email in vendor_emails:  # associate the product with the vendor

                        product_vendor_data.append((product_name, filepath, vendor_email))  # append a tuple of product, filepath and vendor email.

        # 4. Update/Create Products in Database
        for product_name, attachment_filepath, vendor_email in product_vendor_data:
            # Check if the product already exists for this customer
            product = session.query(Product).filter_by(customer_id=customer_id, name=product_name).first()
            now = datetime.now().isoformat()

            if product:
                # Update existing product
                product.attachment_filepath = attachment_filepath
                product.vendor_email = vendor_email
                product.last_update = now

            else:
                # Create a new product
                product = Product(
                    customer_id=customer_id,
                    name=product_name,
                    attachment_filepath=attachment_filepath,
                    vendor_email=vendor_email,
                    last_update = now
                )
                session.add(product)
            session.commit() #Need to flush out the session to have a product id.

            # Create Email Job (Email processing job)
            job = create_job(product.id, "email_processing", session, customer_id, email_processing_job_id = job_id, subject_line = subject_line)

            update_job_status(job.id, "completed", "Email process completed", session) #Add the job

            session.commit() #Commit all jobs.

    except Exception as e:
        print(f"Error in email processing: {e}")
        #Update status as failed
        session = get_db_session()

        try:
            product = session.query(Product).first() #Check for any product
            job = session.query(Job).filter_by(email_processing_job_id = job_id, customer_id = customer_id).first() #update the customer to that job

            update_job_status(job.id, "failed", f"Email process failed with error: {e}", session)  # add to the db
            session.commit()
        except Exception as e:
            print(f"Add the job error {e}. ")

    finally:
        session.close()

#Schedule the job using Flask.
def run_email_processing_job(customer_email, customer_password, product_keywords, subject_line, job_id):
    """Runs the email processing job."""
    #Wrap the method
    try:
        email_processing_job(customer_email, customer_password, product_keywords, subject_line, job_id)
        print(f"Email processing job {job_id} completed")
    except Exception as e:
        print(f"Email processing job {job_id} failed with error: {e}")


def scheduling_job(sender_email, sender_password):
    """
    Monitors the Products table for approved products and schedules meetings.
    """
    session = get_db_session()
    try:
        # 1. Find approved and not-yet-scheduled products (that have completed email processing)
        products_to_schedule = session.query(Product).filter(
            Product.approved == True
        ).all() #get all product that is approved.

        # 2. Schedule meetings for each product
        for product in products_to_schedule:
            # Check if there is a schedule job for it, if not create it.
            schedule_job_exist = session.query(Job).filter(Job.product_id == product.id, Job.job_type == "meeting_scheduling").first() #checking with the product id whether it exist or not
            if schedule_job_exist == None: #If the schedule job is not existed

                # Create Schedule Job (if one doesn't exist)
                job = create_job(product.id, "meeting_scheduling", session)

                try:
                    invite_vendors([product.vendor_email], "Your Scheduling Link")

                    update_job_status(job.id, "completed", "Meeting scheduled successfully", session)

                except Exception as e:
                    print(f"Error scheduling meeting for product {product.id}: {e}")
                    update_job_status(job.id, "failed", f"Meeting schedule failed with error: {e}", session)

        session.commit() #commit the jobs

    except Exception as e:
        print(f"Error in scheduling process: {e}")
    finally:
        session.close()

#Schedule with the main thread.
def schedule_jobs(): #Seperate thread so that Flask app will not hang.
    #Schedule the jobs
    while True:
        scheduling_job("your_email@gmail.com", "Your email password") #Run automatically

        time.sleep(60) #Run the check automatically in 60 seconds.

#For Login
app = Flask(__name__)
app.secret_key = "secret_key" #Need a key to create session

#For Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        session_db = get_db_session()
        customer = session_db.query(Customer).filter_by(email=email, password=password).first() #Check login

        if customer:
            session['customer_id'] = customer.id #Start the session
            session_db.close()
            return redirect(url_for('dashboard')) #After login go to dashboard

        else:
            session_db.close()
            return render_template('login.html', error='Invalid credentials') #If error, show in login page
    return render_template('login.html')

#To render the home page, create register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        session_db = get_db_session()
        #Check whether email exist or not
        existing_customer = session_db.query(Customer).filter_by(email=email).first()
        if existing_customer:
            session_db.close()
            return render_template('register.html', error = "Email exist, create another email. ") #Test the function
        else:

            new_customer = Customer(email=email, password=password) #Add the customer if not exist
            session_db.add(new_customer)
            session_db.commit()
            session_db.close()
            return redirect(url_for('login')) #Go to login
    return render_template('register.html') #Default to regiser

@app.route('/dashboard')
def dashboard():
    if 'customer_id' in session:
        customer_id = session['customer_id'] #get the customer id
        session_db = get_db_session()
        customer = session_db.query(Customer).filter_by(id = customer_id).first()
        jobs = session_db.query(Job).filter_by(customer_id = customer_id).all() #Get the job lists from customer, each customer only have one job
        email_job = session_db.query(Job).filter_by(customer_id = customer_id, job_type = "email_processing").first() #Get specific type of job
        session_db.close()

        return render_template('dashboard.html', customer=customer, jobs = jobs, email_job = email_job) #Render the dashboard.
    else:
        return redirect(url_for('login')) #If not exist, then return to login page.

#Clear all jobs, the thread run.
@app.route('/logout')
def logout():
    session.pop('customer_id', None)
    return redirect(url_for('login'))

#This one is to cancel and will need to implement.
@app.route('/cancel_job', methods=['POST'])
def cancel_email_job():
    if 'customer_id' in session:
        customer_id = session['customer_id']
        session_db = get_db_session()
        customer = session_db.query(Customer).filter_by(id = customer_id).first()

        job = session_db.query(Job).filter_by(customer_id = customer_id, status = "running", job_type = "email_processing").first() #Get the existing job
        if job:
            update_job_status(job.id, "cancelling", "The job has been called to cancel", session_db)
            session_db.commit() #Save it and run again
            session_db.close()
        return redirect(url_for('dashboard')) #Test the function
    else:
      return redirect(url_for('login')) #Back to the login page

@app.route('/start_job', methods=['POST'])
def start_email_job():
    #If is in the session
    if 'customer_id' in session:
        customer_id = session['customer_id']
        session_db = get_db_session()
        customer = session_db.query(Customer).filter_by(id = customer_id).first()

        customer_email = customer.email
        customer_password = customer.password #Don't use in prod, must be store locally and not pass to thread
        subject_line = request.form['subject_line']
        job = session_db.query(Job).filter_by(customer_id = customer_id, status = "running", job_type = "email_processing").first() #Get the existing job

        if job:
            session_db.close()
            return render_template('dashboard.html', error = "The email is running, please cancel it before starting a new job. ", customer = customer) #Test the function
        else:

            session_db.close()
            product_keywords = ["Product A", "Product B", "Product C", "Product D"]
            # Create a unique job ID
            job_id = str(datetime.now().timestamp())
            thread = threading.Thread(target=run_email_processing_job, args=(customer_id, customer_email, customer_password, product_keywords, subject_line, job_id,))
            thread.start()

            return redirect(url_for('dashboard')) #Test the function
    else:
      return redirect(url_for('login')) #Back to the login page

#To render to approve the product page
@app.route('/approve_product/<int:product_id>', methods=['POST'])
def approve_product(product_id):
    """Approves a product."""
    session = get_db_session()  # start session with database
    product = session.query(Product).get(product_id)

    if product:
        product.approved = True
        session.commit()
        session.close()

        return jsonify({'message': f'Product {product_id} approved.'})
    else:
        session.close()
        return jsonify({'error': 'Product not found.'}, 404)

#To render to view the attachment
@app.route('/view_attachment/<int:product_id>')
def view_attachment(product_id):
    """Serves the attachment for a product."""
    session = get_db_session()  # start session with database
    product = session.query(Product).get(product_id)
    session.close()

    if product:
        # Assuming the uploads folder is in the same directory as your app.py file
        filepath = os.path.join(app.root_path, product.attachment_filepath)

        # Dynamically determine content type based on file extension
        if filepath.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        elif filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
            content_type = 'image/jpeg'  # Or image/png
        else:
            content_type = 'application/octet-stream'  # Default to generic binary
        # Ensure file exists:
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
                return f"Error: Could not read file: {e}", 500  # Internal Server Error

        else:
            return "File not found.", 404  # Not Found

    else:
        return "Product not found", 404  # Not Found

#Schedule with the main thread.
def schedule_jobs(): #Seperate thread so that Flask app will not hang.
    #Schedule the jobs
    while True:
        scheduling_job("your_email@gmail.com", "Your email password") #Run automatically

        time.sleep(60) #Run the check automatically in 60 seconds.

def initialize_database():
    engine = create_engine('sqlite:///products.db')  # SQLite database file
    Base.metadata.create_all(engine)  # Create tables
    print("Database initialized")

if __name__ == '__main__':
    app = Flask(__name__)
    app.secret_key = "secret_key" #Need a key to create session

    initialize_database() #Initiliaze the database

    scheduling_thread = threading.Thread(target = schedule_jobs) #Start the job process.
    scheduling_thread.start()

    app.run(debug=True)