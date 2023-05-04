from flask import Flask, request
import sqlite3
import uuid
import requests
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

@app.route('/callback')
def callback():

    conn = sqlite3.connect('acounts.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS tokens (id INTEGER PRIMARY KEY, unique_id TEXT, refresh_token TEXT, token TEXT)')
    conn.commit()

    # handle if error or authorization denied
    error = request.args.get('error')
    if error:
        cursor.close()
        conn.close()
        return 'Authorization denied'
    
    code = request.args.get('code')
    if code:
        # generate unique id
        unique_id = uuid.uuid1()

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
        refresh_token = response_data.get('refresh_token')

        # store the access token in the database
        cursor.execute('INSERT INTO tokens (unique_id, refresh_token, token) VALUES (?, ?, ?)', (str(unique_id), refresh_token, access_token))
        conn.commit()
        
        cursor.close()
        conn.close()

        return f'Unique ID: {unique_id}. Refresh token: {refresh_token}. Access token: {access_token}'
    
    # handle other errors
    cursor.close()
    conn.close()
    return 'Unexpected error'

if __name__ == '__main__':
    app.run(port=8000)
