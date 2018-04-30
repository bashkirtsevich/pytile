import math
import sys

import pygame

import tools
import world
from text_sprite import TextSprite

World = world.World()

# Pre-compute often used multiples
p = 64
p2 = int(p / 2)
p4 = int(p / 4)
p4x3 = p4 * 3
p8 = int(p / 8)
p16 = int(p / 16)

# tile height difference
ph = 8


class TileSprite(pygame.sprite.Sprite):
    """Ground tiles"""
    image = None
    kind = "tile"
    tile_images = dict()
    highlight_images = dict()

    def __init__(self, type_, x_world, y_world, z_world, exclude=False):
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

            for item in highlight_images_keys:
                for idx, key in enumerate(item[0]):
                    TileSprite.highlight_images[key] = self.create_subsurface((idx * p, item[1] * p, p, p))

        self.exclude = exclude
        # x,y,zdim are the global 3D world dimensions of the object
        self.x_dim = 1.0
        self.y_dim = 1.0
        # Slope tiles need to have a height so that they appear correctly
        # in front of objects behind them
        # x,y,zWorld are the global 3D world coodinates of the object
        self.x_world = x_world
        self.y_world = y_world
        self.z_world = z_world
        self.z_dim = 0
        self.type = type_
        self.x_pos = None
        self.y_pos = None
        self.rect = None

        self.update()

    @staticmethod
    def create_subsurface(rect):
        result = TileSprite.image.subsurface(rect)
        result.convert()
        result.set_colorkey((231, 255, 255), pygame.RLEACCEL)

        return result

    def calc_rect(self):
        """Calculate the current rect of this tile"""
        x = self.x_world
        y = self.y_world
        z = self.z_world
        # Global screen positions
        self.x_pos = World.WorldWidth2 - (x * p2) + (y * p2) - p2
        self.y_pos = (x * p4) + (y * p4) - (z * ph)
        # Rect position takes into account the offset
        self.rect = (self.x_pos - World.dxoff, self.y_pos - World.dyoff, p, p)
        return self.rect

    def update_xyz(self):
        """Update xyz coords to match those in the array"""
        self.z_world = World.array[self.x_world][self.y_world][0]
        return self.calc_rect()

    def update_type(self):
        """Update type to match those in the array"""
        self.type = self.array_to_string(World.array[self.x_world][self.y_world][1])

    def update(self):
        """Update sprite's rect and other attributes"""
        # What tile type should this tile be?
        self.image = TileSprite.tile_images[self.type]
        self.calc_rect()

    def change_highlight(self, type_):
        """Update this tile's image with a highlight"""
        tile_type = self.type

        image = pygame.Surface((p, p))
        image.fill((231, 255, 255))
        image.blit(TileSprite.tile_images[tile_type], (0, 0))

        if type_ == 0:
            sprite_info = []  # Empty Image
        # Corner bits, made up of two images
        elif type_ == 1:
            sprite_info = [
                ("%sXX%s" % (tile_type[0], tile_type[3]), (0, 0), (0, 0, p4, p)),
                ("%s%sXX" % (tile_type[0], tile_type[1]), (0, 0), (0, 0, p4, p))
            ]
        elif type_ == 2:
            sprite_info = [
                ("%s%sXX" % (tile_type[0], tile_type[1]), (p4, 0), (p4, 0, p2, p)),
                ("X%s%sX" % (tile_type[1], tile_type[2]), (p4, 0), (p4, 0, p2, p))
            ]
        elif type_ == 3:
            sprite_info = [
                ("X%s%sX" % (tile_type[1], tile_type[2]), (p4x3, 0), (p4x3, 0, p4, p)),
                ("XX%s%s" % (tile_type[2], tile_type[3]), (p4x3, 0), (p4x3, 0, p4, p))
            ]
        elif type_ == 4:
            sprite_info = [
                ("XX%s%s" % (tile_type[2], tile_type[3]), (p4, 0), (p4, 0, p2, p)),
                ("%sXX%s" % (tile_type[0], tile_type[3]), (p4, 0), (p4, 0, p2, p))
            ]
        # Edge bits, made up of one image
        elif type_ == 5:
            sprite_info = [
                ("%s%sXX" % (tile_type[0], tile_type[1]), (0, 0), None)
            ]
        elif type_ == 6:
            sprite_info = [
                ("X%s%sX" % (tile_type[1], tile_type[2]), (0, 0), None)
            ]
        elif type_ == 7:
            sprite_info = [
                ("XX%s%s" % (tile_type[2], tile_type[3]), (0, 0), None)
            ]
        elif type_ == 8:
            sprite_info = [
                ("%sXX%s" % (tile_type[0], tile_type[3]), (0, 0), None)
            ]
        else:
            # Otherwise highlight whole tile (4 images)
            sprite_info = [
                ("%s%sXX" % (tile_type[0], tile_type[1]), (0, 0), None),
                ("X%s%sX" % (tile_type[1], tile_type[2]), (0, 0), None),
                ("XX%s%s" % (tile_type[2], tile_type[3]), (0, 0), None),
                ("%sXX%s" % (tile_type[0], tile_type[3]), (0, 0), None),
            ]

        for img_key, dest, area in sprite_info:
            image.blit(TileSprite.highlight_images[img_key], dest, area)

        image.set_colorkey((231, 255, 255), pygame.RLEACCEL)

        self.image = image
        self.mask = pygame.mask.from_surface(self.image)

        return self.rect

    @staticmethod
    def array_to_string(array):
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

        self.refresh_screen = True

        self.ordered_sprites = pygame.sprite.LayeredUpdates()
        self.ordered_sprites_dict = {}

        # Sprite used to find what the cursor is selecting
        self.mouse_sprite = None
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

        # Clear the stack of dirty tiles
        self.dirty = []

    def main_loop(self):
        """This is the Main Loop of the Game"""
        while True:
            self.clock.tick(0)
            # If there's a quit event, don't bother parsing the event queue
            if pygame.event.peek(pygame.QUIT):
                pygame.display.quit()
                sys.exit()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F12:
                        pygame.image.save(self.screen, "pytile_sc.png")
                    if not self.lmb_tool.process_key(event.key):
                        # process_key() will always return False if it hasn't processed the key,
                        # so that keys can be used for other things if a tool doesn't want them
                        if event.key == pygame.K_h:
                            # Activate terrain modification mode
                            self.lmb_tool = tools.Terrain()
                            self.active_tool_sprite.text_lines = ["Terrain modification"]
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
                    self.refresh_screen = True

            if self.lmb_tool.has_aoe_changed():
                # Update the screen to reflect changes made by tools
                aoe = self.lmb_tool.get_last_aoe() + self.lmb_tool.get_aoe()
                self.update_world(aoe, self.lmb_tool.get_highlight())
                self.lmb_tool.set_aoe_changed(False)
                self.lmb_tool.clear_aoe()

            if self.rmb_tool.active():
                # Repaint the entire screen until something better is implemented
                self.paint_world()
                self.refresh_screen = True

            # Write some useful info on the top bar
            self.fps_elapsed += self.clock.get_time()
            if self.fps_elapsed >= self.fps_refresh:
                self.fps_elapsed = 0
                ii = self.lmb_tool.tile
                if ii:
                    layer = self.ordered_sprites.get_layer_of_sprite(ii)
                    pygame.display.set_caption(
                        "FPS: %i | Tile: (%s,%s) of type: %s, layer: %s | dxoff: %s dyoff: %s" %
                        (self.clock.get_fps(), ii.x_world, ii.y_world, ii.type, layer, World.dxoff,
                         World.dyoff))
                else:
                    pygame.display.set_caption(
                        "FPS: %i | dxoff: %s dyoff: %s" %
                        (self.clock.get_fps(), World.dxoff, World.dyoff))

            # If land height has been altered, or the screen has been moved
            # we need to refresh the entire screen
            if self.refresh_screen:
                self.screen.fill((0, 0, 0))
                self.ordered_sprites.draw(self.screen)
                self.overlay_sprites.draw(self.screen)
                pygame.display.update()
                self.refresh_screen = False
            else:
                for r in self.dirty:
                    self.screen.fill((0, 0, 0), r)

                self.ordered_sprites.draw(self.screen)
                self.overlay_sprites.draw(self.screen)
                pygame.display.update(self.dirty)

    @staticmethod
    def array_to_string(array):
        """Convert a heightfield array to a string"""
        return "{}{}{}{}".format(*array)

    def update_world(self, tiles, highlight=None):
        """Instead of completely regenerating the entire world, just update certain tiles"""
        # Add all the items in tiles to the checked_nearby hash table
        nearby_tiles = []
        for t in tiles:
            x, y = t
            # Also need to look up tiles at (x-1,y) and (x,y-1) and have them re-evaluate their cliffs too
            # This needs to check that a) that tile hasn't already been re-evaluated and that
            # b) that tile isn't one of the ones which we're checking, i.e. not in tiles
            if (x - 1, y) not in tiles and (x - 1, y) not in nearby_tiles:
                nearby_tiles.append((x - 1, y))

            if (x, y - 1) not in tiles and (x, y - 1) not in nearby_tiles:
                nearby_tiles.append((x, y - 1))

        # This is a direct reference back to the aoe specified in the tool,
        # need to make a copy to use this!
        tiles.extend(nearby_tiles)

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
                tile_set = self.ordered_sprites_dict[(x, y)]
                t = tile_set[0]
                # Add old positions to dirty rect list
                self.dirty.append(t.rect)

                # Calculate layer
                layer = self.get_layer(x, y)

                # Update the tile type
                t.update_type()
                # Update the tile image
                t.update()
                # Update cursor highlight for tile (if it has one)
                if len(tile) >= 4:
                    t.change_highlight(tile[3])
                self.dirty.append(t.update_xyz())

                self.ordered_sprites.remove(tile_set)
                # Recreate the cliffs
                cliffs = self.make_cliffs(x, y)
                cliffs.insert(0, t)

                # Add the regenerated sprites back into the appropriate places
                self.ordered_sprites_dict[(x, y)] = cliffs
                self.ordered_sprites.add(cliffs, layer=layer)

    @staticmethod
    def get_layer(x, y):
        """Return the layer a sprite should be based on some parameters"""
        return (x + y) * 10

    def paint_world(self, highlight=None):
        """Paint the world as a series of sprites
        Includes ground and other objects"""
        # highlight defines tiles which should override the tiles stored in World
        # can be accessed in the same way as World
        self.refresh_screen = True
        self.ordered_sprites.empty()  # This doesn't necessarily delete the sprites though?
        self.ordered_sprites_dict = {}
        # Top-left of view relative to world given by self.dxoff, self.dyoff
        # Find the base-level tile at this position
        top_left_tile_y, top_left_tile_x = self.screen_to_iso(World.dxoff, World.dyoff)
        for x1 in range(int(self.screen_width / p + 1)):
            for y1 in range(int(self.screen_height / p4)):
                x = int(top_left_tile_x - x1 + math.ceil(y1 / 2.0))
                y = int(top_left_tile_y + x1 + math.floor(y1 / 2.0))

                # Tile must be within the bounds of the map
                if (x >= 0 and y >= 0) and (x < World.WorldX and y < World.WorldY):
                    # If an override is defined in highlight for this tile,
                    # update based on that rather than on contents of World
                    if highlight and (x, y) in highlight:
                        tile = highlight[(x, y)]
                    else:
                        tile = World.array[x][y]
                    layer = self.get_layer(x, y)
                    # Add the main tile
                    tile_type = self.array_to_string(tile[1])
                    t = TileSprite(tile_type, x, y, tile[0], exclude=False)
                    add_to_dict = [t]

                    # Update cursor highlight for tile (if it has one)
                    if len(tile) >= 4:
                        t.change_highlight(tile[3])

                    self.ordered_sprites.add(t, layer=layer)

                    # Add vertical surfaces (cliffs) for this tile (if any)
                    for t in self.make_cliffs(x, y):
                        add_to_dict.append(t)
                        self.ordered_sprites.add(t, layer=layer)
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
    MainWindow.main_loop()
