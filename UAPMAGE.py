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
    MOISTURE = 4

class generationStatus(Enum):
    START           = 1
    HEIGHTMAP       = 2
    TEMPERATUREMAP  = 3
    MOISTUREMAP     = 5
    BIOMEEVALUATION = 6
    FINISH          = 7

@dataclass
class biomeSettings:
    minH: int
    maxH: int
    minT: int
    maxT: int
    minM: int
    maxM: int

deepWaterCol    = (86,  193, 220)
shallowWaterCol = (153, 217, 234)
plainsCol       = (181, 230, 29)
forestCol       = (23,  121, 53)
swampCol        = (1,   71,  54)
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

moistureSettings = {
    "windAngle"         : 100.0,
    "oceanEvaporation"  : 0.08,
    "landEvaporation"   : 0.04,
    "precipitationRate" : 0.04,
    "orographicStrength": 1.0,
    "noiseInfluence"    : 0.2,
}

biomesSettings = {
    "deepWater"   : biomeSettings(0,   119, 0,   255, 0,   255),
    "shallowWater": biomeSettings(120, 128, 0,   255, 0,   255),
    "mountains"   : biomeSettings(180, 255, 0,   255, 0,   255),
    "plains"      : biomeSettings(129, 179, 0,   160, 151, 255),
    "forest"      : biomeSettings(129, 179, 0,   160, 171, 255),
    "swamp"       : biomeSettings(129, 179, 0,   160, 191, 255),
    "savanna"     : biomeSettings(129, 179, 161, 170, 101, 150),
    "desert"      : biomeSettings(129, 179, 171, 255, 0,   100),
}

