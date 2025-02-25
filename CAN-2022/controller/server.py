import threading
import alarm
import json
import os
from queue import Queue
import ssl
from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from uuid import uuid4


# Create a queue for communication between main program and daemon thread
webserver_message_queue = Queue()
responseQueues = {}
# Set up the Flask web API
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=["https://192.168.2.100:5020", "https://192.168.2.100:5010", "http://192.168.2.100:3000", "https://bobik.lan","https://192.168.99.5"], ping_timeout=11, ping_interval=5, async_mode="threading")
thread = None
thread_lock = threading.Lock()
new_client_exists = False
alarmQueueMessages = {}
thisDir = os.path.dirname(os.path.abspath(__file__))
serverKeysDir = thisDir + "/server-keys"
print(thisDir)

def main():
    global responseQueues
    global webserver_message_queue
    global thisDir

    print("Main program started.")

    # Create a thread for the raspi alarm python script and pass the global variable and message queue
    alarm_thread = threading.Thread(target=alarm.run, args=(webserver_message_queue, ), daemon=True)
    alarm_thread.start()

    @app.route('/status', methods=['GET'])
    def get_status():
        status = {"status": "ok"}
        return jsonify(status)

    @app.after_request
    def add_no_cache_header(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response


    @socketio.on('connect')
    def handle_connect():
        #authenticate()
        global new_client_exists

        new_client_exists = True
        print('Client connected')
        global thread
        with thread_lock:
            if thread is None:
                thread = socketio.start_background_task(update_status_thread)

    @socketio.on('disconnect')
    def disconnect():
        global client_count
        client_count -= 1
        if (client_count == 0):
            thread.kill()
        print('Disconnected')

    @socketio.on('getPastEvents')
    def getPastEvents(message):
        global responseQueues

        callUUID = generateUUID()
        responseQueues[callUUID] = Queue()
        messageToSend = {"request":"GET-PAST-EVENTS", "uuid": callUUID, "responseQueue": responseQueues[callUUID]}
        webserver_message_queue.put(messageToSend)
        response = responseQueues[callUUID].get(True, 5)["response"]
        del responseQueues[callUUID]
        emit('postPastEvents', {'message': json.loads(response)})

    @socketio.on('getStatus')
    def getStatus(message):
        sendAlarmStatus("something")

    @socketio.on('arm')
    def arm(message):
        print('>>>>ARMING')
        callUUID = generateUUID()
        messageToSend = {"request":"ENABLE-ALARM", "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('disarm')
    def disarm(message):
        print('>>>DISARMING')
        callUUID = generateUUID()
        messageToSend = {"request":"DISABLE-ALARM", "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('alarmSoundOn')
    def arm(message):
        callUUID = generateUUID()
        messageToSend = {"request":"FORCE-ALARM-SOUND-ON", "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('clearOldData')
    def arm(message):
        callUUID = generateUUID()
        messageToSend = {"request":"CLEAR-OLD-DATA", "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('checkPhones')
    def arm(message):
        callUUID = generateUUID()
        messageToSend = {"request":"ALERT-CHECK-PHONES", "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('toggleGarageDoorState')
    def disarm(message):
        callUUID = generateUUID()
        messageToSend = {"request":"TOGGLE-GARAGE-DOOR-STATE", "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('cansendrepeatedly')
    def cansendrepeatedly(message):
        callUUID = generateUUID()
        messageToSend = {"request":"CAN-REPEATEDLY-SEND-" + message['message'], "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('cansendsingle')
    def cansendsingle(message):
        callUUID = generateUUID()
        messageToSend = {"request":"CAN-SINGLE-SEND-" + message['message'], "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('canstopsending')
    def canstopsending(message):
        callUUID = generateUUID()
        messageToSend = {"request":"CAN-STOP-SENDING", "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on('getAlarmProfiles')
    def getProfiles(message):
        global responseQueues

        callUUID = generateUUID()
        responseQueues[callUUID] = Queue()
        messageToSend = {"request":"GET-ALARM-PROFILES", "uuid": callUUID, "responseQueue": responseQueues[callUUID] }
        webserver_message_queue.put(messageToSend)
        response = responseQueues[callUUID].get(True, 5)["response"]
        del responseQueues[callUUID]
        emit('postAlarmProfiles', {'message': json.loads(response)})

    @socketio.on('setAlarmProfile')
    def setAlarmProfile(message):
        callUUID = generateUUID()
        messageToSend = {"request":"SET-ALARM-PROFILE-" + str(message['message']), "uuid": callUUID}
        webserver_message_queue.put(messageToSend)

    @socketio.on_error()
    def error(e):
        print('Error', e)
       
    sslContext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sslContext.load_cert_chain(certfile=serverKeysDir+'/server-cert.pem', keyfile=serverKeysDir+'/server-key.pem')

    # Run the Flask app
    #socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True)
    socketio.run(app, host='0.0.0.0', port=8080, ssl_context=sslContext, allow_unsafe_werkzeug=True)

def update_status_thread():
    last_status_str = 0
    while True:    
        #print(f"before update last_client_count {last_client_count}")
        last_status_str = sendAlarmStatus(last_status_str)
        #print(f"updated last_client_count {last_client_count}")
        socketio.sleep(1)

def getClientCount():
    global client_count
    #print('RETURNING CLIENT COUNT ' + str(client_count))
    return client_count

def generateUUID():
    return uuid4().hex

def sendAlarmStatus (last_status_str):
    global new_client_exists
    global responseQueues

    callUUID = generateUUID()
    responseQueues[callUUID] = Queue()
    messageToSend = {"request":"ALARM-STATUS", "uuid": callUUID, "responseQueue": responseQueues[callUUID] }
    webserver_message_queue.put(messageToSend)
    response = responseQueues[callUUID].get(True, 5)["response"]
    del responseQueues[callUUID]

    if (response != last_status_str or new_client_exists):
        print("Sending status to connected clients")
        socketio.emit('postStatus', {'message': json.loads(response)})
        new_client_exists = False


    return response

if __name__ == '__main__':
    main()
