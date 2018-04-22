import sys

import pygame

import tools
import world
from vec2d import *

World = world.World()

# Some useful colours
grey = (100, 100, 100)
light_gray = (200, 200, 200)
red = (255, 0, 0)
dark_red = (192, 0, 0)
green = (0, 255, 0)
dark_green = (0, 128, 0)
blue = (0, 0, 255)
dark_blue = (0, 0, 192)
brown = (72, 64, 0)
silver = (224, 216, 216)
black = (0, 0, 0)
white = (255, 255, 255)
yellow = (255, 255, 0)

transparent = (231, 255, 255)

# Pre-compute often used multiples
p = 64
p2 = int(p / 2)
p4 = int(p / 4)
p4x3 = p4 * 3
p8 = int(p / 8)
p16 = int(p / 16)

# tile height difference
ph = 8


class TextSprite(pygame.sprite.Sprite):
    """Subclass of sprite to draw text to the screen"""

    def __init__(self, position, text, font, fg=(0, 0, 0), bg=None,
                 border_width=0, border_color=(0, 0, 0),
                 bold=False, italic=False, underline=False,
                 line_spacing=3, padding=5):
        pygame.sprite.Sprite.__init__(self)

        self.position = position
        self.font = font
        self.fg = fg
        self.bg = bg
        self.border_width = border_width
        self.border_color = border_color
        self.line_spacing = line_spacing
        self.padding = padding
        self.font.set_bold(bold)
        self.font.set_italic(italic)
        self.font.set_underline(underline)

        self.rect = None
        self.last_rect = None

        self.text = text
        self.update()

    def update(self):
        """"""
        textimages = []
        # Render all lines of text
        for t in self.text:
            textimages.append(self.font.render(t, False, self.fg, self.bg))

        # Find the largest width line of text
        maxwidth = max(textimages, key=lambda x: x.get_width()).get_width()
        # Produce an image to hold all of the text strings
        self.image = pygame.Surface(
            (maxwidth + 2 * (self.border_width + self.padding),
             textimages[0].get_height() * len(textimages) + self.line_spacing * (len(textimages) - 1) + 2 * (
                     self.border_width + self.padding)
             )
        )
        self.image.fill(self.bg)
        if self.border_width > 0:
            pygame.draw.rect(self.image, self.border_color,
                             (0, 0, self.image.get_width(), self.image.get_height()), self.border_width)
        for n, t in enumerate(textimages):
            self.image.blit(t, (self.border_width + self.padding,
                                self.border_width + self.padding + (self.line_spacing + t.get_height()) * n))

        # Store the last rect so if the new one is smaller we can update those bits of the screen too
        self.last_rect = self.rect
        self.rect = pygame.Rect(self.position[0], self.position[1], self.image.get_width(), self.image.get_height())

        if self.last_rect is None:
            return self.rect
        else:
            return self.last_rect.union(self.rect)


