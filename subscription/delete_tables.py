import mysql.connector
import os
from dotenv import load_dotenv
from sql_columns_operation import remove_foreign_key
load_dotenv()

# MySQL database credentials (using environment variables)
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_host = os.environ.get("DB_HOST")
db_name = os.environ.get("DB_NAME")  # This assumes you have already created the DATABASE
# or it exists

try:
    # Establish a connection to the MySQL database
    mydb = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name  # Now we are specifying database because the database now exists
    )

    mycursor = mydb.cursor()
    sql = "DROP TABLE IF EXISTS payment_methods"
    mycursor.execute(sql) 

    mycursor.close()
    mydb.close()

except mysql.connector.Error as err:
    print(f"Error creating tables: {err}")