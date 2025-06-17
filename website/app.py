import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))


from flask import Flask,render_template, request,flash,redirect, url_for, session, jsonify
import bcrypt
import mysql.connector
import os,random,codecs
from datetime import datetime,timedelta
from dotenv import load_dotenv
import secrets  # For generating secure random values
#from users import User,User_info
from static.forms.contact import is_valid,leaveMessage

from fileinput import filename

from processor.email_schedule import schedule_via_email, WorkflowManager

'''
def check_password(user,given,remember,source):
    if bcrypt.check_password_hash(user['password'],given):
        user_object = User_info(user)
        login_user(user_object,remember=remember)
        flash({'title': "Success", 'message': "Login Successfull"}, 'success')
        return redirect('/User-Profile')
    else:
        flash({'title': "Error", 'message': "Invalid Password !"}, 'error')
        return render_template('auth/login.html',value=user[f'{source}'])

'''
load_dotenv()
USER_TABLE = os.getenv('USER_TABLE', 'users')  # Table name from env
# Function to get the user table name
def get_user_table():
    return os.getenv('USER_TABLE', 'users')

# Database configuration from .env
db_config = {
    'user': os.getenv('DB_USER', 'your_db_user'),
    'password': os.getenv('DB_PASSWORD', 'your_db_password'),
    'host': os.getenv('DB_HOST', 'your_db_host'),
    'database': os.getenv('DB_NAME', 'your_db_name')
}

def get_db_connection():
    """Establishes and returns a MySQL database connection."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None


def create_tables():
    """Creates/Updates the user table. Adds missing columns."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        user_table_name = os.getenv('USER_TABLE', 'users')

        try:
            # Check if the table exists
            cursor.execute(f"SHOW TABLES LIKE '{user_table_name}'")
            table_exists = cursor.fetchone()

            if not table_exists:
                # Create the table if it doesn't exist (initial creation)
                cursor.execute(f"""
                    CREATE TABLE `{user_table_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        password VARCHAR(255) NOT NULL,
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        last_login DATETIME
                    )
                """)
                conn.commit()
                print(f"Table '{user_table_name}' created successfully.")
            else:
                # Table exists, so add missing columns

                # Function to add a column if it doesn't exist
                def add_column_if_not_exists(column_name, column_type):
                    try:
                        # Check if column exists
                        cursor.execute(f"ALTER TABLE `{user_table_name}` ADD COLUMN `{column_name}` {column_type}")
                        conn.commit()
                        print(f"Column '{column_name}' added to table '{user_table_name}'.")
                    except mysql.connector.Error as err:
                        # Column already exists, or other error
                        if err.errno == 1060:  # Duplicate column name
                            print(f"Column '{column_name}' already exists in table '{user_table_name}'.")
                        else:
                            print(f"Error adding column '{column_name}': {err}")


                # Add missing columns
                add_column_if_not_exists("first_name", "VARCHAR(255)")
                add_column_if_not_exists("last_name", "VARCHAR(255)")
                add_column_if_not_exists("last_login", "DATETIME")

        except mysql.connector.Error as err:
            print(f"Error creating/updating tables: {err}")
        finally:
            cursor.close()
            conn.close()

def password_hash(password):
    password_bytes = password.encode('utf-8') # Passwords should be bytes
    # Generate a salt (recommended 12 rounds or higher)
    salt = bcrypt.gensalt(rounds=12)
    # Hash the password using the salt
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password

#Verification
def check_password(password, hashed_password):
    password_bytes = password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(24)

#app.jinja_env.globals.update(send_otp=send_otp)

manager = WorkflowManager(db_path="workflow.db")


@app.before_request
def session_handler():
    session.permanent = True
    # App.permanent_session_lifetime = timedelta(minutes=1)


@app.route("/")
def home():
    return render_template("main/index.html")


