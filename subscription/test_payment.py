import stripe
import os  # For accessing environment variables
from dotenv import load_dotenv  # For loading environment variables from a .env file

# Load environment variables from a .env file (if you have one)
load_dotenv()


# --- Configuration ---
#  It's best practice to keep your Stripe secret key out of your code directly.
#  Use environment variables instead.  This is especially important if you're
#  committing your code to a public repository.
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

#  If you don't have a .env file or environment variable set, you can
#  temporarily set the key directly (NOT RECOMMENDED FOR PRODUCTION):
# stripe.api_key = "YOUR_STRIPE_SECRET_KEY"


def create_payment(card_number, card_exp_month, card_exp_year, card_cvc, amount, currency="usd", description="Payment using Stripe"):
    """
    Creates a payment using Stripe with card details.

    Args:
        card_number (str): The card number.
        card_exp_month (int): The card expiration month (e.g., 1 for January).
        card_exp_year (int): The card expiration year (e.g., 2024).
        card_cvc (str): The card CVC.
        amount (int): The payment amount in cents (e.g., 1000 for $10.00).  Stripe requires amount to be in smallest currency unit.
        currency (str): The currency of the payment (default: "usd").
        description (str):  A description for the payment.  Optional.

    Returns:
        dict: A dictionary containing the payment intent confirmation or an error message.
              Returns None if a critical error occurs (like missing API key).
    """

    if not stripe.api_key:
        print("Error: Stripe API key not set.  Please set the STRIPE_SECRET_KEY environment variable.")
        return None  # Indicate critical failure

    try:
        # 1. Create a Payment Method
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": card_number,
                "exp_month": card_exp_month,
                "exp_year": card_exp_year,
                "cvc": card_cvc,
            },
        )

        # 2. Create a Payment Intent
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            payment_method=payment_method.id,
            confirmation_method="manual",  # important if you want to confirm yourself
            confirm=True, # Immediately confirm the payment (if you want to)
            description=description,
        )


        # 3. Handle Payment Intent Status (Very important!)
        if payment_intent.status == "succeeded":
            return {"status": "succeeded", "payment_intent": payment_intent}
        elif payment_intent.status == "requires_action":
            # Handle actions required by the customer (e.g., 3D Secure authentication)
            return {"status": "requires_action", "payment_intent": payment_intent}
        elif payment_intent.status == "requires_confirmation":
            # Confirm the PaymentIntent to finalize the payment
            payment_intent = stripe.PaymentIntent.confirm(payment_intent.id)
            return {"status": "succeeded", "payment_intent": payment_intent} # Assuming confirmation worked.
        elif payment_intent.status == "requires_payment_method":
              # The payment failed - often due to an invalid card or insufficient funds.
              return {"status": "failed", "error": "Payment failed - invalid card or insufficient funds."}  # Add more details as needed
        else:
            # Handle unexpected PaymentIntent status
            return {"status": "error", "error": f"Unexpected PaymentIntent status: {payment_intent.status}"}


    except stripe.error.CardError as e:
        # Handle card errors (e.g., invalid card number, expired card)
        return {"status": "failed", "error": str(e)}
    except stripe.error.RateLimitError as e:
        # Too many requests made to the API too quickly
        return {"status": "failed", "error": "Rate limit error. Please try again later."}
    except stripe.error.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        return {"status": "failed", "error": f"Invalid request: {str(e)}"}
    except stripe.error.AuthenticationError as e:
        # Authentication issues
        return {"status": "failed", "error": "Authentication error. Check your API key."}
    except stripe.error.APIConnectionError as e:
        # Network communication error
        return {"status": "failed", "error": "Network error. Please check your internet connection."}
    except stripe.error.StripeError as e:
        # Generic error handling
        return {"status": "failed", "error": f"Stripe error: {str(e)}"}
    except Exception as e:
        # Handle unexpected errors
        return {"status": "error", "error": f"An unexpected error occurred: {str(e)}"}


# --- Example Usage ---
if __name__ == "__main__":
    # Replace with your actual card details (for testing purposes only!  NEVER use real card details in testing)
    test_card_number = "4242424242424242" # Stripe's test card number
    test_card_exp_month = 12
    test_card_exp_year = 2024
    test_card_cvc = "123"
    test_amount = 1000  # $10.00

    payment_result = create_payment(
        test_card_number, test_card_exp_month, test_card_exp_year, test_card_cvc, test_amount
    )

    if payment_result:
        print("Payment Result:", payment_result)

        if payment_result["status"] == "succeeded":
            print("Payment succeeded!")
            print("Payment Intent ID:", payment_result["payment_intent"].id) # Access the PaymentIntent ID
        elif payment_result["status"] == "requires_action":
            print("Payment requires action (e.g., 3D Secure). Handle this in your frontend.")
            #  You'll need to redirect the user to the `payment_result["payment_intent"].next_action.redirect_to_url.url`
            #  to complete the authentication process.  This is typically done in the frontend.
        elif payment_result["status"] == "failed":
            print("Payment failed:", payment_result["error"])
        elif payment_result["status"] == "error":
            print("An error occurred:", payment_result["error"])
        else:
            print("Unknown payment status.")
    else:
        print("Failed to initialize payment process. Check API key.")