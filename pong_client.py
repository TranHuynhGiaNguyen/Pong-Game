import socket
import pickle
import threading
import pygame
import random
import math
import struct

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = 30
        self.color = color
        self.size = random.randint(2, 5)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(1, self.size * 0.95)
    
    def draw(self, screen):
        alpha = int((self.life / 30) * 255)
        if alpha > 0:
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
            screen.blit(s, (int(self.x - self.size), int(self.y - self.size)))

class PongClient:
    def __init__(self, host='localhost', port=5555):
        # 1. Khởi tạo các biến cơ bản
        self.player_id = 0
        self.game_state = None
        self.running = True
        self.paddle_y = 250
        self.paddle_speed = 10
        self.particles = []
        self.is_ready = False
        self.play_again = False  # For replay
        
        # 2. Khởi tạo Pygame
        pygame.init()

        # 3. Thiết lập kết nối Socket
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((host, port))
            self.player_id = pickle.loads(self.client.recv(1024))
        except Exception as e:
            print(f"Lỗi kết nối: {e}")
            self.running = False

        # 4. Thiết lập hiển thị
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(f"Pong - Player {self.player_id + 1}")

        # Colors
        self.BG_COLOR = (10, 15, 30)
        self.PRIMARY = (0, 255, 255)
        self.SECONDARY = (255, 50, 255)
        self.WHITE = (255, 255, 255)
        self.PADDLE1_COLOR = (0, 200, 255)
        self.PADDLE2_COLOR = (255, 100, 200)
        self.BALL_COLOR = (255, 255, 100)
        self.LINE_COLOR = (50, 70, 100)
        self.GREEN = (0, 255, 100)
        self.ORANGE = (255, 150, 0)
        self.RED = (255, 50, 50)

        # Fonts
        self.font_large = pygame.font.Font(None, 120)
        self.font_medium = pygame.font.Font(None, 74)
        self.font_small = pygame.font.Font(None, 36)
        self.font_tiny = pygame.font.Font(None, 24)

    def receive_game_state(self):
        """Receive game state with proper message framing"""
        while self.running:
            try:
                # First, receive 4-byte length header
                length_data = b''
                while len(length_data) < 4:
                    chunk = self.client.recv(4 - len(length_data))
                    if not chunk:
                        return  # Connection closed
                    length_data += chunk
                
                msg_length = struct.unpack('!I', length_data)[0]
                
                # Now receive the actual message
                data = b''
                while len(data) < msg_length:
                    chunk = self.client.recv(min(8192, msg_length - len(data)))
                    if not chunk:
                        return  # Connection closed
                    data += chunk
                
                # Unpickle the complete message
                new_state = pickle.loads(data)
                
                # Detect collision for particle effects
                if (self.game_state and new_state and 
                    'ball' in self.game_state and 'ball' in new_state):
                    old_ball = self.game_state['ball']
                    new_ball = new_state['ball']
                    if (abs(old_ball.get('dx', 0)) != abs(new_ball.get('dx', 0)) or 
                        abs(old_ball.get('dy', 0)) != abs(new_ball.get('dy', 0))):
                        self.create_particles(new_ball.get('x', 400), new_ball.get('y', 300))
                
                self.game_state = new_state
                    
            except Exception as e:
                print(f"❌ Error receiving game state: {e}")
                break

    def send_game_data(self):
        """Send paddle position, ready state, and play_again with message framing"""
        try:
            data = {
                'paddle_y': self.paddle_y,
                'ready': self.is_ready,
                'play_again': self.play_again
            }
            msg = pickle.dumps(data)
            # Send length prefix + message
            self.client.send(struct.pack('!I', len(msg)) + msg)
        except:
            pass

    def create_particles(self, x, y):
        color = self.BALL_COLOR
        for _ in range(15):
            self.particles.append(Particle(x, y, color))

    def draw_gradient_rect(self, x, y, w, h, color1, color2):
        for i in range(h):
            ratio = i / h
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (x, y + i), (x + w, y + i))

    def draw_glow_circle(self, x, y, radius, color):
        for i in range(3):
            scale = 1 + i * 0.3
            alpha = max(0, 100 - i * 30)
            s = pygame.Surface((int(radius * scale * 2) + 10, int(radius * scale * 2) + 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha), (int(radius * scale) + 5, int(radius * scale) + 5), int(radius * scale))
            self.screen.blit(s, (int(x - radius * scale - 5), int(y - radius * scale - 5)))
        pygame.draw.circle(self.screen, color, (int(x), int(y)), radius)

    def draw_paddle_with_effects(self, x, y, width, height, color):
        shadow_surface = pygame.Surface((width + 10, height + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surface, (*color, 50), (5, 5, width, height), border_radius=8)
        self.screen.blit(shadow_surface, (x - 5, y - 5))
        
        darker_color = tuple(max(0, c - 50) for c in color)
        self.draw_gradient_rect(x, y, width, height, color, darker_color)
        
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, width, height), 2, border_radius=8)

    def draw_center_line(self):
        for i in range(0, self.height, 30):
            alpha = int(150 + 100 * math.sin(pygame.time.get_ticks() / 500 + i / 50))
            s = pygame.Surface((6, 20), pygame.SRCALPHA)
            pygame.draw.rect(s, (*self.LINE_COLOR, alpha), (0, 0, 6, 20))
            self.screen.blit(s, (self.width // 2 - 3, i))

    def draw_score(self, score, x, y, color):
        for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
            glow_text = self.font_large.render(str(score), True, (*color, 100))
            glow_rect = glow_text.get_rect(center=(x + offset[0], y + offset[1]))
            self.screen.blit(glow_text, glow_rect)
        
        text = self.font_large.render(str(score), True, self.WHITE)
        text_rect = text.get_rect(center=(x, y))
        self.screen.blit(text, text_rect)

    def draw_button(self, x, y, w, h, text, color, hover=False):
        """Draw a button with hover effect"""
        alpha = 150 if hover else 100
        bg_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (*color, alpha), (0, 0, w, h), border_radius=10)
        pygame.draw.rect(bg_surface, color, (0, 0, w, h), 3, border_radius=10)
        self.screen.blit(bg_surface, (x, y))
        
        # Choose font size based on text length
        if len(text) > 15:
            button_text = self.font_tiny.render(text, True, self.WHITE)
        else:
            button_text = self.font_small.render(text, True, self.WHITE)
        
        text_rect = button_text.get_rect(center=(x + w // 2, y + h // 2))
        self.screen.blit(button_text, text_rect)
        
        return pygame.Rect(x, y, w, h)

    def draw(self):
        # Background gradient
        for i in range(self.height):
            ratio = i / self.height
            r = int(self.BG_COLOR[0] * (1 - ratio) + 20 * ratio)
            g = int(self.BG_COLOR[1] * (1 - ratio) + 25 * ratio)
            b = int(self.BG_COLOR[2] * (1 - ratio) + 40 * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, i), (self.width, i))

        if self.game_state:
            game_status = self.game_state.get('status', 'waiting')
            
            # Draw center line
            self.draw_center_line()

            pw = self.game_state['paddle_width']
            ph = self.game_state['paddle_height']

            # Draw paddles
            self.draw_paddle_with_effects(10, self.game_state['paddle1']['y'], pw, ph, self.PADDLE1_COLOR)
            self.draw_paddle_with_effects(self.width - pw - 10, self.game_state['paddle2']['y'], pw, ph, self.PADDLE2_COLOR)

            # Draw ball (if playing)
            if game_status == 'playing':
                ball = self.game_state.get('ball', {})
                if ball:
                    ball_x = ball.get('x', 400)
                    ball_y = ball.get('y', 300)
                    ball_radius = ball.get('radius', 10)
                    self.draw_glow_circle(ball_x, ball_y, ball_radius, self.BALL_COLOR)

            # Draw particles
            for particle in self.particles[:]:
                particle.update()
                particle.draw(self.screen)
                if particle.life <= 0:
                    self.particles.remove(particle)

            # Draw scores
            self.draw_score(self.game_state['paddle1']['score'], self.width // 4, 80, self.PADDLE1_COLOR)
            self.draw_score(self.game_state['paddle2']['score'], 3 * self.width // 4, 80, self.PADDLE2_COLOR)

            # Player indicator
            player_text = "YOU"
            indicator_color = self.PADDLE1_COLOR if self.player_id == 0 else self.PADDLE2_COLOR
            x_pos = 20 if self.player_id == 0 else self.width - 100
            
            pulse = int(20 + 10 * math.sin(pygame.time.get_ticks() / 300))
            bg_surface = pygame.Surface((80, 35), pygame.SRCALPHA)
            pygame.draw.rect(bg_surface, (*indicator_color, pulse), (0, 0, 80, 35), border_radius=5)
            self.screen.blit(bg_surface, (x_pos, 15))
            
            label = self.font_small.render(player_text, True, self.WHITE)
            self.screen.blit(label, (x_pos + 12, 20))

            # === WAITING READY ===
            if game_status == 'waiting_ready':
                p1_ready = self.game_state.get('player1_ready', False)
                p2_ready = self.game_state.get('player2_ready', False)
                
                win_score = self.game_state.get('win_score', 5)
                info = self.font_large.render(f"First to {win_score}!", True, self.PRIMARY)
                info_rect = info.get_rect(center=(self.width // 2, 200))
                self.screen.blit(info, info_rect)
                
                # Ready status boxes
                box_y = 280
                box_width = 200
                box_height = 60
                
                # Player 1 status
                p1_box = pygame.Rect(150, box_y, box_width, box_height)
                p1_color = self.GREEN if p1_ready else self.ORANGE
                p1_alpha = 100 if p1_ready else 50
                
                bg1 = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
                pygame.draw.rect(bg1, (*p1_color, p1_alpha), (0, 0, box_width, box_height), border_radius=10)
                pygame.draw.rect(bg1, p1_color, (0, 0, box_width, box_height), 3, border_radius=10)
                self.screen.blit(bg1, (p1_box.x, p1_box.y))
                
                p1_label = self.font_tiny.render("PLAYER 1", True, self.WHITE)
                p1_label_rect = p1_label.get_rect(center=(p1_box.centerx, p1_box.centery - 12))
                self.screen.blit(p1_label, p1_label_rect)
                
                p1_status = "READY ✓" if p1_ready else "NOT READY"
                p1_status_surf = self.font_small.render(p1_status, True, p1_color)
                p1_status_rect = p1_status_surf.get_rect(center=(p1_box.centerx, p1_box.centery + 12))
                self.screen.blit(p1_status_surf, p1_status_rect)
                
                # Player 2 status
                p2_box = pygame.Rect(450, box_y, box_width, box_height)
                p2_color = self.GREEN if p2_ready else self.ORANGE
                p2_alpha = 100 if p2_ready else 50
                
                bg2 = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
                pygame.draw.rect(bg2, (*p2_color, p2_alpha), (0, 0, box_width, box_height), border_radius=10)
                pygame.draw.rect(bg2, p2_color, (0, 0, box_width, box_height), 3, border_radius=10)
                self.screen.blit(bg2, (p2_box.x, p2_box.y))
                
                p2_label = self.font_tiny.render("PLAYER 2", True, self.WHITE)
                p2_label_rect = p2_label.get_rect(center=(p2_box.centerx, p2_box.centery - 12))
                self.screen.blit(p2_label, p2_label_rect)
                
                p2_status = "READY ✓" if p2_ready else "NOT READY"
                p2_status_surf = self.font_small.render(p2_status, True, p2_color)
                p2_status_rect = p2_status_surf.get_rect(center=(p2_box.centerx, p2_box.centery + 12))
                self.screen.blit(p2_status_surf, p2_status_rect)
                
                # Ready button for current player
                mouse_pos = pygame.mouse.get_pos()
                ready_btn = pygame.Rect(self.width // 2 - 120, 380, 240, 70)
                hover = ready_btn.collidepoint(mouse_pos)
                
                btn_color = self.GREEN if self.is_ready else self.PRIMARY
                btn_text = "READY ✓" if self.is_ready else "CLICK TO READY"
                
                self.draw_button(ready_btn.x, ready_btn.y, ready_btn.w, ready_btn.h, btn_text, btn_color, hover)
                
                # Instruction
                instruction = "Both players must be ready to start"
                instruction_surf = self.font_tiny.render(instruction, True, self.LINE_COLOR)
                instruction_rect = instruction_surf.get_rect(center=(self.width // 2, 480))
                self.screen.blit(instruction_surf, instruction_rect)

            # === PLAYING ===
            elif game_status == 'playing':
                speed = self.game_state.get('ball_speed_multiplier', 1.0)
                speed_text = f"Speed: x{speed:.2f}"
                speed_surface = self.font_tiny.render(speed_text, True, self.BALL_COLOR)
                self.screen.blit(speed_surface, (self.width // 2 - 40, 15))
                
                win_score = self.game_state.get('win_score', 5)
                target = self.font_tiny.render(f"Target: {win_score}", True, self.WHITE)
                self.screen.blit(target, (self.width // 2 - 40, 40))

            # === GAME OVER ===
            elif game_status == 'game_over':
                winner = self.game_state.get('winner', 0)
                winner_text = f"PLAYER {winner + 1} WINS!"
                winner_color = self.PADDLE1_COLOR if winner == 0 else self.PADDLE2_COLOR
                
                # Winner announcement with glow
                for offset in [(3, 3), (-3, -3), (3, -3), (-3, 3)]:
                    glow = self.font_large.render(winner_text, True, (*winner_color, 80))
                    glow_rect = glow.get_rect(center=(self.width // 2 + offset[0], 150 + offset[1]))
                    self.screen.blit(glow, glow_rect)
                
                title = self.font_large.render(winner_text, True, winner_color)
                title_rect = title.get_rect(center=(self.width // 2, 150))
                self.screen.blit(title, title_rect)
                
                # Final score
                final_score = f"{self.game_state['paddle1']['score']} - {self.game_state['paddle2']['score']}"
                score_surf = self.font_medium.render(final_score, True, self.WHITE)
                score_rect = score_surf.get_rect(center=(self.width // 2, 240))
                self.screen.blit(score_surf, score_rect)
                
                # Play again status
                p1_again = self.game_state.get('player1_play_again', False)
                p2_again = self.game_state.get('player2_play_again', False)
                
                question = "Play again?"
                question_surf = self.font_medium.render(question, True, self.WHITE)
                question_rect = question_surf.get_rect(center=(self.width // 2, 320))
                self.screen.blit(question_surf, question_rect)
                
                # Status boxes
                box_y = 380
                box_width = 180
                box_height = 50
                
                # Player 1 status
                p1_box = pygame.Rect(170, box_y, box_width, box_height)
                p1_color = self.GREEN if p1_again else self.ORANGE
                p1_alpha = 100 if p1_again else 50
                
                bg1 = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
                pygame.draw.rect(bg1, (*p1_color, p1_alpha), (0, 0, box_width, box_height), border_radius=8)
                pygame.draw.rect(bg1, p1_color, (0, 0, box_width, box_height), 3, border_radius=8)
                self.screen.blit(bg1, (p1_box.x, p1_box.y))
                
                p1_text = "P1: YES ✓" if p1_again else "P1: NO"
                p1_surf = self.font_small.render(p1_text, True, p1_color)
                p1_rect = p1_surf.get_rect(center=(p1_box.centerx, p1_box.centery))
                self.screen.blit(p1_surf, p1_rect)
                
                # Player 2 status
                p2_box = pygame.Rect(450, box_y, box_width, box_height)
                p2_color = self.GREEN if p2_again else self.ORANGE
                p2_alpha = 100 if p2_again else 50
                
                bg2 = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
                pygame.draw.rect(bg2, (*p2_color, p2_alpha), (0, 0, box_width, box_height), border_radius=8)
                pygame.draw.rect(bg2, p2_color, (0, 0, box_width, box_height), 3, border_radius=8)
                self.screen.blit(bg2, (p2_box.x, p2_box.y))
                
                p2_text = "P2: YES ✓" if p2_again else "P2: NO"
                p2_surf = self.font_small.render(p2_text, True, p2_color)
                p2_rect = p2_surf.get_rect(center=(p2_box.centerx, p2_box.centery))
                self.screen.blit(p2_surf, p2_rect)
                
                # Play again button
                mouse_pos = pygame.mouse.get_pos()
                yes_btn = pygame.Rect(self.width // 2 - 120, 460, 240, 60)
                hover = yes_btn.collidepoint(mouse_pos)
                
                btn_color = self.GREEN if self.play_again else self.PRIMARY
                btn_text = "YES, PLAY AGAIN ✓" if self.play_again else "CLICK FOR YES"
                
                self.draw_button(yes_btn.x, yes_btn.y, yes_btn.w, yes_btn.h, btn_text, btn_color, hover)
                
                # Instruction
                instruction = "Both players must click YES to restart"
                instruction_surf = self.font_tiny.render(instruction, True, self.LINE_COLOR)
                instruction_rect = instruction_surf.get_rect(center=(self.width // 2, 545))
                self.screen.blit(instruction_surf, instruction_rect)

        else:
            # Waiting for connection
            pulse = math.sin(pygame.time.get_ticks() / 500)
            
            title = self.font_large.render("PONG", True, self.PRIMARY)
            title_rect = title.get_rect(center=(self.width // 2, self.height // 2 - 80))
            self.screen.blit(title, title_rect)
            
            wait_text = "Waiting for opponent..."
            text = self.font_medium.render(wait_text, True, self.WHITE)
            text_rect = text.get_rect(center=(self.width // 2, self.height // 2 + 20))
            self.screen.blit(text, text_rect)
            
            dots = "." * (int(pygame.time.get_ticks() / 500) % 4)
            dots_text = self.font_medium.render(dots, True, self.SECONDARY)
            dots_rect = dots_text.get_rect(topleft=(text_rect.right + 5, text_rect.top))
            self.screen.blit(dots_text, dots_rect)
            
            info = self.font_small.render(f"You are Player {self.player_id + 1}", True, self.LINE_COLOR)
            info_rect = info.get_rect(center=(self.width // 2, self.height // 2 + 100))
            self.screen.blit(info, info_rect)

        pygame.display.flip()

    def run(self):
        threading.Thread(target=self.receive_game_state, daemon=True).start()
        clock = pygame.time.Clock()
        
        print(f"🎮 Client started! You are Player {self.player_id + 1}")
        print(f"📺 Window opened. Waiting for game state...")

        while self.running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    
                    # Mouse click handling
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if self.game_state:
                            status = self.game_state.get('status', '')
                            mouse_pos = pygame.mouse.get_pos()
                            print(f"🖱️ Mouse clicked at {mouse_pos}, status: {status}")
                            
                            # Waiting ready screen
                            if status == 'waiting_ready':
                                ready_btn = pygame.Rect(self.width // 2 - 120, 380, 240, 70)
                                if ready_btn.collidepoint(mouse_pos):
                                    self.is_ready = not self.is_ready
                            
                            # Game over screen
                            elif status == 'game_over':
                                yes_btn = pygame.Rect(self.width // 2 - 120, 460, 240, 60)
                                if yes_btn.collidepoint(mouse_pos):
                                    self.play_again = not self.play_again
                    
                    elif event.type == pygame.KEYDOWN:
                        if self.game_state:
                            status = self.game_state.get('status', '')
                        
                        # SPACE as alternative to mouse click
                        if event.key == pygame.K_SPACE:
                            if status == 'waiting_ready':
                                self.is_ready = not self.is_ready
                            elif status == 'game_over':
                                self.play_again = not self.play_again

                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP] and self.paddle_y > 0:
                    self.paddle_y -= self.paddle_speed
                if keys[pygame.K_DOWN] and self.paddle_y < self.height - 100:
                    self.paddle_y += self.paddle_speed

                self.send_game_data()
                self.draw()
                clock.tick(60)
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                import traceback
                traceback.print_exc()
            
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                import traceback
                traceback.print_exc()

        self.client.close()
        pygame.quit()
        print("👋 Client closed")

if __name__ == "__main__":
    client = PongClient()
    client.run()