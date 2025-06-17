import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()
def create_subscriptions_table(db_config):
    """
    Creates the 'subscriptions' table in the MySQL database.

    Args:
        db_config (dict):  A dictionary containing the database connection parameters.
                            Example:
                            {
                                'host': 'your_host',
                                'user': 'your_user',
                                'password': 'your_password',
                                'database': 'your_database'
                            }
    """

    try:
        # Establish a connection to the MySQL database
        mydb = mysql.connector.connect(**db_config)
        mycursor = mydb.cursor()

        # SQL statement to create the 'subscriptions' table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            type ENUM('pay_as_you_go', 'monthly', 'yearly') NOT NULL,
            price DECIMAL(10, 2) NOT NULL
        );
        """

        # Execute the SQL query
        mycursor.execute(create_table_query)

        # Commit the changes to the database
        mydb.commit()
        print("Subscriptions table created successfully (if it didn't already exist).")


    except mysql.connector.Error as err:
        print(f"Error creating table: {err}")

    finally:
        # Close the cursor and connection
        if mycursor:
            mycursor.close()
        if mydb:
            mydb.close()

def insert_sample_subscriptions(db_config):
    """
    Inserts sample data into the 'subscriptions' table.

    Args:
        db_config (dict):  A dictionary containing the database connection parameters.
                            (Same as create_subscriptions_table)
    """

    try:
        mydb = mysql.connector.connect(**db_config)
        mycursor = mydb.cursor()


        # Insert sample data (if the table is empty)
        mycursor.execute("SELECT COUNT(*) FROM subscriptions")
        count = mycursor.fetchone()[0]


        # Sample subscription data
        subscriptions_data = [
            ('Pay-As-You-Go Plan', 'Pay only for what you use.', 'pay_as_you_go', 0.00),
            ('Monthly Basic', 'Basic access for one month.', 'monthly', 9.99),
            ('Monthly Premium', 'Premium features for one month.', 'monthly', 29.99),
            ('Yearly Basic', 'Basic access for one year.', 'yearly', 99.99),
            ('Yearly Premium', 'Premium features for one year.', 'yearly', 299.99),
        ]

        # SQL statement to insert data
        insert_query = """
        INSERT INTO subscriptions (name, description, type, price)
        VALUES (%s, %s, %s, %s)
        """

        # Execute the SQL query for each data entry
        mycursor.executemany(insert_query, subscriptions_data)

        # Commit the changes to the database
        mydb.commit()
        print(f"{mycursor.rowcount} subscriptions inserted successfully.")

    except mysql.connector.Error as err:
        print(f"Error inserting data: {err}")

    finally:
        if mycursor:
            mycursor.close()
        if mydb:
            mydb.close()


# Example Usage:
# MySQL database credentials (using environment variables)
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_host = os.environ.get("DB_HOST")
db_name = os.environ.get("DB_NAME")  # This assumes you have already created the DATABASE
# or it exists

# 1.  Configure your database connection:
db_config = {
    'host': db_host,  # Replace with your MySQL host
    'user': db_user,    # Replace with your MySQL username
    'password': db_password, # Replace with your MySQL password
    'database': db_name # Replace with your MySQL database name
}


# 2. Create the table (only run this once, or after dropping the table)
create_subscriptions_table(db_config)

# 3. Insert sample data (optional, can be run multiple times)
insert_sample_subscriptions(db_config)

print("Done!")