import os
from fyers_apiv3 import fyersModel
import webbrowser

# Credentials from environment or placeholders
CLIENT_ID = os.getenv("FYERS_APP_ID", "YOUR_CLIENT_ID_HERE")
SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "YOUR_SECRET_KEY_HERE")
REDIRECT_URI = "https://127.0.0.1:5000/" # Standard local redirect URI (must match what you set in Fyers Portal)
RESPONSE_TYPE = "code"
GRANT_TYPE = "authorization_code"

def generate_access_token():
    # Initialize the SessionModel
    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type=RESPONSE_TYPE,
        grant_type=GRANT_TYPE
    )

    # Generate the auth code URL
    auth_link = session.generate_authcode()
    
    print("=" * 60)
    print("STEP 1: OPEN THIS LINK IN YOUR BROWSER AND LOG IN")
    print("=" * 60)
    print(auth_link)
    
    print("\nAttempting to open your browser automatically...")
    try:
        webbrowser.open(auth_link)
    except:
        print("Could not open browser automatically. Please copy and paste the link above manually.")
        
    print("\n" + "=" * 60)
    print("STEP 2: COPY THE AUTH CODE FROM THE URL")
    print("=" * 60)
    print("After you log in, Fyers will redirect you to a page starting with https://127.0.0.1:5000/")
    print("(It's okay if the page says 'Site cannot be reached').")
    print("\nLook at the URL in your browser's address bar. It will look like:")
    print("https://127.0.0.1:5000/?s=ok&code=YOUR_LONG_AUTH_CODE&state=...")
    print("\nCopy ONLY the value after 'code=' (don't include '&state=...').")
    
    auth_code = input("\nPaste your auth_code here and press Enter: ").strip()
    
    if not auth_code:
        print("Auth code cannot be empty.")
        return
        
    session.set_token(auth_code)
    
    # Generate the access token
    try:
        response = session.generate_token()
        if response.get("s") == "ok":
            access_token = response.get("access_token")
            print("\n" + "=" * 60)
            print("SUCCESS! HERE IS YOUR ACCESS TOKEN:")
            print("=" * 60)
            print(access_token)
            print("\n>>> NEXT STEP: Copy this access token and paste it into `ACCESS_TOKEN` inside test_fyers_5m.py")
        else:
            print(f"\nFailed to generate token. API Response: {response}")
    except Exception as e:
        print(f"\nAn error occurred while generating the token: {e}")

if __name__ == "__main__":
    generate_access_token()