class TileSprite(pygame.sprite.Sprite):
    """Ground tiles"""
    image = None
    kind = "tile"

    @staticmethod
    def create_subsurface(rect):
        result = TileSprite.image.subsurface(rect)
        result.convert()
        result.set_colorkey((231, 255, 255), pygame.RLEACCEL)

        return result

    def __init__(self, type, xWorld, yWorld, zWorld, exclude=False):
        pygame.sprite.Sprite.__init__(self)
        if TileSprite.image is None:
            ground_image = pygame.image.load("textures.png")
            TileSprite.image = ground_image.convert()

            tile_images_keys = [
                (["CL11", "CL10", "CL01", "CR11", "CR10", "CR01"], 2),  # Left and Right cliff images
                (["0000",  # Flat tile
                  "1000", "0100", "0010", "0001",  # Corner tile (up)
                  "1001", "1100", "0110", "0011",  # Slope tile
                  "1101", "1110", "0111", "1011",  # Corner tile (down)
                  "2101", "1210", "0121", "1012",  # Two height corner
                  "1010", "0101"  # "furrow" tiles
                  ], 0)
            ]
            # Tile images will be composited using rendering later, for now just read them in
            TileSprite.tile_images = dict()
            for item in tile_images_keys:
                for idx, key in enumerate(item[0]):
                    TileSprite.tile_images[key] = self.create_subsurface((idx * p, item[1] * p, p, p))

            # Now add the highlight_images
            highlight_images_keys = [
                (["None"], 3),
                (["00XX", "01XX", "10XX", "11XX", "12XX", "21XX", "22XX"], 4),  # bottom-left edge
                (["X00X", "X01X", "X10X", "X11X", "X12X", "X21X", "X22X"], 5),  # bottom-right edge
                (["XX00", "XX01", "XX10", "XX11", "XX12", "XX21", "XX22"], 6),  # top-right edge
                (["0XX0", "1XX0", "0XX1", "1XX1", "2XX1", "1XX2", "2XX2"], 7),  # top-left edge
            ]

            TileSprite.highlight_images = dict()
            for item in highlight_images_keys:
                for idx, key in enumerate(item[0]):
                    TileSprite.highlight_images[key] = self.create_subsurface((idx * p, item[1] * p, p, p))

        self.exclude = exclude
        # x,y,zdim are the global 3D world dimensions of the object
        self.xdim = 1.0
        self.ydim = 1.0
        # Slope tiles need to have a height so that they appear correctly
        # in front of objects behind them
        # x,y,zWorld are the global 3D world coodinates of the object
        self.xWorld = xWorld
        self.yWorld = yWorld
        self.zWorld = zWorld
        self.zdim = 0
        self.type = type
        self.update()

    def calc_rect(self):
        """Calculate the current rect of this tile"""
        x = self.xWorld
        y = self.yWorld
        z = self.zWorld
        # Global screen positions
        self.xpos = World.WorldWidth2 - (x * p2) + (y * p2) - p2
        self.ypos = (x * p4) + (y * p4) - (z * ph)
        # Rect position takes into account the offset
        self.rect = (self.xpos - World.dxoff, self.ypos - World.dyoff, p, p)
        return self.rect

    def update_xyz(self):
        """Update xyz coords to match those in the array"""
        self.zWorld = World.array[self.xWorld][self.yWorld][0]
        return self.calc_rect()

    def update_type(self):
        """Update type to match those in the array"""
        self.type = self.array_to_string(World.array[self.xWorld][self.yWorld][1])

    def update(self):
        """Update sprite's rect and other attributes"""
        # What tile type should this tile be?
        self.image = TileSprite.tile_images[self.type]
        self.calc_rect()

    def change_highlight(self, type):
        """Update this tile's image with a highlight"""
        tiletype = self.type

        image = pygame.Surface((p, p))
        image.fill((231, 255, 255))
        image.blit(TileSprite.tile_images[tiletype], (0, 0))

        if type == 0:
            pass  # Empty Image
        # Corner bits, made up of two images
        elif type == 1:
            image.blit(TileSprite.highlight_images["%sXX%s" % (tiletype[0], tiletype[3])], (0, 0), (0, 0, p4, p))
            image.blit(TileSprite.highlight_images["%s%sXX" % (tiletype[0], tiletype[1])], (0, 0), (0, 0, p4, p))
        elif type == 2:
            image.blit(TileSprite.highlight_images["%s%sXX" % (tiletype[0], tiletype[1])], (p4, 0), (p4, 0, p2, p))
            image.blit(TileSprite.highlight_images["X%s%sX" % (tiletype[1], tiletype[2])], (p4, 0), (p4, 0, p2, p))
        elif type == 3:
            image.blit(TileSprite.highlight_images["X%s%sX" % (tiletype[1], tiletype[2])], (p4x3, 0), (p4x3, 0, p4, p))
            image.blit(TileSprite.highlight_images["XX%s%s" % (tiletype[2], tiletype[3])], (p4x3, 0), (p4x3, 0, p4, p))
        elif type == 4:
            image.blit(TileSprite.highlight_images["XX%s%s" % (tiletype[2], tiletype[3])], (p4, 0), (p4, 0, p2, p))
            image.blit(TileSprite.highlight_images["%sXX%s" % (tiletype[0], tiletype[3])], (p4, 0), (p4, 0, p2, p))
        # Edge bits, made up of one image
        elif type == 5:
            image.blit(TileSprite.highlight_images["%s%sXX" % (tiletype[0], tiletype[1])], (0, 0))
        elif type == 6:
            image.blit(TileSprite.highlight_images["X%s%sX" % (tiletype[1], tiletype[2])], (0, 0))
        elif type == 7:
            image.blit(TileSprite.highlight_images["XX%s%s" % (tiletype[2], tiletype[3])], (0, 0))
        elif type == 8:
            image.blit(TileSprite.highlight_images["%sXX%s" % (tiletype[0], tiletype[3])], (0, 0))
        else:
            # Otherwise highlight whole tile (4 images)
            image.blit(TileSprite.highlight_images["%s%sXX" % (tiletype[0], tiletype[1])], (0, 0))
            image.blit(TileSprite.highlight_images["X%s%sX" % (tiletype[1], tiletype[2])], (0, 0))
            image.blit(TileSprite.highlight_images["XX%s%s" % (tiletype[2], tiletype[3])], (0, 0))
            image.blit(TileSprite.highlight_images["%sXX%s" % (tiletype[0], tiletype[3])], (0, 0))

        image.set_colorkey((231, 255, 255), pygame.RLEACCEL)

        self.image = image
        self.mask = pygame.mask.from_surface(self.image)

        return self.rect

    def array_to_string(self, array):
        """Convert a heightfield array to a string"""
        return "{}{}{}{}".format(*array)


