import random
import math
import array as arr
from functools import lru_cache

from interface import MapInterface

WIDTH, HEIGHT = 256, 256

deepWaterCol = (86,  193, 220)
plainsCol    = (181, 230, 29)
mountainsCol = (195, 195, 195)
savannaCol   = (255, 255, 128)
desertCol    = (255, 242, 0)

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

temperatureSettings = {
    "fallof": 5.0,
    "strength": 0.7,
    "heightInfluence": 0.7
}

biomesSettings = {
    "deepWaterMaxH": 128,
    "mountainsMaxH": 180,
    "plainsMaxT"   : 160,
    "savannaMaxT"  : 170
}

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]

def lerp(a, b, t):
    return a + (b - a) * t

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def smoothStep(v):
    return v * v * (3.0 - 2.0 * v)

def centerWeight(y, h, fallof = 1.0, strength = 1.0, heightInfluence = 0.7):
    distance = 4.0 * y * (1.0 - y)
    positionWeight = distance ** fallof

    heightWeight = 1.0 - heightInfluence * smoothStep(h)

    return strength * positionWeight * heightWeight

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
    hMap = arr.array('i')

    for y in range(HEIGHT):
        for x in range(WIDTH):
            noise = fractalNoise(x, y, settings)

            pValue = int((noise * settings["contrast"] + 1) * 0.5 * 255)
            hMap.append(pValue)

    return hMap    

def generateTemperatureMap(settings, heightMap):
    tMap = arr.array('i')
    for y in range(HEIGHT):
        for x in range(WIDTH):
            pY = y / HEIGHT
            h = heightMap[y * WIDTH + x] / 255
            tValue = centerWeight(pY, h, settings["fallof"], settings["strength"], settings["heightInfluence"])
            tValue = int((tValue + 1) * 0.5 * 255)
            tMap.append(tValue)

    return tMap

def generateMap():
    pixels = bytearray(WIDTH * HEIGHT * 3)
    hMap = generateHeightMap(heightSettings)
    tMap = generateTemperatureMap(temperatureSettings, hMap)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            hValue = max(0, min(255, hMap[y * WIDTH + x]))
            tValue = max(0, min(255, tMap[y * WIDTH + x]))
            i = (y * WIDTH + x) * 3

            if hValue < biomesSettings["deepWaterMaxH"]:
                color = deepWaterCol
            elif hValue > biomesSettings["mountainsMaxH"]:
                color = mountainsCol
            elif tValue < biomesSettings["plainsMaxT"]:
                color = plainsCol
            elif tValue < biomesSettings["savannaMaxT"]:
                color = savannaCol
            else:
                color = desertCol

            pixels[i:i+3] = bytes(color)

    return pixels

if __name__ == "__main__":
    MapInterface(WIDTH, HEIGHT, heightSettings, generateMap).run()