import secrets
import string

def genPW(length=40):
    """
    Generates a cryptographically secure random password.
    """
    # Define the possible characters for a strong password
    alphabet = string.ascii_letters + string.digits + string.punctuation
    
    while True:
        # Generate the password
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        
        # Ensure the password meets complexity requirements
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in string.punctuation for c in password)):
            break # Exit the loop if all criteria are met
            
    return password