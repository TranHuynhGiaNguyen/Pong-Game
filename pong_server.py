import socket
import threading
import pickle
import time
class PongServer:
    def __init__(self, host='localhost', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(2)
        print(f"Server started on {host}:{port}")

        self.game_state = {
            'ball': {'x': 400, 'y': 300, 'dx': 4, 'dy': 4, 'radius': 10},
            'paddle1': {'y': 250, 'score': 0},
            'paddle2': {'y': 250, 'score': 0},
            'width': 800,
            'height': 600,
            'paddle_width': 15,
            'paddle_height': 100
        }

        self.clients = []
        self.running = True
        self.game_started = False
