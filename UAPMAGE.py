import random
import math
import array as arr
from functools import lru_cache

from interface import MapInterface

WIDTH, HEIGHT = 256, 256

heightSettings = {
    "scale": 65.0,
    "octaves": 5,
    "persistence": 0.6,
    "lacunarity": 2.0,
    "offset_x": 0,
    "offset_y": 0,
    "contrast": 2.0,
    "seed": 42,
}

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]

def lerp(a, b, t):
    return a + (b - a) * t

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

@lru_cache(maxsize=65536)
def randomGradient(x, y, seed):
    key = (x * 73856093) ^ (y * 19349663) ^ seed
    rng = random.Random(key)
    angle = rng.random() * math.tau
    return(math.cos(angle), math.sin(angle))

def perlinNoise(x, y, seed):
    cellX = math.floor(x)
    cellY = math.floor(y)

    localX = x - cellX
    localY = y - cellY

    gradientA = randomGradient(cellX,     cellY,     seed)
    gradientB = randomGradient(cellX + 1, cellY,     seed)
    gradientC = randomGradient(cellX,     cellY + 1, seed)
    gradientD = randomGradient(cellX + 1, cellY + 1, seed)

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

def fractalNoise(x, y, settings):
    total = 0
    maxAmplitude = 0
    amplitude = 1.0
    frequency = 1.0

    sampleX = (x + settings["offset_x"]) / settings["scale"]
    sampleY = (y + settings["offset_y"]) / settings["scale"]

    for i in range(settings["octaves"]):
        total += perlinNoise(sampleX * frequency, sampleY * frequency, settings["seed"]) * amplitude
        
        maxAmplitude += amplitude
        
        frequency *= settings["lacunarity"]
        amplitude *= settings["persistence"]

    return total / maxAmplitude if maxAmplitude > 0 else 0

def generateHeightMap(settings):
    hMap = arr.array('f')

    for y in range(HEIGHT):
        for x in range(WIDTH):
            noise = fractalNoise(x, y, settings)

            pValue = int((noise * settings["contrast"] + 1) * 0.5 * 255)
            hMap.append(pValue)

    return hMap    

#def generateTemperatureMap():
#    tMap = array.Array()
#    for y in range(HEIGHT):
#        for x in range(WIDTH):
#
#    return tMap

def generateMap(settings):
    pixels = bytearray(WIDTH * HEIGHT * 3)
    hMap = generateHeightMap(heightSettings)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            hValue = max(0, min(255, hMap[y * WIDTH + x]))
            i = (y * WIDTH + x) * 3

            color = (181, 230, 29) if hValue < 128 else (86, 193, 220)
            pixels[i:i+3] = bytes(color)

    return pixels

if __name__ == "__main__":
    MapInterface(WIDTH, HEIGHT, heightSettings, generateMap).run()