class DisplayMain(object):
    """This handles the main initialisation
    and startup for the display"""

    FPS_REFRESH = 500

    def __init__(self, width, height):
        # Initialize PyGame
        pygame.init()

        # Initiate the clock
        self.clock = pygame.time.Clock()

        # Set the window Size
        self.screen_width = width
        self.screen_height = height

        # Create the Screen
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)

        # tell pygame to keep sending up keystrokes when they are held down
        pygame.key.set_repeat(500, 30)

        # Setup fonts
        self.font = pygame.font.Font(None, 12)

        self.refresh_screen = 1

        self.ordered_sprites = pygame.sprite.LayeredUpdates()
        self.ordered_sprites_dict = {}

    def MainLoop(self):
        """This is the Main Loop of the Game"""
        self.paint_world()

        # Sprite used to find what the cursor is selecting
        self.mouseSprite = None
        # Settings for FPS counter
        self.fps_refresh = DisplayMain.FPS_REFRESH
        self.fps_elapsed = 0
        # Associated with user input
        self.last_mouse_position = pygame.mouse.get_pos()

        # Tools have some global settings/properties, like x/ydims (which determine working area)
        # When tool isn't actually being used it's still updated, to provide highlighting info
        # Most basic tool is the "inspection tool", this will highlight whatever it's over including tiles
        # Terrain raise/lower tool, live preview of affected area
        # Terrain leveling tool, click and drag to select area
        self.lmb_tool = tools.Terrain()
        self.rmb_tool = tools.Move()

        # overlay_sprites is for text that overlays the terrain in the background
        self.overlay_sprites = pygame.sprite.LayeredUpdates()

        # Set up instructions font
        instructions_font = pygame.font.SysFont(pygame.font.get_default_font(), size=20)
        # Make a text sprite to display the instructions
        self.active_tool_sprite = TextSprite(
            (10, 10), ["Terrain modification"],
            instructions_font,
            fg=(0, 0, 0),
            bg=(255, 255, 255),
            bold=False)
        self.overlay_sprites.add(self.active_tool_sprite, layer=100)

        while True:
            self.clock.tick(0)
            # If there's a quit event, don't bother parsing the event queue
            if pygame.event.peek(pygame.QUIT):
                pygame.display.quit()
                sys.exit()

            # Clear the stack of dirty tiles
            self.dirty = []

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F12:
                        pygame.image.save(self.screen, "pytile_sc.png")
                    if not self.lmb_tool.process_key(event.key):
                        # process_key() will always return False if it hasn't processed the key,
                        # so that keys can be used for other things if a tool doesn't want them
                        if event.key == pygame.K_t:
                            # Activate track drawing mode
                            self.lmb_tool = tools.Track()
                            self.active_tool_sprite.text = ["Track drawing"]
                            self.dirty.append(self.active_tool_sprite.update())
                        if event.key == pygame.K_h:
                            # Activate terrain modification mode
                            self.lmb_tool = tools.Terrain()
                            self.active_tool_sprite.text = ["Terrain modification"]
                            self.dirty.append(self.active_tool_sprite.update())

                        # Some tools may use the escape key
                        if event.key == pygame.K_ESCAPE:
                            pygame.display.quit()
                            sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    # LMB
                    if event.button == 1:
                        self.lmb_tool.mouse_down(event.pos, self.ordered_sprites)
                    # RMB
                    if event.button == 3:
                        self.rmb_tool.mouse_down(event.pos, self.ordered_sprites)
                if event.type == pygame.MOUSEBUTTONUP:
                    # LMB
                    if event.button == 1:
                        self.lmb_tool.mouse_up(event.pos, self.ordered_sprites)
                    # RMB
                    if event.button == 3:
                        self.rmb_tool.mouse_up(event.pos, self.ordered_sprites)
                if event.type == pygame.MOUSEMOTION:
                    # LMB is pressed, update all the time to keep highlight working
                    self.lmb_tool.mouse_move(event.pos, self.ordered_sprites)
                    # RMB is pressed, only update while RMB pressed
                    if event.buttons[2] == 1:
                        self.rmb_tool.mouse_move(event.pos, self.ordered_sprites)
                if event.type == pygame.VIDEORESIZE:
                    self.screen_width = event.w
                    self.screen_height = event.h
                    self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
                    self.paint_world()
                    self.refresh_screen = 1

            if self.lmb_tool.has_aoe_changed():
                # Update the screen to reflect changes made by tools
                aoe = self.lmb_tool.get_last_aoe() + self.lmb_tool.get_aoe()
                self.update_world(aoe, self.lmb_tool.get_highlight())
                self.lmb_tool.set_aoe_changed(False)
                self.lmb_tool.clear_aoe()

            if self.rmb_tool.active():
                # Repaint the entire screen until something better is implemented
                self.paint_world()
                self.refresh_screen = 1

            # Write some useful info on the top bar
            self.fps_elapsed += self.clock.get_time()
            if self.fps_elapsed >= self.fps_refresh:
                self.fps_elapsed = 0
                ii = self.lmb_tool.tile
                if ii:
                    layer = self.ordered_sprites.get_layer_of_sprite(ii)
                    pygame.display.set_caption(
                        "FPS: %i | Tile: (%s,%s) of type: %s, layer: %s | dxoff: %s dyoff: %s" %
                        (self.clock.get_fps(), ii.xWorld, ii.yWorld, ii.type, layer, World.dxoff,
                         World.dyoff))
                else:
                    pygame.display.set_caption(
                        "FPS: %i | dxoff: %s dyoff: %s" %
                        (self.clock.get_fps(), World.dxoff, World.dyoff))

            # If land height has been altered, or the screen has been moved
            # we need to refresh the entire screen
            if self.refresh_screen == 1:
                self.screen.fill((0, 0, 0))
                self.ordered_sprites.draw(self.screen)
                self.overlay_sprites.draw(self.screen)
                pygame.display.update()
                self.refresh_screen = 0
            else:
                for r in self.dirty:
                    self.screen.fill((0, 0, 0), r)

                self.ordered_sprites.draw(self.screen)
                self.overlay_sprites.draw(self.screen)
                pygame.display.update(self.dirty)

    @staticmethod
    def array_to_string(array):
        """Convert a heightfield array to a string"""
        return "%s%s%s%s" % (array[0], array[1], array[2], array[3])

    def update_world(self, tiles, highlight=None):
        """Instead of completely regenerating the entire world, just update certain tiles"""
        # Add all the items in tiles to the checked_nearby hash table
        nearbytiles = []
        for t in tiles:
            x, y = t
            # Also need to look up tiles at (x-1,y) and (x,y-1) and have them re-evaluate their cliffs too
            # This needs to check that a) that tile hasn't already been re-evaluated and that
            # b) that tile isn't one of the ones which we're checking, i.e. not in tiles
            if not (x - 1, y) in tiles and not (x - 1, y) in nearbytiles:
                nearbytiles.append((x - 1, y))

            if not (x, y - 1) in tiles and not (x, y - 1) in nearbytiles:
                nearbytiles.append((x, y - 1))
        # This is a direct reference back to the aoe specified in the tool,
        # need to make a copy to use this!
        tiles.extend(nearbytiles)
        for t in tiles:
            x, y = t
            # If an override is defined in highlight for this tile,
            # update based on that rather than on contents of World
            if highlight and (x, y) in highlight:
                tile = highlight[(x, y)]
            else:
                tile = World.array[x][y]
            # Look the tile up in the group using the position, this will give us the tile and all its cliffs
            if (x, y) in self.ordered_sprites_dict:
                tileset = self.ordered_sprites_dict[(x, y)]
                t = tileset[0]
                # Add old positions to dirty rect list
                self.dirty.append(t.rect)

                # Calculate layer
                l = self.get_layer(x, y)

                # Update the tile type
                t.update_type()
                # Update the tile image
                t.update()
                # Update cursor highlight for tile (if it has one)
                try:
                    tile[3]
                except IndexError:
                    pass
                else:
                    t.change_highlight(tile[3])
                self.dirty.append(t.update_xyz())

                self.ordered_sprites.remove(tileset)
                # Recreate the cliffs
                cliffs = self.make_cliffs(x, y)
                cliffs.insert(0, t)

                # Add the regenerated sprites back into the appropriate places
                self.ordered_sprites_dict[(x, y)] = cliffs
                self.ordered_sprites.add(cliffs, layer=l)

    @staticmethod
    def get_layer(x, y):
        """Return the layer a sprite should be based on some parameters"""
        return (x + y) * 10

    def paint_world(self, highlight=None):
        """Paint the world as a series of sprites
        Includes ground and other objects"""
        # highlight defines tiles which should override the tiles stored in World
        # can be accessed in the same way as World
        self.refresh_screen = 1
        self.ordered_sprites.empty()  # This doesn't necessarily delete the sprites though?
        self.ordered_sprites_dict = {}
        # Top-left of view relative to world given by self.dxoff, self.dyoff
        # Find the base-level tile at this position
        top_left_tile_y, top_left_tile_x = self.screen_to_iso(World.dxoff, World.dyoff)
        for x1 in range(int(self.screen_width / p + 1)):
            for y1 in range(int(self.screen_height / p4)):
                x = int(top_left_tile_x - x1 + math.ceil(y1 / 2.0))
                y = int(top_left_tile_y + x1 + math.floor(y1 / 2.0))
                add_to_dict = []
                # Tile must be within the bounds of the map
                if (x >= 0 and y >= 0) and (x < World.WorldX and y < World.WorldY):
                    # If an override is defined in highlight for this tile,
                    # update based on that rather than on contents of World
                    if highlight and (x, y) in highlight:
                        tile = highlight[(x, y)]
                    else:
                        tile = World.array[x][y]
                    l = self.get_layer(x, y)
                    # Add the main tile
                    tile_type = self.array_to_string(tile[1])
                    t = TileSprite(tile_type, x, y, tile[0], exclude=False)
                    # Update cursor highlight for tile (if it has one)
                    try:
                        tile[3]
                    except IndexError:
                        pass
                    else:
                        t.change_highlight(tile[3])

                    add_to_dict.append(t)
                    self.ordered_sprites.add(t, layer=l)

                    # Add vertical surfaces (cliffs) for this tile (if any)
                    for t in self.make_cliffs(x, y):
                        add_to_dict.append(t)
                        self.ordered_sprites.add(t, layer=l)
                    self.ordered_sprites_dict[(x, y)] = add_to_dict

    @staticmethod
    def make_cliffs(x, y):
        """Produce a set of cliff sprites to go with a particular tile"""
        result = []
        # a1/a2 are top and right vertices of tile in front/left of the one we're testing
        if x == World.WorldX - 1:
            a1 = 0
            a2 = 0
        else:
            a1 = World.array[x + 1][y][1][3] + World.array[x + 1][y][0]
            a2 = World.array[x + 1][y][1][2] + World.array[x + 1][y][0]

        # b1/b2 are left and bottom vertices of tile we're testing
        b1 = World.array[x][y][1][0] + World.array[x][y][0]
        b2 = World.array[x][y][1][1] + World.array[x][y][0]

        while b1 > a1 or b2 > a2:
            if b1 > b2:
                b1 -= 1
                tile_type = "CL10"
            elif b1 == b2:
                b1 -= 1
                b2 -= 1
                tile_type = "CL11"
            else:
                b2 -= 1
                tile_type = "CL01"

            result.append(TileSprite(tile_type, x, y, b1, exclude=True))

        # a1/a2 are top and right vertices of tile in front/right of the one we're testing
        if y == World.WorldY - 1:
            a1 = 0
            a2 = 0
        else:
            a1 = World.array[x][y + 1][1][3] + World.array[x][y + 1][0]
            a2 = World.array[x][y + 1][1][0] + World.array[x][y + 1][0]

        # b1/b2 are left and bottom vertices of tile we're testing
        b1 = World.array[x][y][1][2] + World.array[x][y][0]
        b2 = World.array[x][y][1][1] + World.array[x][y][0]

        while b1 > a1 or b2 > a2:
            if b1 > b2:
                b1 -= 1
                tile_type = "CR10"
            elif b1 == b2:
                b1 -= 1
                b2 -= 1
                tile_type = "CR11"
            else:
                b2 -= 1
                tile_type = "CR01"

            result.append(TileSprite(tile_type, x, y, b1, exclude=True))

        return result

    @staticmethod
    def screen_to_iso(wx, wy):
        """Convert screen coordinates to Iso world coordinates
        returns tuple of iso coords"""
        tile_ratio = 2.0

        # Convert coordinates to be relative to the position of tile (0,0)
        dx = wx - World.WorldWidth2
        dy = wy - p2

        # Do some maths
        x = int((dy + (dx / tile_ratio)) / p2)
        y = int((dy - (dx / tile_ratio)) / p2)

        return x, y


if __name__ == "__main__":
    import os

    os.environ["SDL_VIDEO_CENTERED"] = "1"
    WINDOW_WIDTH = 1024
    WINDOW_HEIGHT = 768
    MainWindow = DisplayMain(WINDOW_WIDTH, WINDOW_HEIGHT)
    MainWindow.MainLoop()