biomeColors = {
    "deepWater":    deepWaterCol,
    "shallowWater": shallowWaterCol,
    "mountains":    mountainsCol,
    "plains":       plainsCol,
    "forest":       forestCol,
    "swamp":        swampCol,
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

def clamp(v, miv, mav):
    return min(mav, max(v, miv))

def sign(v):
    return (v > 0) - (v < 0)

def gaussian(x, center, width):
    distance = (x - center) / width
    return math.exp(-distance * distance)

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

def calculateEvaporation(h, t):
    waterLevel = biomesSettings["shallowWater"].maxH /255.0

    if h <= waterLevel:
        return moistureSettings["oceanEvaporation"] * (0.4 + 0.6 * t)

    return moistureSettings["landEvaporation"]


def readMap(map, x, y, default=0.0):
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            return default

    return map[y * WIDTH + x]

def incomingAir(aMap, x, y, windX, windY):
    weightX = abs(windX)
    weightY = abs(windY)
    total = weightX + weightY

    if total < 1e-10:
        return 0.0

    airX = readMap(aMap, x - sign(windX), y) if weightX > 1e-10 else 0.0
    airY = readMap(aMap, x, y - sign(windY)) if weightY > 1e-10 else 0.0

    return (airX * weightX + airY * weightY) / (weightX + weightY)

def calculateMountainEffect(hMap, x, y, windX, windY):
    currentHeight = hMap[y * WIDTH + x]

    previousX = x - sign(windX) if abs(windX) > 1e-10 else x
    previousY = y - sign(windY) if abs(windY) > 1e-10 else y

    upwindHeight  = readMap(hMap, previousX, previousY, currentHeight)
    
    elevationGain = max(0.0, (currentHeight - upwindHeight) / 255.0)

    return elevationGain * moistureSettings["orographicStrength"]

def latitudeRainFactor(y):
    latitude = abs(2 * (y / HEIGHT) - 1)

    equatorialWet  = gaussian(latitude, 0.0,  0.18)
    subtropicalDry = gaussian(latitude, 0.33, 0.10)
    temperateWet   = gaussian(latitude, 0.65, 0.16)

    factor = 1.0

    factor += 0.5 * equatorialWet
    factor -= 0.5 * subtropicalDry
    factor += 0.2 * temperateWet

    return clamp(factor, 0.3, 2.0)

def calculateSurfaceMoisture(precipitation, temperature):
    evaporation = 0.005 + 0.015 * temperature

    if precipitation + evaporation == 0:
        return 0.0

    return precipitation / (precipitation + evaporation) 

def generateMoistureMap(hMap, tMap):
    count = WIDTH * HEIGHT

    aMap = arr.array('f', [0.0]) * count
    rMap = arr.array('f', [0.0]) * count
    mMap = arr.array('i', [0]) * count

    angle = math.radians(moistureSettings["windAngle"])

    windX = math.cos(angle)
    windY = math.sin(angle)

    xOrder = range(WIDTH) if windX >= 0 else range(WIDTH - 1, -1, -1)
    yOrder = range(HEIGHT) if windY >= 0 else range(HEIGHT - 1, -1, -1)

    for y in yOrder:
        for x in xOrder:

            i = y * WIDTH + x
            
            height = hMap[i] / 255
            temperature = tMap[i] / 255

            air = incomingAir(aMap, x, y, windX, windY)

            upwindHeight = None

            air += calculateEvaporation(height, temperature)
            air = clamp(air, 0.0, 1.0)

            rain = moistureSettings["precipitationRate"]
            rain *= latitudeRainFactor(y)

            noise = clamp(0.5 + perlinNoise(x / 32.0, y / 32.0, heightSettings["seed"] + 1000), 0.0, 1.0)
            noiseFactor = 1.0 + moistureSettings["noiseInfluence"] * (2.0 * noise - 1)
            rain *= noiseFactor

            rain += calculateMountainEffect(hMap, x, y, math.cos(moistureSettings["windAngle"]), math.sin(moistureSettings["windAngle"]))
            rain = clamp(rain, 0.0, 0.25)

            precipitation = air * rain
            air -= rain
            
            aMap[i] = air
            rMap[i] = precipitation

    waterLevel = biomesSettings["shallowWater"].maxH
    for i in range(count):
        if hMap[i] <= waterLevel:
            moisture = 1.0
        else:
            temperature = tMap[i] / 255.0
            moisture = calculateSurfaceMoisture(rMap[i], temperature)

        mMap[i] = int(clamp(moisture, 0.0, 1.0) * 255)

    return mMap

def evaluateBiomes(height, temperature, moisture, settings):
    closestBiome = None
    closestDistance = float("inf")

    for name, settings in settings.items():
        dh = max(settings.minH - height, 0, height - settings.maxH)
        dt = max(settings.minT - temperature, 0, temperature - settings.maxT)
        dm = max(settings.minM - moisture, 0, moisture - settings.maxM)
        distance = dh * dh + dt * dt + dm * dm

        if distance < closestDistance:
            closestDistance = distance
            closestBiome = name

    return biomeColors[closestBiome]

heightMap = None
temperatureMap = None
moistureMap = None
pixels = None

def generateMap(state = generationStatus.START, mode = displayMode.FULL):
    global heightMap, temperatureMap, moistureMap, pixels

    if state == generationStatus.START:
        state = generationStatus.HEIGHTMAP

    if not isinstance(state, generationStatus):
        raise ValueError(f"Unknown generation status: {state!r}")

    if state.value <= generationStatus.HEIGHTMAP.value or heightMap is None:
        heightMap = generateHeightMap(heightSettings)
        temperatureMap = None
        moistureMap = None
        pixels = None
        if mode.value == displayMode.HEIGHT.value:
            pixels = fillPixels(pixels, heightMap)
            return pixels

    if state.value <= generationStatus.TEMPERATUREMAP.value or temperatureMap is None:
        temperatureMap = generateTemperatureMap(temperatureSettings, heightMap)
        moistureMap = None
        pixels = None
        if mode.value == displayMode.TEMPERATURE.value:
            pixels = fillPixels(pixels, temperatureMap)
            return pixels

    if state.value <= generationStatus.MOISTUREMAP.value or moistureMap is None:
        moistureMap = generateMoistureMap(heightMap, temperatureMap)
        pixels = None
        if mode.value == displayMode.MOISTURE.value:
            pixels = fillPixels(pixels, moistureMap)
            return pixels

    if state.value <= generationStatus.BIOMEEVALUATION.value or pixels is None:
        pixels = bytearray(WIDTH * HEIGHT * 3)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                hValue = max(0, min(255, heightMap[y * WIDTH + x]))
                tValue = max(0, min(255, temperatureMap[y * WIDTH + x]))
                mValue = max(0, min(255, moistureMap[y * WIDTH + x]))
                i = (y * WIDTH + x) * 3
                color = evaluateBiomes(hValue, tValue, mValue, biomesSettings)
                #color = shallowWaterCol if hValue < biomesSettings["deepWaterMaxH"] else deepWaterCol
                #color = (tValue, tValue, tValue)
                pixels[i:i+3] = bytes(color)
        return pixels
            
if __name__ == "__main__":
    MapInterface(WIDTH, HEIGHT, heightSettings, generateMap, generationStatus).run()