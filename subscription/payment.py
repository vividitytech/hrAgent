from flask import Flask, request, jsonify, render_template, redirect
import stripe
import os
import mysql.connector
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# Stripe configuration (get keys from environment variables)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# MySQL database configuration (get from environment variables)
db_config = {
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'host': os.environ.get("DB_HOST"),
    'database': os.environ.get("DB_NAME"),
    'raise_on_warnings': True
}

# Utility Function to Connect to Database
def connect_to_db():
    return mysql.connector.connect(**db_config)



#------------------------------------------------------
# Basic functions
#------------------------------------------------------
def get_subscription_types():
    """Retrieves the distinct 'type' values from the 'subscriptions' table."""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT DISTINCT type FROM subscriptions")
            types = [row[0] for row in cursor.fetchall()] #extract the type
            return types
    except mysql.connector.Error as e:
        print(f"Error retrieving subscription types: {e}")
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_price_by_type(subscription_type):
    """Retrieves the price for a given subscription type."""
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()
            sql = "SELECT price FROM subscriptions WHERE type = %s"
            cursor.execute(sql, (subscription_type,))  # Use parameterized query to prevent SQL injection
            result = cursor.fetchone()
            if result:
                return result[0]  # Return the price
            else:
                return None # Or handle the case where the type is not found
    except mysql.connector.Error as e:
        print(f"Error retrieving price: {e}")
        return None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


#------------------------------------------------------
# API Endpoints
#------------------------------------------------------
@app.route('/get_subscriptions')
def get_subscriptions():
    try:
        mydb = mysql.connector.connect(**db_config)
        mycursor = mydb.cursor(dictionary=True) # dictionary=True gives you results as dictionaries

        mycursor.execute("SELECT id, name, type, price FROM subscriptions")
        results = mycursor.fetchall()

        mydb.close()
        return jsonify(results) # Convert results to JSON
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return jsonify({'error': str(err)}), 500  # Return error with status code


@app.route('/process_subscription_type', methods=['POST'])
def process_subscription_type():
    try:
        data = request.get_json()
        selected_type = data.get('subscription_type')

        # Validate the selected type
        if selected_type not in ('pay_as_you_go', 'monthly', 'yearly'):
            return jsonify({'error': 'Invalid subscription type'}), 400

        # Connect to the database
        mydb = mysql.connector.connect(**db_config)
        mycursor = mydb.cursor()
        # Example:  You could use the selected_type to filter a query,
        # or to determine which action to take.
        sql = "SELECT * FROM subscriptions WHERE `type` = %s"  # Using parameterized query
        val = (selected_type,)
        mycursor.execute(sql, val)

        results = mycursor.fetchall()
        print(f"Query results based on selected type {selected_type}: {results}")

        mydb.commit()  # Commit the changes
        mycursor.close()
        mydb.close()

        return jsonify({'message': f'Received subscription type: {selected_type}', 'results': results})

    except Exception as e:
        print(f"Error processing request: {e}") #log error for debugging
        return jsonify({'error': str(e)}), 500


