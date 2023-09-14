import threading
import time
import alarm
import json
from queue import Queue
import ssl
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# Replace with your OAuth credentials
CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
TOKEN_URL = 'https://example.com/oauth/token'

# Define a global variable
global_var = "This is a global variable from main_program"

# Create a queue for communication between main program and daemon thread
webserver_message_queue = Queue()
alarm_message_queue = Queue()
# Set up the Flask web API
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def main():
    global alarm_message_queue
    global webserver_message_queue

    print("Main program started.")

    # Create a thread for the raspi alarm python script and pass the global variable and message queue
    alarm_thread = threading.Thread(target=alarm.run, args=(webserver_message_queue,alarm_message_queue), daemon=True)
    alarm_thread.start()

    

    @app.after_request
    def add_no_cache_header(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/arm', methods=['GET'])
    def enable():
        webserver_message_queue.put("ENABLE-ALARM")
        return jsonify({"status": "ARMED"}), 200
        # data = request.json
        # message = data.get('message')
        # if message:
        #     # Put the message in the queue to be picked up by the daemon thread
        #     message_queue.put(message)
        #     return "Message sent to daemon thread."
        # else:
        #     return "No message provided."

    @app.route('/disarm', methods=['GET'])
    def disable():
        webserver_message_queue.put("DISABLE-ALARM")
        return jsonify({"status": "DISARMED"}), 200

    @app.route('/status', methods=['GET'])
    def status():
        webserver_message_queue.put("ALARM-STATUS")
        try:
            message = alarm_message_queue.get(True, 5) #wait up to 5 seconds for a response
        except Queue.empty: 
            message = "NO RESPONSE"
        print(json.dumps(json.loads(message), indent=2))
        return json.loads(message), 200

    @app.route('/pastevents', methods=['GET'])
    def pastevents():
        webserver_message_queue.put("PAST-EVENTS")
        try:
            message = alarm_message_queue.get(True, 5) #wait up to 5 seconds for a response
        except Queue.empty: 
            message = "NO RESPONSE"
        print(json.dumps(json.loads(message), indent=2))
        return json.loads(message), 200

    @socketio.on('connect')
    def handle_connect():
        #authenticate()
        print('Client connected')
        emit('my response', {'data': 'Connected'})

    @socketio.on('disconnect')
    def disconnect():
        print('Disconnected')
        emit('broadcast', {'data': 'Disconnected'}, broadcast=True)

    @socketio.on('getStatus')
    def handle_message(message):
        #emit('message_from_server', {'message': message['message']}, broadcast=True)
        webserver_message_queue.put("ALARM-STATUS")
        try:
            message = alarm_message_queue.get(True, 5) #wait up to 5 seconds for a response
        except Queue.empty: 
            message = "NO RESPONSE"
        #print(json.dumps(json.loads(message), indent=2))
        emit('postStatus', {'message': json.loads(message)}, broadcast=True)

    @socketio.on('arm')
    def arm(message):
        webserver_message_queue.put("ENABLE-ALARM")

    @socketio.on('disarm')
    def disarm(message):
        webserver_message_queue.put("DISABLE-ALARM")

    @socketio.on('pastEvents')
    def disarm(message):
        webserver_message_queue.put("PAST-EVENTS")

    @socketio.on('getAlarmProfiles')
    def getProfiles(message):
        webserver_message_queue.put("GET-ALARM-PROFILES")
        try:
            message = alarm_message_queue.get(True, 5) #wait up to 5 seconds for a response
        except Queue.empty: 
            message = "NO RESPONSE"
        emit('postAlarmProfiles', {'message': json.loads(message)}, broadcast=True)

    @socketio.on('setAlarmProfile')
    def setAlarmProfile(message):
        webserver_message_queue.put("SET-ALARM-PROFILE-" + str(message['message']))

    @socketio.on_error()
    def error(e):
        print('Error', e)
       

    #ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    #ssl_context.load_cert_chain(certfile='path/to/your/cert.pem', keyfile='path/to/your/key.pem')

    # Run the Flask app
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True)
    #socketio.run(app, host='0.0.0.0', port=8080, ssl_context=ssl_context)


def authenticate():
    try:
        # Create an OAuth2Session and get the access token
        client = BackendApplicationClient(client_id=CLIENT_ID)
        oauth_session = OAuth2Session(client=client)
        token = oauth_session.fetch_token(token_url=TOKEN_URL, client_id=CLIENT_ID,
                                          client_secret=CLIENT_SECRET)
        
        # Perform authentication using the access token
        # Here you can implement your custom authentication logic
        authenticated = True  # Replace with your authentication logic
        
        if authenticated:
            emit('authentication_status', "Authenticated successfully!")
        else:
            emit('authentication_status', "Authentication failed.")
    except Exception as e:
        emit('authentication_status', f"Error during authentication: {str(e)}")

if __name__ == '__main__':
    main()
