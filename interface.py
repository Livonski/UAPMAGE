"""Pygame interface for UAPMAGE.

To add another slider, edit only SETTING_CATEGORIES below.
To add a category, add a new descriptor whose `source` matches a settings
Dictionary defined in the module containing generateMap().

This module does not import UAPMAGE to avoid circular imports.
"""

import inspect
import pygame


PIXELSCALE = 3
PANELWIDTH = 300
PANELPADDING = 22
SLIDERSPACING = 72

# (caption, settings key, minimum, maximum, step)
# Keep the keys EXACTLY as they are spelled in the generator.
SETTING_CATEGORIES = [
    {
        "title": "HEIGHT",
        "source": "heightSettings",
        "controls": [
            ("Noise scale", "scale", 10.0, 400.0, 5.0),
            ("Octaves", "octaves", 1, 8, 1),
            ("Persistence", "persistence", 0.1, 1.0, 0.05),
            ("Lacunarity", "lacunarity", 1.0, 4.0, 0.1),
            ("Offset X", "offset_x", -1024, 1024, 8),
            ("Offset Y", "offset_y", -1024, 1024, 8),
            ("Contrast", "contrast", 0.5, 5.0, 0.1),
            ("Seed", "seed", 0, 1000, 1),
        ],
    },
    {
        "title": "TEMPERATURE",
        "source": "temperatureSettings",
        "controls": [
            ("Falloff", "fallof", 0.1, 12.0, 0.1),
            ("Strength", "strength", 0.0, 2.0, 0.05),
            ("Height influence", "heightInfluence", 0.0, 1.0, 0.05),
        ],
    },
    {
        "title": "BIOMES",
        "source": "biomesSettings",
        "controls": [
            ("Deep water max H", "deepWaterMaxH", 0, 255, 1),
            ("Shallow water max H", "shallowWaterMaxH", 0, 255, 1),
            ("Mountains max H", "mountainsMaxH", 0, 255, 1),
            ("Plains max T", "plainsMaxT", 0, 255, 1),
            ("Savanna max T", "savannaMaxT", 0, 255, 1),
        ],
    },
]


