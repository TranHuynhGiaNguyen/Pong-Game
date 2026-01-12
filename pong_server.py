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

    def handle_client(self, conn, player_id):
        print(f"Player {player_id} connected")
        conn.send(pickle.dumps(player_id))

        while self.running:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                paddle_y = pickle.loads(data)
                if player_id == 0:
                    self.game_state['paddle1']['y'] = paddle_y
                else:
                    self.game_state['paddle2']['y'] = paddle_y
            except:
                break

        conn.close()
        if conn in self.clients:
            self.clients.remove(conn)
        print(f"Player {player_id} disconnected")
        
    def update_game(self):
        while self.running:
            if len(self.clients) == 2 and self.game_started:
                ball = self.game_state['ball']

                # Update ball position
                ball['x'] += ball['dx']
                ball['y'] += ball['dy']

                # Ball collision with top/bottom
                if ball['y'] <= ball['radius'] or ball['y'] >= self.game_state['height'] - ball['radius']:
                    ball['dy'] *= -1

                # Ball collision with paddles
                p1 = self.game_state['paddle1']
                p2 = self.game_state['paddle2']
                pw = self.game_state['paddle_width']
                ph = self.game_state['paddle_height']

                # Left paddle collision
                if (ball['x'] - ball['radius'] <= pw and
                        p1['y'] <= ball['y'] <= p1['y'] + ph):
                    ball['dx'] = abs(ball['dx']) * 1.05  # Speed increase
                    # Add spin based on where ball hits paddle
                    hit_pos = (ball['y'] - p1['y']) / ph
                    ball['dy'] += (hit_pos - 0.5) * 2

                # Right paddle collision
                if (ball['x'] + ball['radius'] >= self.game_state['width'] - pw and
                        p2['y'] <= ball['y'] <= p2['y'] + ph):
                    ball['dx'] = -abs(ball['dx']) * 1.05  # Speed increase
                    # Add spin based on where ball hits paddle
                    hit_pos = (ball['y'] - p2['y']) / ph
                    ball['dy'] += (hit_pos - 0.5) * 2

                # Cap ball speed
                max_speed = 15
                if abs(ball['dx']) > max_speed:
                    ball['dx'] = max_speed if ball['dx'] > 0 else -max_speed
                if abs(ball['dy']) > max_speed:
                    ball['dy'] = max_speed if ball['dy'] > 0 else -max_speed

                # Scoring
                if ball['x'] <= 0:
                    p2['score'] += 1
                    self.reset_ball()
                elif ball['x'] >= self.game_state['width']:
                    p1['score'] += 1
                    self.reset_ball()

            time.sleep(0.016)  # ~60 FPSdef reset_ball(self):

    def reset_ball(self):
        ball = self.game_state['ball']
        ball['x'] = 400
        ball['y'] = 300
        ball['dx'] = 4 if ball['dx'] > 0 else -4
        ball['dy'] = 4
    def broadcast_game_state(self):
        while self.running:
            if len(self.clients) == 2:
                if not self.game_started:
                    self.game_started = True
                    print("Game started!")

                data = pickle.dumps(self.game_state)
                for client in self.clients[:]:
                    try:
                        client.send(data)
                    except:
                        self.clients.remove(client)

            time.sleep(0.016)

    def start(self):
        threading.Thread(target=self.update_game, daemon=True).start()
        threading.Thread(target=self.broadcast_game_state, daemon=True).start()

        player_id = 0
        while self.running and len(self.clients) < 2:
            conn, _ = self.server.accept()
            self.clients.append(conn)
            threading.Thread(
                target=self.handle_client,
                args=(conn, player_id),
                daemon=True
            ).start()
            player_id += 1

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            self.server.close()
    
if __name__ == "__main__":
    server = PongServer()
    server.start() 