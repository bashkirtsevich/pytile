import copy

import pygame

import world

World = world.World()

# Pre-compute often used multiples
p = 64
p2 = int(p / 2)
p4 = int(p / 4)
p4x3 = int(p4 * 3)
p8 = int(p / 8)
p16 = int(p / 16)

# tile height difference
ph = 8


class MouseSprite(pygame.sprite.Sprite):
    """Small invisible sprite to use for mouse/sprite collision testing"""
    # This sprite never gets drawn, so no need to worry about what it looks like
    image = None
    mask = None

    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        if MouseSprite.image is None:
            MouseSprite.image = pygame.Surface((1, 1))
            MouseSprite.image.fill((1, 1, 1))
            MouseSprite.image.set_colorkey((0, 0, 0), pygame.RLEACCEL)

        if MouseSprite.mask is None:
            MouseSprite.mask = pygame.mask.from_surface(MouseSprite.image)

        self.mask = MouseSprite.mask
        self.image = MouseSprite.image
        self.rect = pygame.Rect(x, y, 1, 1)

    def update(self, x, y):
        self.rect = pygame.Rect(x, y, 1, 1)


class Tool(object):
    """Methods which all tools can access"""

    def __init__(self):
        """"""
        self.mouseSprite = False

        # The tile found through collision detection
        self.tile = None
        # The subtile of that tile
        self.subtile = None
        # Setup highlight vars
        self.highlight_changed = False
        self.highlight = {}
        # Setup aoe vars
        self.aoe_changed = False
        self.aoe = []
        self.last_aoe = []

    def active(self):
        """Return true if tool currently being used and screen needs updating
        This method is only used for RMB tools, other tools use has_aoe_changed()
        and update the AOE of the tool"""
        return True

    def process_key(self, key):
        """Process keystrokes sent to this tool"""
        pygame.key.name(key)
        return False

    def mouse_down(self, position, collisionlist):
        """Mouse button DOWN"""
        pass

    def mouse_up(self, position, collisionlist):
        """Mouse button UP"""
        pass

    def mouse_move(self, position, collisionlist):
        """Tool updated, current cursor position is newpos"""
        pass

    # AOE related access functions
    def get_aoe(self):
        """Return the current area of effect for this tool"""
        return self.aoe

    def get_last_aoe(self):
        """Return the current area of effect for this tool"""
        return self.last_aoe

    def has_aoe_changed(self):
        """Return True if the area of effect of this tool has changed since the last call to this function"""
        return self.aoe_changed

    def set_aoe_changed(self, v):
        """On aoe change set to True to let main loop know to redraw changed area of screen"""
        self.aoe_changed = v
        return True

    def clear_aoe(self):
        """Clear the area of effect, changes only drawn if aoe_changed returns True"""
        self.last_aoe = copy.copy(self.aoe)
        self.aoe = []
        return True

    # Commonly used aoe-producing functions
    def find_rect_aoe(self, x, y):
        """Return a list of tiles for the primary area of effect of the tool based on a box pattern"""
        tiles = []
        for xx in range(self.xdims):
            for yy in range(self.ydims):
                # Tiles in aoe must be within the bounds of the World
                if x + xx < World.WorldX and y + yy < World.WorldY:
                    tiles.append((x + xx, y + yy))
        return tiles

    # Highlight related access functions
    def get_highlight(self):
        """Return the current highlight area for this tool"""
        return self.highlight

    def set_highlight(self, value):
        """Set the current highlight for this tool"""
        self.highlight = value
        return True

    def collide_locate(self, mousepos, collideagainst):
        """Locates the sprite(s) that the mouse position intersects with"""
        # Draw mouseSprite at cursor position
        if self.mouseSprite:
            self.mouseSprite.sprite.update(*mousepos)
        else:
            self.mouseSprite = pygame.sprite.GroupSingle(MouseSprite(*mousepos))
        # Find sprites that the mouseSprite intersects with
        collision_list1 = pygame.sprite.spritecollide(self.mouseSprite.sprite, collideagainst, False)
        if collision_list1:
            collision_list = pygame.sprite.spritecollide(
                self.mouseSprite.sprite, collision_list1, False, pygame.sprite.collide_mask)
            if collision_list:
                collision_list.reverse()
                for t in collision_list:
                    if not t.exclude:
                        return t
                return None
            else:
                # No collision means nothing to select
                return None
        else:
            return None

    @staticmethod
    def subtile_position(mousepos, tile):
        """Find the sub-tile position of the cursor"""
        x = tile.x_world
        y = tile.y_world
        # Find where this tile would've been drawn on the screen, and subtract the mouse's position
        mousex, mousey = mousepos
        posx = World.WorldWidth2 - (x * (p2)) + (y * (p2)) - p2
        posy = x * p4 + y * p4 - World.array[x][y][0] * ph
        offx = mousex - (posx - World.dxoff)
        offy = mousey - (posy - World.dyoff)
        # Then compare these offsets to the table of values for this particular kind of tile
        # to find which overlay selection sprite should be drawn
        # Height in 16th incremenets, width in 8th increments
        offx8 = int(offx / p8)
        offy16 = int(offy / p16)
        # Then lookup the mask number based on this, this should be drawn on the screen
        try:
            tilesubposition = World.type[tile.type][offy16][offx8]
            return tilesubposition
        except IndexError:
            # print("offy16: %s, offx8: %s, coltile: %s" % (offy16, offx8, tile.type))
            return None


