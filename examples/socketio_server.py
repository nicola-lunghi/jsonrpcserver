from flask import Flask
from flask_socketio import SocketIO
from jsonrpcserver import Methods, dispatch

app = Flask(__name__)
socketio = SocketIO(app)
methods = Methods()

@methods.add
def ping():
    return 'pong'

@socketio.on('message')
def handle_message(request):
    return dispatch(methods, request)

if __name__ == '__main__':
    socketio.run(app, port=5000)