@app.route("/Login",methods=["GET","POST"])
def login():
    if 'email' in session:
        return redirect('/User-Profile') #return redirect(url_for('index'))  # Redirect to home page if logged in
    else:
        if request.method=="GET":
            return render_template("auth/login.html",value=None)
        elif request.method=="POST":
            username = request.form['username']
            password = request.form['password']
            try:
                remember = request.form['remember']
            except:
                remember = False

            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    user_table_name = get_user_table()
                    # Retrieve user from database
                    cursor.execute(f"SELECT id, email, password, first_name FROM `{user_table_name}` WHERE email = %s", (username,))
                    user = cursor.fetchone()

                    if user:
                        user_id, db_email, db_password, first_name = user
                        # Verify password using bcrypt
                        if bcrypt.checkpw(password.encode('utf-8'), db_password.encode('utf-8')):
                            # Passwords match

                            # Update last login time
                            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cursor.execute(f"UPDATE `{user_table_name}` SET last_login = %s WHERE id = %s", (now, user_id))
                            conn.commit()

                            # Store user information in session
                            session['email'] = db_email
                            session['first_name'] = first_name
                            flash('login successfully!', 'success')
                            return redirect(url_for('home'))  # Redirect to home page
                        else:
                            flash('login failed, please check your password, and retry.', 'error')
                            return render_template('auth/login.html', error='Incorrect password.')
                    else:
                        flash('login failed, please check your username and retry.', 'error')
                        return render_template('auth/login.html', error='Invalid email.')
                except mysql.connector.Error as err:
                    print(f"Error during login: {err}")
                    return render_template('login.html', error='Login failed. Please try again.')
                finally:
                    cursor.close()
                    conn.close()
                flash({'title': "Error", 'message': "Invalid Username or Email !",'options':{'TOASTR_POSITION_CLASS':'toast-top-center'}}, 'error')
                return render_template('auth/login.html',value=username)
            
            else:
                return render_template('login.html', error='Database connection error.')
        else: return None

@app.route("/Register",methods=["GET","POST"])
def register():
    if 'email' in session:
        return redirect('/User-Profile') #return redirect(url_for('index'))  # Redirect to home page if logged in
    else:
        if request.method=="GET":
            return render_template("auth/register.html",value=None,otp_req=False)
        elif request.method=="POST":
            global otp_list,user_name,user_email,user_username,user_password
            
            user_email = request.form['email']
            #user_name = request.form['name']
            #user_username = request.form['username']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            hashed_password = password_hash(request.form['password']).decode('utf-8')
            if not user_email or not hashed_password or not first_name or not last_name:
                return render_template('auth/register.html', error='All fields are required.')

            # Validate email format (basic check)
            if "@" not in user_email or "." not in user_email:
                return render_template('auth/register.html', error='Invalid email format.')

            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    user_table_name = get_user_table()
                    # Check if the email already exists
                    cursor.execute(f"SELECT id FROM `{user_table_name}` WHERE email = %s", (user_email,))
                    existing_user = cursor.fetchone()
                    username = first_name+" "+last_name
                    
                    if existing_user:
                        flash({'title': "Warning", 'message': "Username Already Exists !",}, 'warning')
                        return render_template('auth/register.html', value={'message' : 'Email already exists.' , 'email' : f'{user_email}' , 'username' : f'{username}'},otp_req=False)

                    
                    # Insert the new user into the database
                    cursor.execute(f"INSERT INTO `{user_table_name}` (email, password, username, first_name, last_name) VALUES (%s, %s, %s, %s, %s)",
                                (user_email, hashed_password, username, first_name, last_name))
                    conn.commit()
                    flash({'title': "Success", 'message': "Registered Successfully!"}, 'success')
                    return redirect(url_for('login'))  # redirect to login page after registration

                except mysql.connector.Error as err:
                    print(f"Error during registration: {err}")
                    return render_template('auth/register.html', error='Registration failed. Please try again.')  # More user-friendly message
                finally:
                    cursor.close()
                    conn.close()
            else:
                return render_template('auth/register.html', error='Database connection error.')
            '''
            if auth_db.find_one(filter={'email' : f'{user_email}'}) == None:
                if auth_db.find_one(filter={'username' : f'{user_username}'}) == None:
                    x = round(random.random()*1000000)
                    otp_list=[]
                    otp_list.append(x)
                    send_email(name=user_name,email=user_email,other=True,count=1,otp=otp_list[0])
                    return render_template('auth/register.html',value={'name' : f'{user_name}' , 'email' : f'{user_email}' , 'username' : f'{user_username}'},otp_req=True)
                else:
                    flash({'title': "Warning", 'message': "Username Already Exists !",}, 'warning')
                    return render_template('auth/register.html',value={'name' : f'{user_name}' , 'email' : f'{user_email}' , 'username' : f'{user_username}'},otp_req=False)
            else:
                flash({'title': "Warning", 'message': "Email Already Exists !"}, 'warning')
                return render_template('auth/register.html',value={'name' : f'{user_name}' , 'email' : f'{user_email}' , 'username' : f'{user_username}'},otp_req=False)
            '''
        else: return None