class Move(Tool):
    """Screen movement tool"""

    def __init__(self):
        """First time the Move tool is used"""
        super().__init__()
        self.start = None
        self.current = None

    def active(self):
        """Return true if tool currently being used and screen needs updating"""
        return bool(self.start)

    def mouse_down(self, position, collisionlist):
        """"""
        self.start = position

    def mouse_up(self, position, collisionlist):
        """"""
        self.current = position
        self.start = None

    def mouse_move(self, position, collisionlist):
        """"""
        self.current = position
        if self.start:
            self.move_screen(self.start, self.current)
        self.start = self.current

    @staticmethod
    def move_screen(start, end):
        """Move the screen on mouse input"""
        start_x, start_y = start
        end_x, end_y = end
        rel_x = start_x - end_x
        rel_y = start_y - end_y
        World.set_offset(World.dxoff + rel_x, World.dyoff + rel_y)


class Terrain(Tool):
    """Terrain modification tool"""
    # Variables that persist through instances of this tool
    # Reference with Terrain.var
    xdims = 1
    ydims = 1
    smooth = False

    def __init__(self):
        """First time the Terrain tool is used"""
        # Call init method of parent
        super().__init__()
        # tiles - all the tiles in the primary area of effect (ones which are modified first)
        self.tiles = []
        # Other variables used
        self.start = None

    def process_key(self, key):
        """Process keystrokes sent to this tool"""
        keyname = pygame.key.name(key)
        ret = False
        if keyname == "k":
            Terrain.xdims += 1
            ret = True
        elif keyname == "o":
            Terrain.xdims -= 1
            if Terrain.xdims < 1:
                Terrain.xdims = 1
            ret = True
        elif keyname == "l":
            Terrain.ydims += 1
            ret = True
        elif keyname == "i":
            Terrain.ydims -= 1
            if Terrain.ydims < 1:
                Terrain.ydims = 1
            ret = True
        elif keyname == "s":
            Terrain.smooth = not Terrain.smooth
            ret = True
        if keyname in ["i", "o", "k", "l"]:
            if self.tile:
                self.set_highlight(self.find_highlight(self.tile.x_world, self.tile.y_world, self.subtile))
                self.set_aoe_changed(True)
                self.aoe = self.find_rect_aoe(self.tile.x_world, self.tile.y_world)
            ret = True
        return ret

    def find_highlight(self, x, y, subtile):
        """Find the primary area of effect of the tool, based on tool dimensions
        Return a list of tiles to modify in [(x,y), modifier] form
        Used to specify region which will be highlighted"""
        tiles = {}
        if self.xdims > 1 or self.ydims > 1:
            for xx in range(self.xdims):
                for yy in range(self.ydims):
                    try:
                        World.array[x + xx][y + yy]
                    except IndexError:
                        pass
                    else:
                        t = copy.copy(World.array[x + xx][y + yy])
                        if len(t) == 2:
                            t.append([])
                        t.append(9)
                        tiles[(x + xx, y + yy)] = t
        else:
            t = copy.copy(World.array[x][y])
            if len(t) == 2:
                t.append([])
            t.append(subtile)
            tiles[(x, y)] = t
        return tiles

    def mouse_down(self, position, collisionlist):
        """Reset the start position for a new operation"""
        self.start = position
        self.addback = 0

    def mouse_up(self, position, collisionlist):
        """End of application of tool"""
        self.current = position
        self.tiles = []
        self.start = None

    def mouse_move(self, position, collisionlist):
        """Tool updated, current cursor position is newpos"""
        # If start is None, then there's no dragging operation ongoing, just update the position of the highlight
        self.current = position
        if self.start is None:
            tile = self.collide_locate(self.current, collisionlist)
            # print("tile is: %s" % tile)
            if tile and not tile.exclude:
                subtile = self.subtile_position(self.current, tile)
                # Only update the highlight if the cursor has changed enough to require it
                if tile != self.tile or subtile != self.subtile:
                    self.set_highlight(self.find_highlight(tile.x_world, tile.y_world, subtile))
                    self.set_aoe_changed(True)
                    self.aoe = self.find_rect_aoe(tile.x_world, tile.y_world)
                else:
                    self.set_aoe_changed(False)
                self.tile = tile
                self.subtile = subtile
            else:
                self.set_highlight({})
                self.set_aoe_changed(True)
                self.tile = None
                self.subtile = None
        # Otherwise a drag operation is on-going, do usual tool behaviour
        else:
            # If we don't already have a list of tiles to use as the primary area of effect
            if not self.tiles:
                tile = self.collide_locate(self.current, collisionlist)
                if tile and not tile.exclude:
                    subtile = self.subtile_position(self.current, tile)
                    self.tiles = self.find_rect_aoe(tile.x_world, tile.y_world)
                    # Tiles now contains the primary area of effect for this operation
                    self.tile = tile
                    self.subtile = subtile

            # We keep track of the mouse position in the y dimension, as it moves it ticks over 
            # in ph size increments each time it does this we remove a ph size increment from 
            # the start location, so that next time we start from the right place. If when we 
            # actually try to modify the terrain by that number of ticks we find we're unable 
            # to (e.g. we've hit a terrain limit) and the modification is less than the 
            # requested modification the start position needs to be offset such that we have 
            # to "make back" that offset.

            # Coord system is from top-left corner, down = -ve, up = +ve, so do start pos - end pos
            # This gets us the number of units to move up or down by
            diff = int((self.start[1] - self.current[1]) / ph)
            self.start = (self.start[0], self.start[1] - diff * ph)

            # If diff < 0 we're lowering terrain, if diff > 0 we're raising it
            # If raising, check if addback is positive, if so we need to zero out addback before doing any raising
            # to the terrain
            if diff > 0:
                while self.addback > 0:
                    if diff == 0:
                        break
                    diff -= 1
                    self.addback -= 1

            if diff != 0:
                if len(self.tiles) > 1:
                    r = self.modify_tiles(self.tiles, diff, soft=Terrain.smooth)
                else:
                    r = self.modify_tiles(self.tiles, diff, subtile=self.subtile, soft=Terrain.smooth)
                # Addback is calcuated as the actual height change minus the requested height change. 
                # The remainder is the amount of cursor movement which doesn't actually do anything.
                # For example, if the cursor moves down (lowering the terrain) and hits the "0" level
                # of the terrain we can't continue to lower the terrain. The cursor keeps moving 
                # however and the addback value keeps track of this so that when the cursor starts to 
                # move up it won't start raising the terrain until it hits the "0" level again

                # If we're lowering, update addback if necessary
                if diff < 0:
                    self.addback += r - diff

                # Set this so that the changed portion of the map is updated on screen
                self.set_aoe_changed(True)

    def modify_tiles(self, tiles, amount, subtile=9, soft=False):
        """Raise or lower a region of tiles"""
        # r measures the total amount of raising/lowering *actually* done
        # This can then be compared with the amount requested to calculate the cursor offset
        r = 0
        # The area of effect of the tool (list of tiles modified)
        self.aoe = []
        # This will always be a whole tile raise/lower
        # If subtile is None, this is always a whole tile raise/lower
        # If subtile is something, and there's only one tile in the array then this is a single tile action
        # If subtile is something, and there's more than one tile in the array then this is a multi-tile action,
        # but based
        #   off a vertex rather than a face
        vertices = []
        # Lowering terrain, find maximum value to start from
        if amount < 0:
            for t in tiles:
                x = t[0]
                y = t[1]
                tgrid = World.get_height(x, y)
                if tgrid:
                    vertices.append([tgrid.height + max(tgrid.array), (x, y)])
                    self.aoe.append((x, y))
            step = -1
            for i in range(0, amount, step):
                maxval = max(vertices, key=lambda x: x[0])[0]
                if maxval != 0:
                    rr = 0
                    for point in vertices:
                        if point[0] == maxval:
                            point[0] -= 1
                            # Whole tile lower
                            if subtile == 9:
                                tgrid = World.get_height(point[1])
                                rr = tgrid.lower_face()
                                World.set_height(tgrid, point[1])
                            # Edge lower
                            elif subtile in [5, 6, 7, 8]:
                                st1 = subtile - 5
                                st2 = st1 + 1
                                tgrid = World.get_height(point[1])
                                rr = tgrid.lower_edge(st1, st2)
                                World.set_height(tgrid, point[1])
                            # Vertex lower
                            elif subtile in [1, 2, 3, 4]:
                                tgrid = World.get_height(point[1])
                                rr = tgrid.lower_vertex(subtile - 1)
                                World.set_height(tgrid, point[1])
                    # Since we're potentially modifying a large number of individual tiles we only want to know if
                    # *any* of them were lowered for the purposes of calculating the real raise/lower amount
                    # Thus r should only be incremented once per raise/lower level
                    r += rr
            if soft:
                # Soften around the modified tiles
                self.soften(self.aoe, soften_down=True)
        # Raising terrain, find minimum value to start from
        else:
            for t in tiles:
                x = t[0]
                y = t[1]
                tgrid = World.get_height(x, y)
                if tgrid:
                    vertices.append([tgrid.height, (x, y)])
                    self.aoe.append((x, y))
            step = 1
            for i in range(0, amount, step):
                # TODO: Fix it when "vertices" is empty
                min_val = min(vertices, key=lambda x: x[0])[0]
                for point in vertices:
                    if point[0] == min_val:
                        point[0] += 1
                        # Whole tile raise
                        if subtile == 9:
                            tgrid = World.get_height(point[1])
                            tgrid.raise_face()
                            World.set_height(tgrid, point[1])
                        # Edge raise
                        elif subtile in [5, 6, 7, 8]:
                            st1 = subtile - 5
                            st2 = st1 + 1
                            tgrid = World.get_height(point[1])
                            tgrid.raise_edge(st1, st2)
                            World.set_height(tgrid, point[1])
                        # Vertex raise
                        elif subtile in [1, 2, 3, 4]:
                            tgrid = World.get_height(point[1])
                            tgrid.raise_vertex(subtile - 1)
                            World.set_height(tgrid, point[1])
            if soft:
                # Soften around the modified tiles
                self.soften(self.aoe, soften_up=True)
        return r

    def soften(self, tiles, soften_up=False, soften_down=False):
        """Soften the tiles around a given set of tiles, raising them to make a smooth slope
        Can be set to either raise tiles to the same height or lower them"""
        # Init stacks
        to_check = {}
        checked = {}
        # Add all initial tiles to first stack
        for t in tiles:
            to_check[t] = World.get_height(t)

        # Find any neighbours of this tile which have the same vertex height before we raise it
        # Need to compare 4 corners and 4 edges
        # Corners:
        # x+1,y-1 -> 0:2
        # x+1,y+1 -> 1:3
        # x-1,y+1 -> 2:0
        # x-1,y-1 -> 3:1
        # Edges:
        # x,y-1 -> 3:2,0:1
        # x+1,y -> 0:3,1:2
        # x,y+1 -> 1:0,2:3
        # x-1,y -> 2:1,3:0
        c_x = [1, 1, -1, -1, 0, 1, 0, -1]
        c_y = [-1, 1, 1, -1, -1, 0, 1, 0]
        c_a = [(0, None), (1, None), (2, None), (3, None), (3, 0), (0, 1), (1, 2), (2, 3)]
        c_b = [(2, None), (3, None), (0, None), (1, None), (2, 1), (3, 2), (0, 3), (1, 0)]

        while to_check:
            # Checking should be empty from the end of the last loop
            checking = to_check
            # To check should be emptied at this point ready to add values this look
            to_check = {}
            for key, value in checking.items():
                # Find all neighbours which haven't already been added to to_check and which aren't already
                # Needs to be changed so that it checks if this tile has already been checked (will be speedier)
                for x, y, a, b in zip(c_x, c_y, c_a, c_b):
                    x = key[0] + x
                    y = key[1] + y
                    # Check if the potential tile has been checked before, if so use the existing object
                    if (x, y) in checked:
                        #                        potential = checked[(x,y)]
                        potential = None
                    elif (x, y) in checking:
                        #                        potential = checking[(x,y)]
                        potential = None
                    elif (x, y) in to_check:
                        potential = to_check[(x, y)]
                    #                        potential = None
                    # Otherwise create a new tile object for that tile
                    else:
                        potential = World.get_height(x, y)
                    m = 0
                    # If there is a tile to compare to (bounds check) and the comparison tile is lower
                    if potential and soften_up:
                        # Raise vertex to same height as the tile we're comparing against
                        # Do this twice for edges, only once for corners
                        for aa, bb in zip(a, b):
                            while self.compare_vertex_higher(value, potential, aa, bb):
                                potential.raise_vertex(bb)
                                m = 1
                    elif potential and soften_down:
                        # Lower vertex to same height as the tile we're comparing against
                        for aa, bb in zip(a, b):
                            while self.compare_vertex_lower(value, potential, aa, bb):
                                potential.lower_vertex(bb)
                                m = 1
                    elif potential:
                        checked[(x, y)] = potential
                    # Since we've modified this vertex, add it to the list to be checked next time around
                    if m == 1:
                        to_check[(x, y)] = potential
                        self.aoe.append((x, y))

            # Add the last iteration's checked values to the checked stack
            checked.update(checking)

        # Finally modify the world to reflect changes made by this tool
        for k in checked.keys():
            World.set_height(checked[k], k)

    @staticmethod
    def compare_vertex_higher(tgrid1, tgrid2, v1, v2):
        """Return True if specified vertex of tgrid1 is higher than specified vertex of tgrid2"""
        if v1 is None or v2 is None:
            return False

        return tgrid1[v1] + tgrid1.height > tgrid2[v2] + tgrid2.height

    @staticmethod
    def compare_vertex_lower(tgrid1, tgrid2, v1, v2):
        """Return True if specified vertex of tgrid1 is lower than specified vertex of tgrid2"""
        if v1 is None or v2 is None:
            return False

        return tgrid1[v1] + tgrid1.height < tgrid2[v2] + tgrid2.height
