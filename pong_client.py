import socket
import pickle
import threading
import pygame

class PongClient:
    def __init__(self, host='localhost', port=5555):
        # 1. Khởi tạo các biến cơ bản trước để tránh lỗi "AttributeError"
        self.player_id = 0
        self.game_state = None
        self.running = True
        self.paddle_y = 250
        self.paddle_speed = 10
        
        # 2. Khởi tạo Pygame
        pygame.init()

        # 3. Thiết lập kết nối Socket
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((host, port))
            # Nhận ID từ server (Giả sử server gửi ID đầu tiên)
            self.player_id = pickle.loads(self.client.recv(1024))
        except Exception as e:
            print(f"Lỗi kết nối: {e}")
            self.running = False

        # 4. Thiết lập hiển thị
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        # Bây giờ self.player_id đã tồn tại, không còn bị lỗi dòng dưới:
        pygame.display.set_caption(f"Pong - Player {self.player_id + 1}")

        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)

        # Font
        self.font = pygame.font.Font(None, 74)
        self.small_font = pygame.font.Font(None, 36)

    # Thêm hàm nhận dữ liệu để khớp với lệnh gọi trong run()
    def receive_game_state(self):
        while self.running:
            try:
                data = self.client.recv(4096)
                if data:
                    self.game_state = pickle.loads(data)
            except:
                break

    # Thêm hàm gửi dữ liệu để khớp với lệnh gọi trong run()
    def send_paddle_position(self):
        try:
            # Gửi tọa độ Y của mình lên cho Server
            self.client.send(pickle.dumps(self.paddle_y))
        except:
            pass

    def draw(self):
        self.screen.fill(self.BLACK)

        if self.game_state:
            for i in range(0, self.height, 20):
                pygame.draw.rect(self.screen, self.WHITE, (self.width//2-2, i, 4, 10))

            pw = self.game_state['paddle_width']
            ph = self.game_state['paddle_height']

            pygame.draw.rect(self.screen, self.WHITE, (0, self.game_state['paddle1']['y'], pw, ph))
            pygame.draw.rect(self.screen, self.WHITE, (self.width-pw, self.game_state['paddle2']['y'], pw, ph))

            ball = self.game_state['ball']
            pygame.draw.circle(self.screen, self.WHITE, (int(ball['x']), int(ball['y'])), ball['radius'])

            s1 = self.font.render(str(self.game_state['paddle1']['score']), True, self.WHITE)
            s2 = self.font.render(str(self.game_state['paddle2']['score']), True, self.WHITE)
            self.screen.blit(s1, (self.width//4, 50))
            self.screen.blit(s2, (3*self.width//4, 50))

            text = "You (Left)" if self.player_id == 0 else "You (Right)"
            label = self.small_font.render(text, True, self.WHITE)
            self.screen.blit(label, (10 if self.player_id == 0 else self.width-150, 10))
        else:
            text = self.font.render("Waiting for opponent...", True, self.WHITE)
            self.screen.blit(text, text.get_rect(center=(self.width//2, self.height//2)))

        pygame.display.flip()

    def run(self):
        # Chạy luồng nhận dữ liệu từ server
        threading.Thread(
            target=self.receive_game_state,
            daemon=True
        ).start()

        clock = pygame.time.Clock()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            keys = pygame.key.get_pressed()
            # Giới hạn biên để paddle không chạy ra ngoài màn hình
            if keys[pygame.K_UP] and self.paddle_y > 0:
                self.paddle_y -= self.paddle_speed
            if keys[pygame.K_DOWN] and self.paddle_y < self.height - 100:
                self.paddle_y += self.paddle_speed

            self.send_paddle_position()
            self.draw()
            clock.tick(60)

        self.client.close()
        pygame.quit()

if __name__ == "__main__":
    client = PongClient()
    client.run()