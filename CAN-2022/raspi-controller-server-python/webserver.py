import threading
import time
import alarm
import json
from queue import Queue

# Define a global variable
global_var = "This is a global variable from main_program"

# Create a queue for communication between main program and daemon thread
webserver_message_queue = Queue()
alarm_message_queue = Queue()

def main():
    global alarm_message_queue
    global webserver_message_queue

    print("Main program started.")

    # Create a thread for the raspi alarm python script and pass the global variable and message queue
    alarm_thread = threading.Thread(target=alarm.run, args=(webserver_message_queue,alarm_message_queue), daemon=True)
    alarm_thread.start()

    # Set up the Flask web API
    from flask import Flask, request, jsonify
    app = Flask(__name__)

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

    # Run the Flask app
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    main()