'''
@App.route("/OTP-Validation",methods=["GET","POST"])
def send_otp():
    if current_user.is_authenticated:
            return redirect("/")
    else:
        if request.method=="POST":
            global otp_list,user_name,user_email,user_username,user_password
            print(int(request.form['otp']),otp_list)
            if int(request.form['otp']) == otp_list[0]:
                auth_db.insert_one({'name' : f'{user_name}' , 'email' : f'{user_email}' , 'username' : f'{user_username}' , 'password' : f'{user_password}'})
                flash({'title': "Success", 'message': "Registered Successfully!"}, 'success')
                return render_template('auth/login.html',value=user_username)
            else:
                flash({'title': "Warning", 'message': "Please Provide Correct OTP !<br>Register Again Please !"}, 'warning')
                return redirect("/Register")
        else:
            flash({'title': "Info", 'message': "Please Register first !"}, 'info')
            return redirect("/Register")
'''    

@app.route("/DA-1")
@app.route("/DA-2")
@app.route("/DA-3")
@app.route("/ML-1")
@app.route("/ML-2")
@app.route("/ML-3")
@app.route("/DL-1")
@app.route("/DL-2")
@app.route("/DL-3")
def project_dis():
    re = str(request.url_rule)
    if re in ["/DA-1","/DA-2","/DA-3"]:
        return render_template("portfolio/portfolio-DA.html",value = re)
    elif re in ["/ML-1","/ML-2","/ML-3"]:
        return render_template("portfolio/portfolio-ML.html",value = re)
    elif re in ["/DL-1","/DL-2","/DL-3"]:
        return render_template("portfolio/portfolio-DL.html",value = re)
    else:
        return None

'''
@app.route("/Contact",methods=["GET","POST"])
def contact():
    if request.method=="POST":
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        if contact_db.find_one(filter={'email' : f'{email}'}) == None:  
            if is_valid(email):
                contact_db.insert_one( {'date_time' : f'{datetime.now()}' , 'name' : f'{name}' , 'email' : f'{email}' , 'subject' : f'{subject}' , 'message' : f'{message}' } )
                send_email(name,email,subject,message)
                flash({'title': "Success", 'message': "Message Sent Successfully !"}, 'success')
            else:                
                flash({'title': "Error", 'message': "Please Provide A Working Email !"}, 'error')
            return redirect('/')
        else:
            flash({'title': "Information", 'message': "Message Already Sent Please Wait For Support !"}, 'info')
            return redirect('/')
    else:
        return False
'''
@app.route("/User-Profile")
def profile():
    return render_template("profile/user-profile.html", current_user=session)


@app.route("/Contact", methods=["GET","POST"])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        title = request.form['title']
        email = request.form['email']
        message = request.form['message']
        print(f"Name: {name}, Title: {title}, Email: {email}, Message: {message}")  #For testing, remove in production
        # send_email(name,email,title,message)
        leaveMessage(name, email, title, message)
        flash({'title': "Success", 'message': "Message Sent Successfully !"}, 'success')
        return redirect('/')
    else:
        return render_template("main/contact2.html", current_user=session)


@app.route("/User-Profile/Edit-Profile",methods=["GET","POST"])
def edit_profile():
    if request.method=="GET":
        return redirect("/User-Profile")
    elif request.method=="POST":
        id = ObjectId(session['_user_id'])
        
        image,name,about,company,job,country,address,phone,twitter,facebook,instagram,linkedin,github = \
            request.files['image'],request.form['fullName'],request.form['about'],request.form['company'],\
            request.form['job'],request.form['country'],request.form['address'],request.form['phone'],\
            request.form['twitter'],request.form['facebook'],request.form['instagram'],request.form['linkedin'],request.form['github']
        
        image.save(f"static/assets/upload/{image.filename}")
        
        with open(f"static/assets/upload/{image.filename}", "rb") as imageFile:
            encoded_image = codecs.encode(imageFile.read(),encoding="base64")
        decoded_image=encoded_image.decode()
        
        auth_db.find_one_and_update(filter={'_id':id},
                                    update={'$set':{'image':f'{decoded_image}','name':f'{name}','about':f'{about}','company':f'{company}',
                                            'job':f'{job}','country':f'{country}','address':f'{address}','phone':f'{phone}',
                                            'twitter':f'{twitter}','facebook':f'{facebook}','instagram':f'{instagram}',
                                            'linkedin':f'{linkedin}','github':f'{github}'}})
        
        flash({'title': "Success", 'message': "Profile Updated Successfully!"}, 'success')
        return redirect("/User-Profile")

