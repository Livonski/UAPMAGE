import pygame

import random
import math

WIDTH, HEIGHT, SCALE = 256, 256, 3
SEED = 42
FREQUENCY = 0.02

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]

def lerp(a, b, t):
    return a + (b - a) * t

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def randomGradient(x, y):
    seed = (x * 73856093) ^ (y * 19349663) ^ SEED
    rng = random.Random(seed)

    angle = rng.random() * math.tau

    return(math.cos(angle), math.sin(angle))

def perlinNoise(x, y):
    cellX = math.floor(x)
    cellY = math.floor(y)

    localX = x - cellX
    localY = y - cellY

    gradientA = randomGradient(cellX,     cellY)
    gradientB = randomGradient(cellX + 1, cellY)
    gradientC = randomGradient(cellX,     cellY + 1)
    gradientD = randomGradient(cellX + 1, cellY + 1)

    distanceA = (localX,     localY)
    distanceB = (localX - 1, localY)
    distanceC = (localX,     localY - 1)
    distanceD = (localX - 1, localY - 1)

    valueA = dot(gradientA, distanceA)
    valueB = dot(gradientB, distanceB)
    valueC = dot(gradientC, distanceC)
    valueD = dot(gradientD, distanceD)

    u = fade(localX)
    v = fade(localY)

    top = lerp(valueA, valueB, u)
    bottom = lerp(valueC, valueD, u)

    return lerp(top, bottom, v)

pixels = bytearray(WIDTH * HEIGHT * 3)

for y in range(HEIGHT):
    for x in range(WIDTH):
        pValue = int((perlinNoise(x * FREQUENCY, y * FREQUENCY) + 1) / 2 * 255)
        color = (pValue, pValue, pValue)
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