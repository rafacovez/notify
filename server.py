from flask import Flask

app = Flask(__name__)

@app.route('/callback')
def callback():
    # handle the Spotify authorization callback here
    return 'Callback received'

if __name__ == '__main__':
    app.run(port=8000)
