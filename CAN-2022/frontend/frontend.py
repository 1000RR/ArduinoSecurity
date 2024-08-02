import os
from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import subprocess
import ssl


# Set the directory containing your static files (HTML and images)
#static_directory = os.path.join(os.path.dirname(__file__), './')
thisDir = os.path.dirname(os.path.realpath(__file__))
static_directory = thisDir + '/content'
serverKeysDir = "../server-keys/"
print(static_directory)

# Define the IP address and port for the server
hostname = socket.gethostname()
host = socket.gethostbyname(hostname) if hostname else "127.0.0.1"
port = 443

if (host == '127.0.0.1'):
    # Run the ifconfig command and capture its output
    try:
        output = subprocess.check_output(["ifconfig", "eth0"])
        output = output.decode("utf-8")
    except subprocess.CalledProcessError as e:
        print(f"Error running ifconfig: {e}")
        output = ""

    # Search for the IP address in the output (assuming a typical Linux/macOS format)
    import re

    # Define a regular expression pattern to match IP addresses
    ip_pattern = r'inet (\d+\.\d+\.\d+\.\d+)'

    # Use re.findall to find all IP addresses in the output
    ip_addresses = re.findall(ip_pattern, output)

    # Filter out loopback addresses (127.0.0.1)
    ip_addresses = [ip for ip in ip_addresses if ip != '127.0.0.1']

    # Print the IP addresses (if any)
    if ip_addresses:
        host = ip_addresses[0]
    else:
        print(f"No IP addresses found. Using the default {host}")

print(f">>hosting on {host}:{port}")

allowed_extensions = {'.html', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.json'}
allowed_paths = {'/'}

# Create a custom request handler to modify the behavior
class CustomRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', 'bobik.lan, bobik, bobikwifi, bobikwifi.lan, 192.168.0.0/17') #the protocol is SSL-dependent; mask /16 is 192.168.*.*; mask /17 is 192.168.0.0-192.168.127.255
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        SimpleHTTPRequestHandler.end_headers(self)
    
    def do_GET(self):
        if not self.is_valid_path():
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
        elif self.path == '/':
            # Serve the main HTML file
            self.path = '/content/main.html'
        else:
            self.path = '/content/' + self.path
        return super().do_GET()

    def is_valid_path(self):
        # Check if the requested file has an allowed extension
        file_extension = os.path.splitext(self.path)[1].lower()
        return (file_extension in allowed_extensions) or (self.path in allowed_paths)

# Create the HTTP server
try:
    # Load the SSL certificate and private key
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=serverKeysDir+'/server-cert.pem', keyfile=serverKeysDir+'/server-key.pem')

    # Create the HTTP server with SSL context
    server = HTTPServer((host, port), CustomRequestHandler)
    server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    print(f'Static server started at https://{host}:{port}')
    server.serve_forever()
except KeyboardInterrupt:
    print('Server stopped')
    server.socket.close()