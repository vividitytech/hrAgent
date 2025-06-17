import mysql.connector
import os
from dotenv import load_dotenv

def execute_query(cursor, query):
    """Executes a SQL query using the provided cursor."""
    try:
        cursor.execute(query)
    except mysql.connector.Error as err:
        print(f"Error executing query: {err}")
        raise  # Re-raise the exception for handling elsewhere

def connect_to_db(host, user, password, database):
    """Connects to the MySQL database."""
    try:
        mydb = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        return mydb
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None


load_dotenv()

# MySQL database credentials (using environment variables)
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_host = os.environ.get("DB_HOST")
db_name = os.environ.get("DB_NAME")  # This assumes you have already created the DATABASE
# or it exists

def change_type(mycursor, table_name, field_name):

    # Change data type from INT to TEXT (or VARCHAR)
    alter_query = f"ALTER TABLE {table_name} MODIFY COLUMN {field_name} TEXT;"  #or LONGTEXT
    execute_query(mycursor, alter_query)

def add_field(mycursor, table_name, new_field_name, new_field_type):
    #table_name = "your_table"
    #new_field_name = "new_column"
    #new_field_type = "INT"

    add_column_query = f"ALTER TABLE {table_name} ADD COLUMN {new_field_name} {new_field_type};"
    # add_column_query = f"ALTER TABLE {table_name} ADD COLUMN {new_field_name} {new_field_type} NOT NULL DEFAULT '';" #must give a default value if NOT NULL
    execute_query(mycursor, add_column_query)

def remove_field(mycursor, table_name,field_to_remove):
    # table_name = "your_table"
    # field_to_remove = "column_to_remove"
    drop_column_query = f"ALTER TABLE {table_name} DROP COLUMN {field_to_remove};"
    execute_query(mycursor, drop_column_query)


def remove_foreign_key(mycursor, table_name, constraint_name, column_to_remove):
    #table_name = "your_table"
    #constraint_name = "fk_constraint_name" # Name of the foreign key constraint
    mycursor.execute(f"DESCRIBE {table_name}")  # Be careful with SQL injection, see warning below.
    # Alternative using INFORMATION_SCHEMA (more robust against SQL injection)
    # mycursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table_name}'")

    columns_and_types = []
    for row in mycursor:
        columns_and_types.append((row[0], row[1])) # DESCRIBE: column_name, data_type, ...
            # For INFORMATION_SCHEMA: (row[0], row[1]) would also work, since the query selected them in that order.


    if constraint_name is None:
        # Find the constraint name if not provided
        sql_find_constraint = f"""
        SELECT CONSTRAINT_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE REFERENCED_TABLE_NAME = '{table_name}'
        AND COLUMN_NAME = '{column_to_remove}'
        AND CONSTRAINT_SCHEMA = '{db_name}';
        """

        sql_find_constraint = f"""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM
            INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE
            REFERENCED_TABLE_NAME = 'payment_methods' AND REFERENCED_COLUMN_NAME = 'id';  
        """
        #-- Assuming 'id' is the primary key of payment_method table
        mycursor.execute(sql_find_constraint)
        result = mycursor.fetchone()

        if result:
            constraint_name = result[2]
        else:
            print(f"No foreign key constraint found for column '{column_to_remove}' in table '{table_name}'.  Column will still be deleted.")
            # We still proceed to delete the column, but without FK removal.
            constraint_name = None


    if constraint_name:
        # Remove the foreign key constraint
        sql_remove_fk = f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name};"
        try:
            mycursor.execute(sql_remove_fk)
            mydb.commit()
            print(f"Foreign key constraint '{constraint_name}' removed from table '{table_name}'.")
        except mysql.connector.Error as err:
            print(f"Error removing foreign key: {err}")
            # It's important to handle errors gracefully, especially if the FK doesn't exist
            # but we're trying to remove it.  We still want to proceed to the column deletion.




    #drop_fk_query = f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name};"
    #execute_query(mycursor, drop_fk_query)

    # Then drop the column
    # column_to_remove = "column_to_remove"
    drop_column_query = f"ALTER TABLE {table_name} DROP COLUMN {column_to_remove};"
    execute_query(mycursor, drop_column_query)

# Example Usage (assuming you've set up your database connection):
if __name__ == "__main__":
    mydb = connect_to_db(db_host, db_user, db_password, db_name)

    if mydb:
        mycursor = mydb.cursor()

        try:
            # Example modifications go here (see specific examples below)

            #remove_foreign_key(mycursor, "user_subscriptions", None, "payment_method_id")
            add_field(mycursor, "user_subscriptions", "payment_method_token", "TEXT")
            mydb.commit()  # Important:  Commit the changes to the database
            print("Table modifications completed successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
            mydb.rollback()  # Rollback changes if an error occurred
            print("Changes rolled back.")

        finally:
            mycursor.close()
            mydb.close()