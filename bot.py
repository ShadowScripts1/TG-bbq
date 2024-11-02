import subprocess
import sys
import json
import requests
import time
from urllib.parse import parse_qs, unquote
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import os
import random
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the required modules
required_modules = ['base64', 'time', 'json', 'requests', 'urllib.parse', 'Crypto']

# Function to check and install missing modules
def check_and_install_modules():
    for module in required_modules:
        try:
            __import__(module)
            logging.info(f"✅ Module '{module}' found.")
        except ImportError:
            logging.warning(f"❌ Module '{module}' missing. Installing...")
            if module == 'Crypto':
                install('pycryptodome')
            else:
                install(module)

# Helper function to install packages
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

check_and_install_modules()

def encode_event(e, t):
    r = f"{e}|{t}|{int(time.time())}"
    n = "tttttttttttttttttttttttttttttttt"
    key = n.encode('utf-8')
    iv = key[:16]  # Use the first 16 bytes for IV
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(r.encode('utf-8'), AES.block_size))
    return base64.b64encode(base64.b64encode(encrypted)).decode('utf-8')

user_agents = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.6723.90 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.86 Mobile Safari/537.36"
]

user_agent_file = "user_agent.txt"
if not os.path.exists(user_agent_file):
    selected_user_agent = random.choice(user_agents)
    with open(user_agent_file, "w") as f:
        f.write(selected_user_agent)
else:
    with open(user_agent_file, "r") as f:
        selected_user_agent = f.read().strip()

logging.info(f"Using User Agent: {selected_user_agent}")

query_ids = []
try:
    with open('data.txt', 'r') as file:
        query_ids = [line.strip() for line in file if line.strip()]
        for query_id in query_ids:
            logging.info(f"Loaded query ID: {query_id}")
except FileNotFoundError:
    logging.error("File 'data.txt' not found.")
    sys.exit(1)

if not query_ids:
    logging.error("No query IDs found in 'data.txt'. Exiting.")
    sys.exit(1)

taps = '15000'
base_headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'user-agent': selected_user_agent,
}

user_balances = {}

def bbq_tap(query_id):
    try:
        query_params = parse_qs(query_id)
        user_info = json.loads(query_params['user'][0])
        user_id = str(user_info['id'])
        user_name = unquote(user_info.get('first_name', 'Unknown User'))
        
        data = {
            'id_user': user_id,
            'mm': taps,
            'game': encode_event(user_id, taps),
        }
        
        headers = base_headers.copy()
        headers['use-agen'] = query_id  # Insert query ID here
        
        response = requests.post('https://bbqbackcs.bbqcoin.ai/api/coin/earnmoney', headers=headers, data=data)
        response.raise_for_status()
        
        if 'data' in response.json():
            balance = response.json()['data']
            user_balances[user_name] = balance
            logging.info(f"Updated balance for {user_name}: {balance}")
            return user_name, balance  # Return both name and balance
        else:
            logging.warning(f"Unexpected response format for {user_name}: {response.json()}")

    except (KeyError, json.JSONDecodeError) as e:
        logging.error(f"Error parsing query ID: {query_id}. Skipping. Error: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error making request for {query_id}: {e}")

# Function to display user balances in a single line
def display_balances():
    print("\033c", end="")  # Clear the terminal (Linux/Mac)
    for user, balance in user_balances.items():
        print(f"{user}: ⚡ Coins Added! Total Coins: {balance} 🪙")

# Main execution loop using ThreadPoolExecutor
with ThreadPoolExecutor() as executor:
    while True:
        # Schedule all requests with a delay
        futures = {executor.submit(bbq_tap, query_id): query_id for query_id in query_ids}
        for future in futures:
            try:
                result = future.result()  # Wait for each future to complete
                if result:  # If there was a successful update
                    user_name, balance = result
                    user_balances[user_name] = balance  # Update the global balance dictionary
            except Exception as e:
                logging.error(f"Error occurred: {e}")

        display_balances()  # Display all balances after each batch
        time.sleep(0.80)  # Delay between processing batches of requests
