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

# (UI label, displayMode member, cached map name)
# Add new output types here as the generator gains cached map layers.
DISPLAY_OPTIONS = [
    ("FULL", "FULL", None),
    ("HEIGHT", "HEIGHT", "heightMap"),
    ("TEMP", "TEMPERATURE", "temperatureMap"),
]

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
            ("Axial tilt", "axialTilt", 0.0, 90.0, 1.0),
        ],
    },
    {
        "title": "BIOMES",
        "source": "biomesSettings",
        "colorSource": "biomeColors",
        # Each dictionary value is a biomeSettings dataclass (or a dict).
        # Biome names come from the generator automatically.
        "itemControls": [
            ("Min height", "minH", 0, 255, 1),
            ("Max height", "maxH", 0, 255, 1),
            ("Min temperature", "minT", 0, 255, 1),
            ("Max temperature", "maxT", 0, 255, 1),
        ],
    },
]


class MapInterface:
    def __init__(self, width, height, settings, generateMap, generationStatus):
        # Preserve the existing call:
        # MapInterface(WIDTH, HEIGHT, heightSettings, generateMap).run()
        self.width = width
        self.height = height
        self.settings = settings
        self.generateMap = generateMap
        self.generationStatus = generationStatus

        # The generator owns its dictionaries. We share their references,
        # so changing values here changes what generateMap() will read.
        generatorGlobals = getattr(generateMap, "__globals__", {})
        self.generatorGlobals = generatorGlobals
        modeType = generatorGlobals.get("displayMode")
        self.displayOptions = []
        for title, modeName, source in DISPLAY_OPTIONS:
            mode = getattr(modeType, modeName, None)
            if mode is not None:
                self.displayOptions.append({
                    "title": title, "mode": mode, "source": source
                })
        if not self.displayOptions:
            self.displayOptions = [{"title": "FULL", "mode": None, "source": None}]
        self.displayIndex = 0
        self.previewCache = {}

        self.categories = []
        for definition in SETTING_CATEGORIES:
            settingsDict = (
                settings if definition["source"] == "heightSettings"
                else generatorGlobals.get(definition["source"])
            )
            if not isinstance(settingsDict, dict):
                print(f"[Interface] Settings '{definition['source']}' not found; skipping category")
                continue

            itemControls = definition.get("itemControls")
            if itemControls is None:
                missing = [key for _, key, *_ in definition["controls"] if key not in settingsDict]
            else:
                if not settingsDict:
                    raise ValueError(f"Category {definition['title']} has no items")
                missing = [
                    f"{itemName}.{key}"
                    for itemName, item in settingsDict.items()
                    for _, key, *_ in itemControls
                    if (key not in item if isinstance(item, dict) else not hasattr(item, key))
                ]
            if missing:
                raise KeyError(
                    f"Category {definition['title']} has unknown settings keys: {missing}"
                )

            self.categories.append({
                "title": definition["title"],
                "source": definition["source"],
                "settings": settingsDict,
                "controls": definition.get("controls", []),
                "itemControls": itemControls,
                "colors": generatorGlobals.get(definition.get("colorSource")),
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
        self.generateTakesSettings = "state" in signature.parameters
        self.generateHasDisplayMode = "mode" in signature.parameters

        self.mapWidth = width * PIXELSCALE
        self.mapHeight = height * PIXELSCALE
        self.panelX = self.mapWidth
        self.sliderX = self.panelX + PANELPADDING
        self.sliderWidth = PANELWIDTH - PANELPADDING * 2
        self.sliderTop = 235
        self.contentBottom = self.mapHeight - 66

        self.categoryIndex = 0
        self.itemIndices = [0] * len(self.categories)
        self.scrollY = 0
        self.activeSlider = None
        self.sliderChanged = False

        gap = 6
        buttonWidth = (
            self.sliderWidth - gap * (len(self.displayOptions) - 1)
        ) // len(self.displayOptions)
        self.displayRects = [
            pygame.Rect(
                self.sliderX + index * (buttonWidth + gap), 80,
                buttonWidth if index < len(self.displayOptions) - 1
                else self.sliderWidth - index * (buttonWidth + gap),
                32,
            )
            for index in range(len(self.displayOptions))
        ]

        self.previousRect = pygame.Rect(self.sliderX, 153, 39, 38)
        self.nextRect = pygame.Rect(
            self.panelX + PANELWIDTH - PANELPADDING - 39, 153, 39, 38
        )
        self.itemPreviousRect = pygame.Rect(self.sliderX, 237, 39, 38)
        self.itemNextRect = pygame.Rect(
            self.panelX + PANELWIDTH - PANELPADDING - 39, 237, 39, 38
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
        self.regenerateMap(generationStatus.START)

    @property
    def category(self):
        return self.categories[self.categoryIndex]

    @property
    def hasItems(self):
        return self.category["itemControls"] is not None

    @property
    def controls(self):
        return self.category["itemControls"] if self.hasItems else self.category["controls"]

    @property
    def itemName(self):
        return list(self.category["settings"])[self.itemIndices[self.categoryIndex]]

    def targetSettings(self):
        settings = self.category["settings"]
        return settings[self.itemName] if self.hasItems else settings

    def getSetting(self, key):
        target = self.targetSettings()
        return target[key] if isinstance(target, dict) else getattr(target, key)

    def setSetting(self, key, value):
        target = self.targetSettings()
        if isinstance(target, dict):
            target[key] = value
        else:
            setattr(target, key, value)

    def sliderStartY(self):
        return self.sliderTop + (73 if self.hasItems else 0)

    def currentContentRect(self):
        top = self.sliderStartY() - 12
        return pygame.Rect(
            self.panelX, top, PANELWIDTH,
            max(0, self.contentBottom - top + 17),
        )

    def regenerateMap(self, stage=None):
        # Always retain a full biome image so switching display modes never
        # reruns the generator or invalidates its cached intermediate maps.
        if stage is None:
            stageBySource = {
                "heightSettings": self.generationStatus.HEIGHTMAP,
                "temperatureSettings": self.generationStatus.TEMPERATUREMAP,
                "biomesSettings": self.generationStatus.BIOMEEVALUATION,
            }
            stage = stageBySource.get(
                self.category["source"], self.generationStatus.START
            )

        if self.generateTakesSettings:
            if self.generateHasDisplayMode:
                fullMode = next(
                    (option["mode"] for option in self.displayOptions
                     if option["source"] is None),
                    None,
                )
                self.fullPixels = self.generateMap(stage, fullMode)
            else:
                self.fullPixels = self.generateMap(stage)
        else:
            self.fullPixels = self.generateMap()

        expectedSize = self.width * self.height * 3
        if self.fullPixels is None or len(self.fullPixels) != expectedSize:
            actualSize = None if self.fullPixels is None else len(self.fullPixels)
            raise ValueError(
                f"generateMap() returned {actualSize} bytes; "
                f"expected {expectedSize} RGB bytes"
            )

        # A stage may recompute intermediate layers when earlier data is absent.
        self.previewCache.clear()
        self.refreshDisplay()

    def refreshDisplay(self):
        option = self.displayOptions[self.displayIndex]
        source = option["source"]

        if source is None:
            self.pixels = self.fullPixels
        else:
            if source not in self.previewCache:
                values = self.generatorGlobals.get(source)
                if values is None:
                    self.pixels = self.fullPixels
                else:
                    expectedSize = self.width * self.height
                    if len(values) != expectedSize:
                        raise ValueError(
                            f"{source} has {len(values)} elements; "
                            f"expected {expectedSize}"
                        )
                    grayscale = bytearray(expectedSize * 3)
                    for index, rawValue in enumerate(values):
                        value = max(0, min(255, int(rawValue)))
                        offset = index * 3
                        grayscale[offset:offset + 3] = bytes((value, value, value))
                    self.previewCache[source] = grayscale
                    self.pixels = grayscale
            else:
                self.pixels = self.previewCache[source]

        surface = pygame.image.frombuffer(
            self.pixels, (self.width, self.height), "RGB"
        )
        self.mapImage = pygame.transform.scale(
            surface, (self.mapWidth, self.mapHeight)
        )

    def selectDisplay(self, index):
        if self.activeSlider is not None:
            return
        if 0 <= index < len(self.displayOptions) and index != self.displayIndex:
            self.displayIndex = index
            self.refreshDisplay()

    def selectCategory(self, index):
        if self.activeSlider is not None:
            return
        self.categoryIndex = index % len(self.categories)
        self.scrollY = 0

    def selectItem(self, delta):
        if self.activeSlider is not None or not self.hasItems:
            return
        categoryIndex = self.categoryIndex
        count = len(self.category["settings"])
        self.itemIndices[categoryIndex] = (self.itemIndices[categoryIndex] + delta) % count
        self.scrollY = 0

    def maxScroll(self):
        controlsCount = len(self.controls)
        if not controlsCount:
            return 0
        lastKnobY = self.sliderStartY() + 39 + (controlsCount - 1) * SLIDERSPACING
        return max(0, lastKnobY + 16 - self.contentBottom)

    def sliderY(self, index):
        return self.sliderStartY() + 39 + index * SLIDERSPACING - self.scrollY

    def updateSlider(self, index, mouseX):
        _, key, low, high, step = self.controls[index]

        t = max(0.0, min(1.0, (mouseX - self.sliderX) / self.sliderWidth))
        # Using step-index arithmetic avoids most floating-point drift.
        steps = round((high - low) / step)
        stepIndex = round(t * steps)
        value = max(low, min(high, low + stepIndex * step))
        value = int(value) if isinstance(step, int) else round(value, 4)

        # Keep min/max ranges valid while editing biome boundaries.
        if self.hasItems and key.startswith(("min", "max")):
            opposite = ("max" if key.startswith("min") else "min") + key[3:]
            target = self.targetSettings()
            hasOpposite = opposite in target if isinstance(target, dict) else hasattr(target, opposite)
            if hasOpposite:
                boundary = self.getSetting(opposite)
                value = min(value, boundary) if key.startswith("min") else max(value, boundary)

        if self.getSetting(key) != value:
            self.setSetting(key, value)
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
        self.drawText("DISPLAY  [1-3]", self.sliderX, 56,
                      (155, 168, 182), self.smallFont)

        for index, option in enumerate(self.displayOptions):
            rect = self.displayRects[index]
            active = index == self.displayIndex
            background = (53, 104, 143) if active else (45, 51, 60)
            pygame.draw.rect(self.window, background, rect, border_radius=5)
            label = self.smallFont.render(
                option["title"], True,
                (248, 251, 255) if active else (177, 188, 201),
            )
            self.window.blit(
                label, (
                    rect.centerx - label.get_width() // 2,
                    rect.centery - label.get_height() // 2,
                ),
            )

        pygame.draw.line(
            self.window, (57, 65, 75),
            (self.sliderX, 132), (self.sliderX + self.sliderWidth, 132),
        )

        # Selector always takes one row, regardless of category count.
        pygame.draw.rect(self.window, (45, 51, 60), self.previousRect, border_radius=5)
        pygame.draw.rect(self.window, (45, 51, 60), self.nextRect, border_radius=5)
        self.drawText("<", self.previousRect.x + 14, self.previousRect.y + 7)
        self.drawText(">", self.nextRect.x + 14, self.nextRect.y + 7)

        categoryLabel = self.category["title"]
        labelSurface = self.font.render(categoryLabel, True, (238, 242, 247))
        self.window.blit(
            labelSurface,
            (self.panelX + (PANELWIDTH - labelSurface.get_width()) // 2, 157),
        )
        counter = f"{self.categoryIndex + 1} / {len(self.categories)}"
        counterSurface = self.smallFont.render(counter, True, (155, 168, 182))
        self.window.blit(
            counterSurface,
            (self.panelX + (PANELWIDTH - counterSurface.get_width()) // 2, 180),
        )

        pygame.draw.line(
            self.window, (57, 65, 75),
            (self.sliderX, 211), (self.sliderX + self.sliderWidth, 211),
        )

        if self.hasItems:
            self.drawText("BIOME", self.sliderX, 220, (155, 168, 182), self.smallFont)
            pygame.draw.rect(self.window, (45, 51, 60), self.itemPreviousRect, border_radius=5)
            pygame.draw.rect(self.window, (45, 51, 60), self.itemNextRect, border_radius=5)
            self.drawText("<", self.itemPreviousRect.x + 14, self.itemPreviousRect.y + 7)
            self.drawText(">", self.itemNextRect.x + 14, self.itemNextRect.y + 7)

            displayName = "".join(" " + char if char.isupper() else char for char in self.itemName)
            displayName = displayName.strip().title()
            itemSurface = self.font.render(displayName, True, (238, 242, 247))
            self.window.blit(itemSurface, (
                self.panelX + (PANELWIDTH - itemSurface.get_width()) // 2, 246
            ))
            colors = self.category["colors"]
            if isinstance(colors, dict) and self.itemName in colors:
                pygame.draw.rect(
                    self.window, colors[self.itemName],
                    (self.sliderX, 284, 18, 12), border_radius=2,
                )
                self.drawText("Biome color", self.sliderX + 25, 281,
                              (153, 164, 177), self.smallFont)

        previousClip = self.window.get_clip()
        self.window.set_clip(self.currentContentRect())
        for index, (label, key, low, high, step) in enumerate(self.controls):
            y = self.sliderY(index)
            if y < self.sliderStartY() - 35 or y > self.contentBottom + 20:
                continue

            value = self.getSetting(key)
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
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.selectDisplay(
                    (pygame.K_1, pygame.K_2, pygame.K_3).index(event.key)
                )
            if event.key in (pygame.K_TAB, pygame.K_RIGHT):
                self.selectCategory(self.categoryIndex + 1)
            elif event.key == pygame.K_LEFT:
                self.selectCategory(self.categoryIndex - 1)
            elif event.key == pygame.K_UP:
                self.selectItem(-1)
            elif event.key == pygame.K_DOWN:
                self.selectItem(1)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.displayRects):
                if rect.collidepoint(event.pos):
                    self.selectDisplay(index)
                    return True
            if self.previousRect.collidepoint(event.pos):
                self.selectCategory(self.categoryIndex - 1)
            elif self.nextRect.collidepoint(event.pos):
                self.selectCategory(self.categoryIndex + 1)
            elif self.hasItems and self.itemPreviousRect.collidepoint(event.pos):
                self.selectItem(-1)
            elif self.hasItems and self.itemNextRect.collidepoint(event.pos):
                self.selectItem(1)
            elif self.regenerateRect.collidepoint(event.pos):
                self.regenerateMap()
            elif self.currentContentRect().collidepoint(event.pos):
                for index in range(len(self.controls)):
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