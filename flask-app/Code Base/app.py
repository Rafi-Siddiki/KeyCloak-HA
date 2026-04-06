from flask import Flask, redirect, url_for, session, render_template, request
import requests
import os
from functools import wraps
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

app = Flask(__name__)

# Use the Secret Key from env, or a fallback for safety
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# --- CONFIGURATION FROM ENV ---
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL')
REALM_NAME = os.getenv('REALM_NAME')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
# URLs
TOKEN_URL = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token"
USERINFO_URL = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/userinfo"

# Define the "Security Guard"
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def home():
    user = session.get('user')
    products = [
        {
            "name": "AMD Ryzen 9 7950X Desktop Processor", 
            "price": "65,000৳", 
            "tag": "In Stock",
            "img": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?auto=format&fit=crop&w=500&q=80"
        },
        {
            "name": "NVIDIA GeForce RTX 4090 Founders Edition", 
            "price": "210,000৳", 
            "tag": "Offer",
            "img": "https://images.unsplash.com/photo-1624701928517-44c8ac49d93c?auto=format&fit=crop&w=500&q=80"
        },
        {
            "name": "Corsair Vengeance RGB 32GB DDR5 RAM", 
            "price": "18,500৳", 
            "tag": "New",
            "img": "https://images.unsplash.com/photo-1562976540-1502c2145186?auto=format&fit=crop&w=500&q=80"
        },
        {
            "name": "Mechanical RGB Gaming Keyboard", 
            "price": "8,500৳", 
            "tag": "Sale",
            "img": "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?auto=format&fit=crop&w=500&q=80"
        },
    ]
    return render_template('dashboard.html', user=user, products=products)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, send to home
    if session.get('user'):
        return redirect('/')

    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # DEBUG: Print what we are sending (DO NOT print password in production)
        print(f"--- Attempting Login for: {username} ---")

        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'username': username,
            'password': password,
            'grant_type': 'password',
            'scope': 'openid profile email'
        }

        try:
            # Backend-to-Backend login request
            response = requests.post(TOKEN_URL, data=payload, verify=False)
            
            # --- DEBUGGING BLOCK START ---
            if response.status_code != 200:
                print(f"!!! KEYCLOAK ERROR !!!")
                print(f"Status Code: {response.status_code}")
                print(f"Response Text: {response.text}")
            # --- DEBUGGING BLOCK END ---

            if response.status_code == 200:
                tokens = response.json()
                headers = {'Authorization': f"Bearer {tokens['access_token']}"}
                user_info = requests.get(USERINFO_URL, headers=headers, verify=False).json()
                
                session['user'] = user_info
                return redirect('/')
            else:
                # Capture the specific error for the UI if possible, or generic
                try:
                    error_json = response.json()
                    error_desc = error_json.get('error_description', error_json.get('error', 'Unknown Error'))
                    error = f"Login Failed: {error_desc}"
                except:
                    error = "Invalid credentials or Keycloak Config Error."
                    
        except requests.exceptions.ConnectionError:
            print("!!! CONNECTION ERROR: Could not reach Keycloak !!!")
            error = "Connection failed. Is Keycloak running at the specified IP?"
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR: {e} !!!")
            error = "An unexpected error occurred."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/rafi')
@login_required
def rafi():
    return render_template('rafi.html')

if __name__ == '__main__':
    # Using 0.0.0.0 allows access from other devices if needed
    app.run(host='0.0.0.0', port=5000, debug=True)