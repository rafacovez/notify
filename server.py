from flask import Flask, request
import sqlite3
import requests
from dotenv import load_dotenv
import os

load_dotenv()

conn = sqlite3.connect('spotify.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS tokens (id INTEGER PRIMARY KEY, token TEXT)')
conn.commit()

app = Flask(__name__)

@app.route('/callback')
def callback():
    # handle if error or authorization denied
    error = request.args.get('error')
    if error:
        return 'Authorization denied'
    
    code = request.args.get('code')
    if code:
        # exchange authorization code for an access token
        token_endpoint = 'https://accounts.spotify.com/api/token'
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        redirect_uri = os.getenv('REDIRECT_URI')
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
        }
        response = requests.post(token_endpoint, data=params)
        response_data = response.json()

        access_token = response_data.get('access_token')

        # store the access token in the database
        cursor.execute('INSERT INTO tokens (token) VALUES (?)', (access_token,))
        conn.commit()
        
        return f'Access token: {access_token}'
    # handle other errors
    return 'Unexpected error'

if __name__ == '__main__':
    app.run(port=8000)
