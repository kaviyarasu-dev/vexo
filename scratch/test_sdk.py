import os
from fyers_apiv3 import fyersModel
import json

app_id = os.getenv('FYERS_APP_ID', 'SAMPLEAPPID-100')
secret = os.getenv('FYERS_SECRET_KEY', 'sample_secret_placeholder')
redirect = 'https://127.0.0.1:5000/'
code = os.getenv('FYERS_AUTH_CODE', 'sample_auth_code_placeholder')
pin = '0000'

session = fyersModel.SessionModel(
    client_id=app_id,
    secret_key=secret,
    redirect_uri=redirect,
    response_type="code",
    grant_type="authorization_code"
)

session.set_token(code)
try:
    response = session.generate_token()
    print("SDK Generate Token Response:", response)
except Exception as e:
    print("SDK Exception:", e)

