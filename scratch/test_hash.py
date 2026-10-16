import os
import urllib.request
import json
import hashlib

app_id = os.getenv('FYERS_APP_ID', 'SAMPLEAPPID-100')
secret = os.getenv('FYERS_SECRET_KEY', 'sample_secret_placeholder')
code = os.getenv('FYERS_AUTH_CODE', 'sample_auth_code_placeholder')

hash1 = hashlib.sha256((app_id + ':' + secret).encode()).hexdigest()
hash2 = hashlib.sha256((app_id.split('-')[0] + ':' + secret).encode()).hexdigest()
hash3 = hashlib.sha256((app_id.replace('-200', '-100') + ':' + secret).encode()).hexdigest()

print("Hash 1 (standard):", hash1)
print("Hash 2 (short):", hash2)
print("Hash 3 (as -100):", hash3)

for name, h in [('standard', hash1), ('short', hash2), ('as-100', hash3)]:
    print(f"\nTesting {name} hash...")
    payload = {
        'grant_type': 'authorization_code',
        'appIdHash': h,
        'code': code
    }
    req = urllib.request.Request(
        'https://api-t1.fyers.in/api/v3/validate-authcode',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        resp = urllib.request.urlopen(req)
        print("Success:", resp.read())
    except urllib.error.HTTPError as e:
        print("Error:", e.code, e.read().decode())
    except Exception as e:
        print("Exception:", e)
