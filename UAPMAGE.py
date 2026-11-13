import random
import math
import array as arr
from enum import Enum
from functools import lru_cache
from dataclasses import dataclass

from interface import MapInterface

WIDTH, HEIGHT = 256, 256

class displayMode(Enum):
    FULL = 1
    HEIGHT = 2
    TEMPERATURE = 3

class generationStatus(Enum):
    START           = 1
    HEIGHTMAP       = 2
    TEMPERATUREMAP  = 3
    BIOMEEVALUATION = 4
    FINISH          = 5

@dataclass
class biomeSettings:
    minH: int
    maxH: int
    minT: int
    maxT: int

deepWaterCol    = (86,  193, 220)
shallowWaterCol = (153, 217, 234)
plainsCol       = (181, 230, 29)
mountainsCol    = (195, 195, 195)
savannaCol      = (255, 255, 128)
desertCol       = (255, 242, 0)

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
    "fallof"         : 3.0,
    "strength"       : 0.7,
    "heightInfluence": 0.8,
    "axialTilt"      : 23.5,
}

biomesSettings = {
    "deepWater"   : biomeSettings(0,   119, 0,   255),
    "shallowWater": biomeSettings(120, 128, 0,   255),
    "mountains"   : biomeSettings(180, 255, 0,   255),
    "plains"      : biomeSettings(129, 179, 0,   160),
    "savanna"     : biomeSettings(129, 179, 161, 170),
    "desert"      : biomeSettings(129, 179, 171, 255),
}

biomeColors = {
    "deepWater":    deepWaterCol,
    "shallowWater": shallowWaterCol,
    "mountains":    mountainsCol,
    "plains":       plainsCol,
    "savanna":      savannaCol,
    "desert":       desertCol,
}

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]

def lerp(a, b, t):
    return a + (b - a) * t

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def smoothStep(v):
    return v * v * (3.0 - 2.0 * v)

def centerWeight(y, h, fallof = 1.0, strength = 1.0, heightInfluence = 0.7, axialTilt = 23.5):
    tiltFactor = 1.0 + 2.0 * axialTilt / 90.0
    
    distance = 4.0 * y * (1.0 - y)
    positionWeight = distance ** (fallof / tiltFactor)

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

def fillPixels(pixels, map):
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            value = max(0, min(255, map[y * WIDTH + x]))
            color = (value, value, value)
            i = (y * WIDTH + x) * 3
            pixels[i:i+3] = bytes(color)
    return pixels

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
            tValue = centerWeight(pY, h, settings["fallof"], settings["strength"], settings["heightInfluence"], settings["axialTilt"])
            tValue = int((tValue + 1) * 0.5 * 255)
            tMap.append(tValue)

    return tMap

def evaluateBiomes(height, temperature, settings):
    closestBiome = None
    closestDistance = float("inf")

    for name, settings in settings.items():
        dh = max(settings.minH - height, 0, height - settings.maxH)
        dt = max(settings.minT - temperature, 0, temperature - settings.maxT)
        distance = dh * dh + dt * dt

        if distance < closestDistance:
            closestDistance = distance
            closestBiome = name

    return biomeColors[closestBiome]

heightMap = None
temperatureMap = None
pixels = None

class displayMode(Enum):
    FULL = 1
    HEIGHT = 2
    TEMPERATURE = 3

def generateMap(state = generationStatus.START, mode = displayMode.FULL):
    global heightMap, temperatureMap, pixels

    if state == generationStatus.START:
        state = generationStatus.HEIGHTMAP

    if not isinstance(state, generationStatus):
        raise ValueError(f"Unknown generation status: {state!r}")

    if state.value <= generationStatus.HEIGHTMAP.value or heightMap is None:
        heightMap = generateHeightMap(heightSettings)
        temperatureMap = None
        pixels = None
        if mode.value == displayMode.HEIGHT.value:
            pixels = fillPixels(pixels, heightMap)
            return pixels

    if state.value <= generationStatus.TEMPERATUREMAP.value or temperatureMap is None:
        temperatureMap = generateTemperatureMap(temperatureSettings, heightMap)
        pixels = None
        if mode.value == displayMode.TEMPERATURE.value:
            pixels = fillPixels(pixels, temperatureMap)
            return pixels

    if state.value <= generationStatus.BIOMEEVALUATION.value or pixels is None:
        pixels = bytearray(WIDTH * HEIGHT * 3)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                hValue = max(0, min(255, heightMap[y * WIDTH + x]))
                tValue = max(0, min(255, temperatureMap[y * WIDTH + x]))
                i = (y * WIDTH + x) * 3
                color = evaluateBiomes(hValue, tValue, biomesSettings)
                #color = shallowWaterCol if hValue < biomesSettings["deepWaterMaxH"] else deepWaterCol
                #color = (tValue, tValue, tValue)
                pixels[i:i+3] = bytes(color)
        return pixels
            
if __name__ == "__main__":
    MapInterface(WIDTH, HEIGHT, heightSettings, generateMap, generationStatus).run()