#----------------
# Subscription Management
#----------------
@app.route('/add_payment_method', methods=['POST'])
def add_payment_method():
    try:
        data = request.get_json()
        user_id = data['user_id']
        payment_method_id = data['payment_method_id']
        conn = connect_to_db()
        cursor = conn.cursor()  

        # Insert user subscription
        cursor.execute(
            "INSERT INTO payment_methods (user_id, payment_method_id) VALUES (%s, %s)",
            (user_id, payment_method_id, 'active')
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Subscribed successfully'}), 200
    except Exception as e:
        if conn:
            conn.rollback() #Rollback on error
            cursor.close()
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/subscribe', methods=['POST'])
def subscribe():
    try:
        data = request.get_json()
        user_id = data['user_id']
        subscription_id = data['subscription_id']
        #payment_method_id = data['payment_method_id']
        payment_token = data['stripeToken']
        conn = connect_to_db()
        cursor = conn.cursor()

        if 'price' in data and data['price'] is None:
            # Fetch subscription details
            cursor.execute("SELECT type, price FROM subscriptions WHERE id = %s", (subscription_id,))
            subscription_data = cursor.fetchone()

            if not subscription_data:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Subscription not found'}), 400

            subscription_type, price = subscription_data
        else:
            subscription_type = "pay_as_you_go"
            price = data['price']
            if not subscription_id:
                subscription_id = 1

        start_date = datetime.now().date()
        end_date = None
        next_payment_date = None

        if subscription_type == 'monthly':
            next_payment_date = start_date + timedelta(days=30)
        elif subscription_type == 'yearly':
            next_payment_date = start_date + timedelta(days=365)

        # Charge the user if not pay-as-you-go
        transaction_id = None
        payment_status = 'pending' #default status
        '''
        if subscription_type != 'pay_as_you_go':
            # Fetch payment method details (token)
            cursor.execute("SELECT details FROM payment_methods WHERE id = %s AND user_id = %s", (payment_method_id, user_id))
            payment_method_data = cursor.fetchone()

            if not payment_method_data:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Payment method not found or not authorized'}), 400
        
            payment_token = payment_method_data[0]
            '''
        try:
            # Create a Stripe charge
            charge = stripe.Charge.create(
                amount=int(price * 100),  # Amount in cents
                currency='usd',
                source=payment_token,  # Use the tokenized payment method
                description=f"Subscription payment for {subscription_id}"
            )
            transaction_id = charge.id
            payment_status = 'success'
        except stripe.error.CardError as e:
            payment_status = 'failed'
            error_message = str(e)
            cursor.close()
            conn.close()
            return jsonify({'error': f'Payment failed: {error_message}'}), 400
        except Exception as e:
            payment_status = 'failed'
            error_message = str(e)
            cursor.close()
            conn.close()
            return jsonify({'error': f'Error processing payment: {error_message}'}), 500

        # Insert user subscription
        payment_method_id =1
        cursor.execute(
            "INSERT INTO user_subscriptions (user_id, subscription_id, start_date, end_date, next_payment_date, payment_method_token, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user_id, subscription_id, start_date, end_date, next_payment_date, payment_token, 'active')
        )
        user_subscription_id = cursor.lastrowid

        # Insert payment record
        cursor.execute(
            "INSERT INTO payments (user_subscription_id, payment_date, amount, transaction_id, status, payment_method) VALUES (%s, %s, %s, %s, %s, %s)",
            (user_subscription_id, datetime.now(), price, transaction_id, payment_status, 'credit_card')  # Adjust payment_method
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Subscribed successfully'}), 200

    except Exception as e:
        if conn:
            conn.rollback() #Rollback on error
            cursor.close()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/cancel_subscription', methods=['POST'])
def cancel_subscription():
    try:
        data = request.get_json()
        user_subscription_id = data['user_subscription_id']

        conn = connect_to_db()
        cursor = conn.cursor()

        # Update subscription status
        cursor.execute("UPDATE user_subscriptions SET status = 'canceled', end_date = %s WHERE id = %s", (datetime.now().date(), user_subscription_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Subscription canceled successfully'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/update_payment_method', methods=['POST'])
def update_payment_method():
    try:
        data = request.get_json()
        user_id = data['user_id']
        payment_method_id = data['payment_method_id']
        new_payment_token = data['new_payment_token']

        conn = connect_to_db()
        cursor = conn.cursor()

        # Update payment method details
        cursor.execute("UPDATE payment_methods SET details = %s WHERE id = %s AND user_id = %s", (new_payment_token, payment_method_id, user_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Payment method updated successfully'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/get_subscription_details', methods=['GET'])
def get_subscription_details():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        conn = connect_to_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.name, us.status, us.next_payment_date
            FROM user_subscriptions us
            JOIN subscriptions s ON us.subscription_id = s.id
            WHERE us.user_id = %s AND us.status = 'active'
        """, (user_id,))

        subscription_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if subscription_data:
            subscription_name, status, next_payment_date = subscription_data
            return jsonify({
                'subscription_name': subscription_name,
                'status': status,
                'next_payment_date': str(next_payment_date) if next_payment_date else None
            }), 200
        else:
            return jsonify({'message': 'No active subscription found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

#----------------
# Payment Verification
#----------------
def requires_payment(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')  # Example
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400

        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user_subscriptions WHERE user_id = %s AND status = 'active'", (user_id,))
        has_active_subscription = cursor.fetchone() is not None

        cursor.close()
        conn.close()

        if not has_active_subscription:
            return jsonify({'error': 'Payment required to access this resource'}), 403

        return f(*args, **kwargs)
    return decorated_function

@app.route('/protected')
@requires_payment
def protected_resource():
    return jsonify({'message': 'You have access!'})


@app.route('/payment')
def payment():
    return render_template('payment.html')

# Serve the HTML Page.  This is the entry point for your site.
@app.route('/', methods=['GET'])
def index():
    return render_template('subscription.html')


'''
      
export STRIPE_SECRET_KEY="your_stripe_secret_key"
export STRIPE_PUBLISHABLE_KEY="your_stripe_publishable_key"
export DB_USER="your_db_user"
export DB_PASSWORD="your_db_password"
export DB_HOST="your_db_host"
export DB_NAME="your_db_name"

'''
@app.route('/home')
def home():
    new_ip = '0.0.0.0'  # Replace with the desired IP address
    new_port = '5000'      # Replace with the desired port
    new_url = f'http://{new_ip}:{new_port}/'
    return redirect(new_url, code=302)
#------------------------------------------------------
# Main
#------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)