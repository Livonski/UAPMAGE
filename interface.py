import pygame


PIXELSCALE = 3
PANELWIDTH = 290
SLIDERWIDTH = PANELWIDTH - 50
SLIDERFIRSTY = 108
SLIDERSPACING = 75

controls = [
    ("Noise scale", "scale", 10, 400, 5),
    ("Octaves", "octaves", 1, 8, 1),
    ("Persistence", "persistence", 0.1, 1.0, 0.05),
    ("Lacunarity", "lacunarity", 1.0, 4.0, 0.1),
    ("Offset X", "offset_x", -1024, 1024, 8),
    ("Offset Y", "offset_y", -1024, 1024, 8),
    ("Contrast", "contrast", 0.5, 5.0, 0.1),
    ("Seed", "seed", 0, 1000, 1),
]

class MapInterface:
    def __init__(self, width, height, settings, generateMap):
        self.width = width
        self.height = height
        self.settings = settings
        self.generateMap = generateMap

        self.mapWidth = width * PIXELSCALE
        self.mapHeight = height * PIXELSCALE
        self.sliderX = self.mapWidth + 25
        self.activeSlider = None

        pygame.init()
        self.window = pygame.display.set_mode((self.mapWidth + PANELWIDTH, self.mapHeight))
        pygame.display.set_caption("UAPMAGE")
        self.font = pygame.font.SysFont("consolas", 18)
        self.smallFont = pygame.font.SysFont("consolas", 18)
        self.clock = pygame.time.Clock()

        self.mapImage = None
        self.pixels = None
        self.regenerateMap()

    def regenerateMap(self):
        self.pixels = self.generateMap()
        surface = pygame.image.frombuffer(self.pixels, (self.width, self.height), "RGB")
        self.mapImage = pygame.transform.scale(surface, (self.mapWidth, self.mapHeight))

    def sliderY(self, index):
        return SLIDERFIRSTY + index * SLIDERSPACING

    def updateSlider(self, index, mouseX):
        _, key, low, high, step = controls[index]

        t = max(0.0, min(1.0, (mouseX - self.sliderX) / SLIDERWIDTH))
        value = low + round((high - low) * t / step) * step
        value = max(low, min(high, value))

        self.settings[key] = int(value) if isinstance(step, int) else round(value, 3)

    def drawPanel(self):
        pygame.draw.rect(self.window, (29, 33, 39), (self.mapWidth, 0, PANELWIDTH, self.mapHeight))
        self.window.blit(self.font.render("PERLIN SETTINGS", True, (240, 240, 240)), (self.sliderX, 30))

        for index, (label, key, low, high, step) in enumerate(controls):
            y = self.sliderY(index)
            value = self.settings[key]
            displayValue = str(value) if isinstance(value, int) else f"{value:.2f}"
            caption = self.font.render(f"{label}: {displayValue}", True, (230, 230, 230))
            self.window.blit(caption, (self.sliderX, y - 33))

            t = (value - low) / (high - low)
            knobX = round(self.sliderX + t * SLIDERWIDTH)
            pygame.draw.rect(self.window, (75, 82, 92), (self.sliderX, y - 3, SLIDERWIDTH, 6), border_radius=3)
            pygame.draw.rect(self.window, (75, 170, 230), (self.sliderX, y - 3, max(0, knobX - self.sliderX), 6), border_radius=3)
            pygame.draw.circle(self.window, (235, 240, 245), (knobX, y), 9)

        hint = "Release mouse to update" if self.activeSlider is not None else "Drag a slider to change"
        self.window.blit(self.smallFont.render(hint, True, (165, 172, 183)), (self.sliderX, self.mapHeight - 52))

    def run(self):
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for index in range(len(controls)):
                        hitbox = pygame.Rect(self.sliderX - 10, self.sliderY(index) - 14, SLIDERWIDTH + 20, 28)
                        if hitbox.collidepoint(event.pos):
                            self.activeSlider = index
                            self.updateSlider(index, event.pos[0])
                            break
                elif event.type == pygame.MOUSEMOTION and self.activeSlider is not None:
                    self.updateSlider(self.activeSlider, event.pos[0])
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.activeSlider is not None:
                        self.updateSlider(self.activeSlider, event.pos[0])
                        self.activeSlider = None
                        self.regenerateMap()

            self.window.blit(self.mapImage, (0, 0))
            self.drawPanel()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