@app.route("/User-Profile/Edit-Password",methods=["GET","POST"])
def edit_password():
    if request.method=="GET":
        return redirect("/User-Profile")
    elif request.method=="POST":
        current_password = request.form['password']
        new_password = bcrypt.generate_password_hash(request.form['newpassword']).decode()
        id = ObjectId(session['_user_id'])
        user = auth_db.find_one(filter={"_id":id})
        if user!=None:
            if bcrypt.check_password_hash(user['password'],current_password):
                auth_db.find_one_and_update(filter={"_id":id},update={'$set':{'password':f'{new_password}'}})
                flash({'title': "Success", 'message': "Password Changed Successfully!"}, 'success')
                return redirect("/User-Profile")
            else:
                flash({'title': "Error", 'message': "Wrong Current Password Entered !<br>Please Provide Correct Current Password."}, 'error')
                return redirect("/User-Profile")
        else:
            flash({'title': "Error", 'message': "Something Went Wrong"}, 'error')
            return redirect("/User-Profile")

# @App.route("/User-Profile/Edit-Settings",methods=["GET","POST"])
# @login_required
# def edit_notifications():
#     if request.method=="GET":
#         return redirect("/User-Profile/#profile-settings")
#     elif request.method=="POST":
#         id = ObjectId(session['_user_id'])
#         auth_db.find_one_and_update(filter={'_id':id},update={"$set":{'changesmade':f'{request.form["changesmade"]}','newproducts'}})

@app.route("/Privacy", methods=["GET","POST"])
def privacy():
    return render_template("main/privacy.html")

@app.route("/Terms", methods=["GET","POST"])
def terms():
    return render_template("main/terms_and_conditions.html")

@app.route('/Logout')
def logout():
    """Logs the user out."""
    session.pop('email', None)  # Remove email from the session
    session.pop('first_name',None)
    #return redirect(url_for('login')) # Redirect to login page after logout
    flash({'title': "Success", 'message': "Logged Out Successfully !"}, 'success')
    return redirect('Login')



@app.route("/Chat")
def chat():
    return redirect('http://localhost:5001/chat', code=301)

# for individual to schedule 1 on 1
@app.route("/Schedule", methods=["GET","POST"])
def schedule():
    if request.method == 'POST':
        name = request.form['name']
        title = request.form['title']
        email = request.form['email']
        message = request.form['message']
        payment = request.form['message']
        task_id = schedule_via_email(manager, email, email, title)
        return render_template("main/schedule.html", user_id=email, schedule_id=title,  task_id=task_id)

import uuid
@app.route('/task')
def task():
    """Renders the main page."""
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id

    schedule_id = request.args.get('schedule_id')
    task_id = request.args.get('task_id')
    return render_template("main/schedule.html", user_id=user_id, schedule_id=schedule_id, task_id=task_id)

@app.route('/schedule_task', methods=['POST'])
def schedule_task():
    """Schedules a new task for the user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not found'}), 400

    task_id = schedule_via_email(manager, "chenricher@gmail.com", "chenricher@gmail.com", "schedule a time to meet for you application")
    return jsonify({'schedule_id': "schedule_id", 'task_id': task_id})

'''
new_status: dictionary
'get_friend_availability' ='running'
'check_my_availability' ='pending'
'schedule_meeting' ='pending'
'overall' ='pending'
'''
@app.route('/get_task_status/<task_id>')
def get_task_status(task_id):
    new_status = manager.get_task_status(task_id)
    return jsonify({'status': new_status['schedule_meeting']})

@app.errorhandler(404)
def not_found(error):
    return render_template("extra/404.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
