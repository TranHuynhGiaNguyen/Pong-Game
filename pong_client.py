import socket
import pickle
import threading

import pygame


# Update UI logic

class PongClient:

    def __init__(self, host='localhost', port=5555):
        
        # Initialize Pygame
        pygame.init()
        

        # Display
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(f"Pong - Player {self.player_id + 1}")

        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)

        # Font
        self.font = pygame.font.Font(None, 74)
        self.small_font = pygame.font.Font(None, 36)
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
            if keys[pygame.K_UP]:
                self.paddle_y -= self.paddle_speed
            if keys[pygame.K_DOWN]:
                self.paddle_y += self.paddle_speed

            self.send_paddle_position()
            self.draw()
            clock.tick(60)

        self.client.close()
        pygame.quit()

if __name__ == "__main__":
    client = PongClient()
    client.run()
