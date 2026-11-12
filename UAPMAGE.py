import pygame
import random

WIDTH, HEIGHT, SCALE = 256, 256, 3

pixels = bytearray(WIDTH * HEIGHT * 3)

for y in range(HEIGHT):
    for x in range(WIDTH):
        color = (0,0,0) if random.random() < 0.5 else (255, 255, 255)
        i = (y * WIDTH + x) * 3
        pixels[i:i+3] = bytes(color)

pygame.init()
window = pygame.display.set_mode((WIDTH * SCALE, HEIGHT * SCALE))
surface = pygame.image.frombuffer(pixels, (WIDTH, HEIGHT), "RGB")

window.blit(pygame.transform.scale(surface, window.get_size()), (0, 0))
pygame.display.flip()

while pygame.event.wait().type != pygame.QUIT:
    pass

pygame.quit()