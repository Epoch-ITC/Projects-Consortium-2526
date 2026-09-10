import os
import sys
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

_CACHED_GET_GRADES_FUNCTION = None

def _load_encrypted_function():
    """
    Decrypts the 'aims_fetcher.enc' file using the key from env
    and returns the 'get_grades' function.
    """
    key = os.getenv("AIMS_ENCRYPTION_KEY")
    if not key:
        raise ValueError("AIMS_ENCRYPTION_KEY not found in environment variables.")

    # Path to the encrypted file (assumed to be in the same directory as this script)
    enc_path = os.path.join(os.path.dirname(__file__), 'aims_fetcher.enc')
    
    if not os.path.exists(enc_path):
        raise FileNotFoundError(f"Encrypted file not found at {enc_path}")
        
    # Read encrypted data
    with open(enc_path, 'rb') as f:
        encrypted_data = f.read()
        
    # Decrypt
    try:
        fernet = Fernet(key)
        decrypted_code = fernet.decrypt(encrypted_data).decode('utf-8')
    except Exception as e:
        raise ValueError("Failed to decrypt code. Invalid Key? Check AIMS_ENCRYPTION_KEY") from e
    
    # Create a local namespace to execute the code
    module_namespace = {}
    
    # Execute the decrypted code
    try:
        exec(decrypted_code, module_namespace)
    except Exception as e:
        raise RuntimeError(f"Failed to execute decrypted code: {e}")
    
    # Retrieve the function
    if 'get_grades' not in module_namespace:
        raise ValueError("The encrypted code did not contain 'get_grades' function.")
        
    return module_namespace['get_grades']

def get_grades(username, password):
    """
    Wrapper function that decrypts the actual function (if not already done)
    and calls it with the provided arguments.
    """
    global _CACHED_GET_GRADES_FUNCTION
    if _CACHED_GET_GRADES_FUNCTION is None:
        _CACHED_GET_GRADES_FUNCTION = _load_encrypted_function()
        
    return _CACHED_GET_GRADES_FUNCTION(username, password)

if __name__ == "__main__":
    # Simple CLI for testing the secure wrapper
    if len(sys.argv) > 1:
        u = sys.argv[1]
    else:
        u = input("Username: ").strip()
    
    import getpass
    p = getpass.getpass("Password: ")
    
    try:
        print("[-] Calling secure get_grades...")
        result = get_grades(u, p)
        print(result)
    except Exception as e:
        print(f"[!] Error: {e}")
