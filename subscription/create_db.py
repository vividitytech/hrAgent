import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# MySQL database credentials (using environment variables)
db_user = os.environ.get("DB_USER")  # e.g., "root"
db_password = os.environ.get("DB_PASSWORD")
db_host = os.environ.get("DB_HOST")  # e.g., "localhost"
db_name = os.environ.get("DB_NAME")  # The DATABASE you want to create

try:
    # Establish a connection to the MySQL server (without specifying the database initially)
    mydb = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password
    )

    mycursor = mydb.cursor()

    # Create the database (if it doesn't exist)
    mycursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    print(f"Database '{db_name}' created (or already exists).")

    # Optional: Switch to the newly created database (not strictly necessary here)
    mycursor.execute(f"USE {db_name}")
    print(f"Using database '{db_name}'.")

    mydb.commit()  # Commit the changes
    mycursor.close()
    mydb.close()

except mysql.connector.Error as err:
    print(f"Error creating database: {err}")