import socket
import threading
import pickle
import time
import random
import struct

class PongServer:
    def __init__(self, host='localhost', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(2)
        print(f"🎮 Pong Server started on {host}:{port}")
        print(f"⏳ Waiting for players to connect...")

        self.game_state = {
            'ball': {'x': 400, 'y': 300, 'dx': 5, 'dy': 5, 'radius': 10},
            'paddle1': {'y': 250, 'score': 0},
            'paddle2': {'y': 250, 'score': 0},
            'width': 800,
            'height': 600,
            'paddle_width': 15,
            'paddle_height': 100,
            'status': 'waiting_connection',  # waiting_connection -> waiting_ready -> playing -> game_over
            'player1_ready': False,
            'player2_ready': False,
            'win_score': 5,  # Fixed win score
            'ball_speed_multiplier': 1.0,  # Increases with each hit
            'winner': None,
            'player1_play_again': False,
            'player2_play_again': False
        }

        self.clients = []
        self.running = True
        self.game_started = False
        
        # Speed settings
        self.BASE_SPEED = 5
        self.SPEED_INCREASE_PER_HIT = 0.05  # 5% increase per hit

    def handle_client(self, conn, player_id):
        print(f"✅ Player {player_id + 1} connected")
        conn.send(pickle.dumps(player_id))

        while self.running:
            try:
                # Receive 4-byte length header
                length_data = b''
                while len(length_data) < 4:
                    chunk = conn.recv(4 - len(length_data))
                    if not chunk:
                        break
                    length_data += chunk
                
                if len(length_data) < 4:
                    break
                
                msg_length = struct.unpack('!I', length_data)[0]
                
                # Receive the actual message
                data = b''
                while len(data) < msg_length:
                    chunk = conn.recv(min(8192, msg_length - len(data)))
                    if not chunk:
                        break
                    data += chunk
                
                if len(data) < msg_length:
                    break

                client_data = pickle.loads(data)
                
                if isinstance(client_data, dict):
                    paddle_y = client_data.get('paddle_y', 250)
                    ready_status = client_data.get('ready', False)
                    play_again = client_data.get('play_again', False)
                else:
                    paddle_y = client_data
                    ready_status = False
                    play_again = False
                
                paddle_y = max(0, min(paddle_y, self.game_state['height'] - self.game_state['paddle_height']))
                
                if player_id == 0:
                    self.game_state['paddle1']['y'] = paddle_y
                    self.game_state['player1_ready'] = ready_status
                    self.game_state['player1_play_again'] = play_again
                else:
                    self.game_state['paddle2']['y'] = paddle_y
                    self.game_state['player2_ready'] = ready_status
                    self.game_state['player2_play_again'] = play_again
                
                # Check transitions
                status = self.game_state['status']
                
                # Waiting ready -> Playing
                if (status == 'waiting_ready' and 
                    self.game_state['player1_ready'] and 
                    self.game_state['player2_ready']):
                    self.start_game()
                
                # Game over -> Restart
                if (status == 'game_over' and
                    self.game_state['player1_play_again'] and
                    self.game_state['player2_play_again']):
                    self.restart_game()
                    
            except Exception as e:
                import traceback
                print(f"❗ Error handling client {player_id + 1}: {e}")
                traceback.print_exc()
                break

        conn.close()
        if conn in self.clients:
            self.clients.remove(conn)
        print(f"❌ Player {player_id + 1} disconnected")
        self.game_started = False
        self.game_state['status'] = 'waiting_connection'

    def start_game(self):
        """Start the game after both players are ready"""
        print("🚀 Game starting!")
        self.game_state['status'] = 'playing'
        self.game_state['ball_speed_multiplier'] = 1.0
        self.reset_ball()

    def restart_game(self):
        """Restart the game"""
        print("🔄 Restarting game...")
        self.game_state['paddle1']['score'] = 0
        self.game_state['paddle2']['score'] = 0
        self.game_state['status'] = 'waiting_ready'
        self.game_state['player1_ready'] = False
        self.game_state['player2_ready'] = False
        self.game_state['player1_play_again'] = False
        self.game_state['player2_play_again'] = False
        self.game_state['winner'] = None
        self.game_state['ball_speed_multiplier'] = 1.0
        self.reset_ball()

    def check_winner(self):
        """Check if someone won"""
        p1_score = self.game_state['paddle1']['score']
        p2_score = self.game_state['paddle2']['score']
        win_score = self.game_state['win_score']
        
        if p1_score >= win_score:
            self.game_state['winner'] = 0
            self.game_state['status'] = 'game_over'
            print(f"🏆 Player 1 WINS! Final score: {p1_score} - {p2_score}")
            return True
        elif p2_score >= win_score:
            self.game_state['winner'] = 1
            self.game_state['status'] = 'game_over'
            print(f"🏆 Player 2 WINS! Final score: {p1_score} - {p2_score}")
            return True
        
        return False

    def update_game(self):
        while self.running:
            if len(self.clients) == 2 and self.game_state['status'] == 'playing':
                ball = self.game_state['ball']
                multiplier = self.game_state['ball_speed_multiplier']

                # Update ball position
                ball['x'] += ball['dx'] * multiplier
                ball['y'] += ball['dy'] * multiplier

                # Ball collision with top/bottom
                if ball['y'] <= ball['radius'] or ball['y'] >= self.game_state['height'] - ball['radius']:
                    ball['dy'] *= -1
                    ball['y'] = max(ball['radius'], min(ball['y'], self.game_state['height'] - ball['radius']))

                # Ball collision with paddles
                p1 = self.game_state['paddle1']
                p2 = self.game_state['paddle2']
                pw = self.game_state['paddle_width']
                ph = self.game_state['paddle_height']

                # Left paddle collision (Player 1)
                if (ball['x'] - ball['radius'] <= 10 + pw and
                    ball['dx'] < 0 and
                    p1['y'] <= ball['y'] <= p1['y'] + ph):
                    ball['dx'] = abs(ball['dx'])
                    ball['x'] = 10 + pw + ball['radius']
                    
                    # INCREASE SPEED ON HIT
                    self.game_state['ball_speed_multiplier'] += self.SPEED_INCREASE_PER_HIT
                    print(f"⚡ Speed increased to x{self.game_state['ball_speed_multiplier']:.2f}")
                    
                    # Add spin
                    hit_pos = (ball['y'] - p1['y']) / ph
                    ball['dy'] += (hit_pos - 0.5) * 3

                # Right paddle collision (Player 2)
                if (ball['x'] + ball['radius'] >= self.game_state['width'] - 10 - pw and
                    ball['dx'] > 0 and
                    p2['y'] <= ball['y'] <= p2['y'] + ph):
                    ball['dx'] = -abs(ball['dx'])
                    ball['x'] = self.game_state['width'] - 10 - pw - ball['radius']
                    
                    # INCREASE SPEED ON HIT
                    self.game_state['ball_speed_multiplier'] += self.SPEED_INCREASE_PER_HIT
                    print(f"⚡ Speed increased to x{self.game_state['ball_speed_multiplier']:.2f}")
                    
                    # Add spin
                    hit_pos = (ball['y'] - p2['y']) / ph
                    ball['dy'] += (hit_pos - 0.5) * 3

                # Cap base ball speed
                max_base_speed = 15
                if abs(ball['dx']) > max_base_speed:
                    ball['dx'] = max_base_speed if ball['dx'] > 0 else -max_base_speed
                if abs(ball['dy']) > max_base_speed:
                    ball['dy'] = max_base_speed if ball['dy'] > 0 else -max_base_speed

                # Scoring
                if ball['x'] <= 0:
                    p2['score'] += 1
                    print(f"🎯 Player 2 scores! Score: {p1['score']} - {p2['score']}")
                    
                    # Check winner
                    if not self.check_winner():
                        # RESET SPEED AFTER SCORE
                        self.game_state['ball_speed_multiplier'] = 1.0
                        print(f"🔄 Speed reset to x1.0")
                        self.reset_ball()
                        
                elif ball['x'] >= self.game_state['width']:
                    p1['score'] += 1
                    print(f"🎯 Player 1 scores! Score: {p1['score']} - {p2['score']}")
                    
                    # Check winner
                    if not self.check_winner():
                        # RESET SPEED AFTER SCORE
                        self.game_state['ball_speed_multiplier'] = 1.0
                        print(f"🔄 Speed reset to x1.0")
                        self.reset_ball()

            time.sleep(0.016)  # ~60 FPS

    def reset_ball(self):
        """Reset ball to center"""
        ball = self.game_state['ball']
        ball['x'] = 400
        ball['y'] = 300
        
        # Random direction
        direction = random.choice([-1, 1])
        ball['dx'] = self.BASE_SPEED * direction
        ball['dy'] = random.uniform(-3, 3)

    def broadcast_game_state(self):
        while self.running:
            if len(self.clients) == 2:
                if not self.game_started:
                    self.game_started = True
                    # Both players connected, go to waiting ready
                    self.game_state['status'] = 'waiting_ready'
                    print("👥 Both players connected! Press READY to start (First to 5)...")

                data = pickle.dumps(self.game_state)
                msg = struct.pack('!I', len(data)) + data  # Length prefix + data
                
                for client in self.clients[:]:
                    try:
                        client.sendall(msg)  # Use sendall to ensure complete send
                    except:
                        if client in self.clients:
                            self.clients.remove(client)

            time.sleep(0.016)  # ~60 FPS

    def start(self):
        threading.Thread(target=self.update_game, daemon=True).start()
        threading.Thread(target=self.broadcast_game_state, daemon=True).start()

        while self.running:
            if len(self.clients) < 2:
                conn, addr = self.server.accept()
                print(f"📡 Connection from {addr}")
                
                player_id = len(self.clients)
                self.clients.append(conn)
                
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, player_id),
                    daemon=True
                ).start()
                
                if len(self.clients) == 2:
                    print("✨ Both players connected!")
            else:
                time.sleep(0.1)
        
        print("\n⏹️  Shutting down server...")
        self.server.close()
    
if __name__ == "__main__":
    server = PongServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
        server.running = False