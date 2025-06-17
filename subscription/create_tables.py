import mysql.connector
import os
from dotenv import load_dotenv

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

    # SQL statements to create the tables
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL
    );
    """

    create_subscriptions_table = """
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        type ENUM('pay_as_you_go', 'monthly', 'yearly') NOT NULL,
        price DECIMAL(10, 2) NOT NULL
    );
    """

    create_user_subscriptions_table = """
    CREATE TABLE IF NOT EXISTS user_subscriptions (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        subscription_id INT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE,  -- Can be NULL for pay_as_you_go
        status ENUM('active', 'inactive', 'canceled') NOT NULL DEFAULT 'active',
        next_payment_date DATE,
        payment_method_token TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(id),
    );
    """

    create_payments_table = """
    CREATE TABLE IF NOT EXISTS payments (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_subscription_id INT NOT NULL,
        payment_date DATETIME NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        transaction_id VARCHAR(255) NOT NULL,
        status ENUM('success', 'failed') NOT NULL,
        payment_method VARCHAR(255),
        FOREIGN KEY (user_subscription_id) REFERENCES user_subscriptions(id)
    );
    """

    create_payment_methods_table = """
    CREATE TABLE IF NOT EXISTS payment_methods (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        payment_method_id VARCHAR(255) NOT NULL,
        type VARCHAR(255) NOT NULL,
        details TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """

    # Execute the CREATE TABLE statements
    mycursor.execute(create_users_table)
    mycursor.execute(create_subscriptions_table)    
    mycursor.execute(create_payment_methods_table)
    mycursor.execute(create_user_subscriptions_table)
    mycursor.execute(create_payments_table)


    print("Tables created (or already exist).")

    mydb.commit()  # Commit the changes
    mycursor.close()
    mydb.close()

except mysql.connector.Error as err:
    print(f"Error creating tables: {err}")