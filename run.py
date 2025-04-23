from app import create_app, socketio, db
from app.models import User, Session, Message, Review
import sys
import socket
import os

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Session': Session,
        'Message': Message,
        'Review': Review
    }

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    host = '0.0.0.0'  # Allow connections from any IP

    # Get local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    # Check if SSL certificate exists
    ssl_context = None
    cert_path = os.path.join(os.path.dirname(__file__), 'ssl', 'cert.pem')
    key_path = os.path.join(os.path.dirname(__file__), 'ssl', 'key.pem')

    if os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context = (cert_path, key_path)
        print(f"\nRunning on secure network URL: https://{local_ip}:{port}/")
        print("You can access this URL from other devices on the same network.")
        print("Note: You may need to accept the self-signed certificate warning in your browser.\n")
    else:
        print(f"\nRunning on network URL: http://{local_ip}:{port}/")
        print("You can access this URL from other devices on the same network.")
        print("Warning: For better WebRTC compatibility, consider using HTTPS.\n")

    socketio.run(app, debug=True, host=host, port=port, ssl_context=ssl_context, allow_unsafe_werkzeug=True)