class MapInterface:
    def __init__(self, width, height, settings, generateMap):
        # Preserve the existing call:
        # MapInterface(WIDTH, HEIGHT, heightSettings, generateMap).run()
        self.width = width
        self.height = height
        self.settings = settings
        self.generateMap = generateMap

        # The generator owns its dictionaries. We share their references,
        # so changing values here changes what generateMap() will read.
        generatorGlobals = getattr(generateMap, "__globals__", {})
        self.categories = []
        for definition in SETTING_CATEGORIES:
            settingsDict = (
                settings if definition["source"] == "heightSettings"
                else generatorGlobals.get(definition["source"])
            )
            if not isinstance(settingsDict, dict):
                print(f"[Interface] Settings '{definition['source']}' not found; skipping category")
                continue

            missing = [key for _, key, *_ in definition["controls"] if key not in settingsDict]
            if missing:
                raise KeyError(
                    f"Category {definition['title']} has unknown settings keys: {missing}"
                )

            self.categories.append({
                "title": definition["title"],
                "settings": settingsDict,
                "controls": definition["controls"],
            })

        if not self.categories:
            raise ValueError("MapInterface has no settings categories to display")

        # Current generator takes no arguments. Also keep compatibility with
        # the previous generateMap(settings) version.
        signature = inspect.signature(generateMap)
        requiredPositional = [
            parameter for parameter in signature.parameters.values()
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ) and parameter.default is inspect.Parameter.empty
        ]
        if len(requiredPositional) > 1:
            raise TypeError("generateMap must take zero or one required positional argument")
        self.generateTakesSettings = bool(requiredPositional)

        self.mapWidth = width * PIXELSCALE
        self.mapHeight = height * PIXELSCALE
        self.panelX = self.mapWidth
        self.sliderX = self.panelX + PANELPADDING
        self.sliderWidth = PANELWIDTH - PANELPADDING * 2
        self.sliderTop = 157
        self.contentBottom = self.mapHeight - 66
        self.contentRect = pygame.Rect(
            self.panelX, self.sliderTop - 12,
            PANELWIDTH, max(0, self.contentBottom - self.sliderTop + 17),
        )

        self.categoryIndex = 0
        self.scrollY = 0
        self.activeSlider = None
        self.sliderChanged = False

        self.previousRect = pygame.Rect(self.sliderX, 76, 39, 38)
        self.nextRect = pygame.Rect(
            self.panelX + PANELWIDTH - PANELPADDING - 39, 76, 39, 38
        )
        self.regenerateRect = pygame.Rect(
            self.sliderX, self.mapHeight - 48, self.sliderWidth, 30
        )

        pygame.init()
        self.window = pygame.display.set_mode(
            (self.mapWidth + PANELWIDTH, self.mapHeight)
        )
        pygame.display.set_caption("UAPMAGE")
        self.font = pygame.font.SysFont("consolas", 17)
        self.smallFont = pygame.font.SysFont("consolas", 14)
        self.titleFont = pygame.font.SysFont("consolas", 20, bold=True)
        self.clock = pygame.time.Clock()

        self.pixels = None
        self.mapImage = None
        self.regenerateMap()

    @property
    def category(self):
        return self.categories[self.categoryIndex]

    def regenerateMap(self):
        if self.generateTakesSettings:
            self.pixels = self.generateMap(self.settings)
        else:
            self.pixels = self.generateMap()

        expectedSize = self.width * self.height * 3
        if len(self.pixels) != expectedSize:
            raise ValueError(
                f"generateMap() returned {len(self.pixels)} bytes; "
                f"expected {expectedSize} RGB bytes"
            )
        surface = pygame.image.frombuffer(self.pixels, (self.width, self.height), "RGB")
        self.mapImage = pygame.transform.scale(
            surface, (self.mapWidth, self.mapHeight)
        )

    def selectCategory(self, index):
        if self.activeSlider is not None:
            return
        self.categoryIndex = index % len(self.categories)
        self.scrollY = 0

    def maxScroll(self):
        controlsCount = len(self.category["controls"])
        if not controlsCount:
            return 0
        lastKnobY = self.sliderTop + 39 + (controlsCount - 1) * SLIDERSPACING
        return max(0, lastKnobY + 16 - self.contentBottom)

    def sliderY(self, index):
        return self.sliderTop + 39 + index * SLIDERSPACING - self.scrollY

    def updateSlider(self, index, mouseX):
        _, key, low, high, step = self.category["controls"][index]

        t = max(0.0, min(1.0, (mouseX - self.sliderX) / self.sliderWidth))
        # Using step-index arithmetic avoids most floating-point drift.
        steps = round((high - low) / step)
        stepIndex = round(t * steps)
        value = max(low, min(high, low + stepIndex * step))
        value = int(value) if isinstance(step, int) else round(value, 4)

        settings = self.category["settings"]
        if settings[key] != value:
            settings[key] = value
            self.sliderChanged = True

    def drawText(self, text, x, y, color=(235, 238, 242), font=None):
        font = font or self.font
        self.window.blit(font.render(text, True, color), (x, y))

    def drawPanel(self):
        pygame.draw.rect(
            self.window, (29, 33, 39),
            (self.panelX, 0, PANELWIDTH, self.mapHeight),
        )
        self.drawText("MAP SETTINGS", self.sliderX, 22, font=self.titleFont)

        # Selector always takes one row, regardless of category count.
        pygame.draw.rect(self.window, (45, 51, 60), self.previousRect, border_radius=5)
        pygame.draw.rect(self.window, (45, 51, 60), self.nextRect, border_radius=5)
        self.drawText("<", self.previousRect.x + 14, self.previousRect.y + 7)
        self.drawText(">", self.nextRect.x + 14, self.nextRect.y + 7)

        categoryLabel = self.category["title"]
        labelSurface = self.font.render(categoryLabel, True, (238, 242, 247))
        self.window.blit(
            labelSurface,
            (self.panelX + (PANELWIDTH - labelSurface.get_width()) // 2, 80),
        )
        counter = f"{self.categoryIndex + 1} / {len(self.categories)}"
        counterSurface = self.smallFont.render(counter, True, (155, 168, 182))
        self.window.blit(
            counterSurface,
            (self.panelX + (PANELWIDTH - counterSurface.get_width()) // 2, 103),
        )

        pygame.draw.line(
            self.window, (57, 65, 75),
            (self.sliderX, 132), (self.sliderX + self.sliderWidth, 132),
        )

        previousClip = self.window.get_clip()
        self.window.set_clip(self.contentRect)
        for index, (label, key, low, high, step) in enumerate(self.category["controls"]):
            y = self.sliderY(index)
            if y < self.sliderTop - 35 or y > self.contentBottom + 20:
                continue

            value = self.category["settings"][key]
            displayValue = str(value) if isinstance(value, int) else f"{value:.2f}"
            self.drawText(f"{label}: {displayValue}", self.sliderX, y - 33)

            t = max(0.0, min(1.0, (value - low) / (high - low)))
            knobX = round(self.sliderX + t * self.sliderWidth)
            pygame.draw.rect(
                self.window, (75, 82, 92),
                (self.sliderX, y - 3, self.sliderWidth, 6),
                border_radius=3,
            )
            pygame.draw.rect(
                self.window, (75, 170, 230),
                (self.sliderX, y - 3, max(0, knobX - self.sliderX), 6),
                border_radius=3,
            )
            pygame.draw.circle(self.window, (235, 240, 245), (knobX, y), 9)

        self.window.set_clip(previousClip)

        if self.maxScroll():
            self.drawText(
                "Wheel: scroll settings", self.sliderX,
                self.mapHeight - 75, (153, 164, 177), self.smallFont,
            )

        pygame.draw.rect(
            self.window, (53, 104, 143), self.regenerateRect, border_radius=5
        )
        text = "REGENERATE   [R]"
        textSurface = self.smallFont.render(text, True, (242, 247, 252))
        self.window.blit(
            textSurface,
            (self.regenerateRect.centerx - textSurface.get_width() // 2,
             self.regenerateRect.centery - textSurface.get_height() // 2),
        )

    def handleEvent(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_r:
                self.regenerateMap()
            if event.key in (pygame.K_TAB, pygame.K_RIGHT):
                self.selectCategory(self.categoryIndex + 1)
            elif event.key == pygame.K_LEFT:
                self.selectCategory(self.categoryIndex - 1)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.previousRect.collidepoint(event.pos):
                self.selectCategory(self.categoryIndex - 1)
            elif self.nextRect.collidepoint(event.pos):
                self.selectCategory(self.categoryIndex + 1)
            elif self.regenerateRect.collidepoint(event.pos):
                self.regenerateMap()
            elif self.contentRect.collidepoint(event.pos):
                for index in range(len(self.category["controls"])):
                    hitbox = pygame.Rect(
                        self.sliderX - 10, self.sliderY(index) - 14,
                        self.sliderWidth + 20, 28,
                    )
                    if hitbox.collidepoint(event.pos):
                        self.activeSlider = index
                        self.sliderChanged = False
                        self.updateSlider(index, event.pos[0])
                        break

        elif event.type == pygame.MOUSEMOTION and self.activeSlider is not None:
            self.updateSlider(self.activeSlider, event.pos[0])

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.activeSlider is not None:
                self.updateSlider(self.activeSlider, event.pos[0])
                self.activeSlider = None
                if self.sliderChanged:
                    self.regenerateMap()
                self.sliderChanged = False

        elif event.type == pygame.MOUSEWHEEL and self.activeSlider is None:
            # Scrolling should only act when the pointer is over the panel.
            if pygame.mouse.get_pos()[0] >= self.panelX:
                self.scrollY = max(
                    0, min(self.maxScroll(), self.scrollY - event.y * 35)
                )

        return True

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if not self.handleEvent(event):
                    running = False
                    break

            if not running:
                break

            self.window.blit(self.mapImage, (0, 0))
            self.drawPanel()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()