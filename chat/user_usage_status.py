import time
import datetime
import sqlite3  # Or your database of choice

class UsageLimiter:
    """
    Limits API usage based on user type, using configurable table names.
    """

    def __init__(self, database_path="app.db", limit=3, period=24,
                 users_table_name="users", usage_table_name="usage"):
        """
        Initializes the UsageLimiter.

        Args:
            database_path (str): Path to the database file.
            limit (int): Maximum allowed usage within the period (for unpaid users).
            period (int): The period in hours.
            users_table_name (str): Name of the users table.
            usage_table_name (str): Name of the usage table.
        """
        self.database_path = database_path
        self.limit = limit
        self.period = period
        self.users_table_name = users_table_name
        self.usage_table_name = usage_table_name

        self.conn = None # initialize connection
        self.cursor = None # initialize cursor
        self._create_tables()

    def _get_connection(self):
        """Helper to get the database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.database_path)
        return self.conn

    def _get_cursor(self):
        """Helper to get the database cursor."""
        if self.cursor is None or self.conn is None:
            self.conn = self._get_connection()
            self.cursor = self.conn.cursor()
        return self.cursor


    def _create_tables(self):
        """Creates the users and usage tables if they don't exist."""
        conn = self._get_connection()
        cursor = self._get_cursor()

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.users_table_name} (
                user_id TEXT PRIMARY KEY,
                user_type TEXT NOT NULL DEFAULT 'unpaid' CHECK (user_type IN ('unpaid', 'pay_as_you_go', 'monthly_subscription'))
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.usage_table_name} (
                user_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES {self.users_table_name}(user_id),
                PRIMARY KEY (user_id, timestamp)
            )
        """)
        conn.commit()

    def get_user_type(self, user_id):
        """
        Gets the user type from the users table.
        """
        conn = self._get_connection()
        cursor = self._get_cursor()

        cursor.execute(f"SELECT user_type FROM {self.users_table_name} WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 'unpaid'

    def is_allowed(self, user_id):
        """
        Checks if a user is allowed to use the API based on their user type and usage history.
        """
        user_type = self.get_user_type(user_id)

        if user_type == 'monthly_subscription':
            return True  # Monthly subscribers are always allowed

        if user_type == 'pay_as_you_go':
            return True  # Pay-as-you-go users are always allowed (assuming charged separately)

        # Handle unpaid users (check usage limit)
        conn = self._get_connection()
        cursor = self._get_cursor()

        now = time.time()
        cutoff = now - (self.period * 3600)  # Calculate the cutoff timestamp

        cursor.execute(f"""
            SELECT COUNT(*) FROM {self.usage_table_name}
            WHERE user_id = ? AND timestamp > ?
        """, (user_id, cutoff))
        count = cursor.fetchone()[0]

        return count < self.limit  # Allowed if usage count is less than the limit


    def record_usage(self, user_id):
        """
        Records an API usage event for a user.
        """
        conn = self._get_connection()
        cursor = self._get_cursor()

        cursor.execute(f"INSERT INTO {self.usage_table_name} (user_id, timestamp) VALUES (?, ?)",
                       (user_id, time.time()))
        conn.commit()


    def create_user(self, user_id, user_type='unpaid'):
        """
        Creates a new user in the users table.
        """
        conn = self._get_connection()
        cursor = self._get_cursor()
        try:
            cursor.execute(f"INSERT INTO {self.users_table_name} (user_id, user_type) VALUES (?, ?)", (user_id, user_type))
            conn.commit()
        except sqlite3.IntegrityError:
            print(f"User with ID '{user_id}' already exists.")

    def update_user_type(self, user_id, new_user_type):
        """
        Updates the user type for a given user.
        """
        conn = self._get_connection()
        cursor = self._get_cursor()

        cursor.execute(f"UPDATE {self.users_table_name} SET user_type = ? WHERE user_id = ?", (new_user_type, user_id))
        conn.commit()

    def close(self):
        """Closes the database connections."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

# Example usage
if __name__ == '__main__':
    limiter = UsageLimiter(database_path="test_app.db", limit=3, period=24, users_table_name="accounts", usage_table_name="api_calls")

    unpaid_user = "unpaid_user"
    pay_as_you_go_user = "pay_user"
    monthly_user = "monthly_user"

    # Create the users
    limiter.create_user(unpaid_user, "unpaid")
    limiter.create_user(pay_as_you_go_user, "pay_as_you_go")
    limiter.create_user(monthly_user, "monthly_subscription")

    print("--- Unpaid User ---")
    for i in range(5):
        if limiter.is_allowed(unpaid_user):
            print(f"Request {i+1}: Allowed (Unpaid User)")
            limiter.record_usage(unpaid_user)
            time.sleep(1)
        else:
            print(f"Request {i+1}: Denied - Usage limit reached (Unpaid User)")
            break

    print("\n--- Pay-as-you-go User ---")
    for i in range(2):
        if limiter.is_allowed(pay_as_you_go_user):
            print(f"Request {i+1}: Allowed (Pay-as-you-go User)")
            limiter.record_usage(pay_as_you_go_user)
            time.sleep(1)
        else:
            print(f"Request {i+1}: Denied - Should not happen (Pay-as-you-go)")
            break

    print("\n--- Monthly Subscription User ---")
    for i in range(2):
        if limiter.is_allowed(monthly_user):
            print(f"Request {i+1}: Allowed (Monthly Subscription User)")
            limiter.record_usage(monthly_user)
            time.sleep(1)
        else:
            print(f"Request {i+1}: Denied - Should not happen (Monthly Subscription)")
            break

    limiter.close()