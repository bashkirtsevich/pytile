p = 64
p2 = int(p / 2)
p4 = int(p / 4)
p4x3 = int(p4 * 3)
p8 = int(p / 8)
p16 = int(p / 16)

# tile height difference
ph = 8


class TGrid(object):
    """Represents a tile's vertex height and can be used to modify that height"""

    def __init__(self, height, vertices):
        self.array = vertices
        self.height = height
        self.length = len(self.array)

    def __len__(self):
        return len(self.array)

    def __call__(self, vertices):
        self.array = vertices

    def __getitem__(self, index):
        return self.array[index % self.length]

    def __setitem__(self, index, value):
        self.array[index % self.length] = value

    def __contains__(self, item):
        return item in self.array

    def __str__(self):
        return str(self.array)

    # Return the basic array of the tile (vertex info)
    def get_array(self):
        return self.array

    # Return the height of the tile
    def height(self):
        return self.height

    # Set the height of the tile
    def set_height(self, h):
        self.height = h

    # Terrain modification functions
    def raise_face(self):
        """Raise an entire face of a tile (all 4 vertices)"""
        # Sort the correct tile type
        if 2 in self:
            self.height += 1
            for k in range(len(self)):
                self[k] -= 1
                if self[k] < 0:
                    self[k] = 0
        elif 1 in self:
            self.height += 1
            self.array = [0, 0, 0, 0]
        else:
            self.height += 1

    def raise_edge(self, v1, v2):
        """Raise a tile edge, takes two vertices as arguments which define the edge"""
        v1 = v1 % 4
        v2 = v2 % 4
        if self.array[v1] < self.array[v2]:
            self.raise_vertex(v1)
        elif self.array[v1] > self.array[v2]:
            self.raise_vertex(v2)
        else:
            self.raise_vertex(v1)
            self.raise_vertex(v2)
        return True

    def raise_vertex(self, v):
        """Raise vertex, and if all vertices > 1 raise tile"""
        v = v % 4
        # First raise target vertex
        self.array[v] += 1
        # Then do a consistency check
        self.correct_vertices(v)
        # No restriction on tile height, so return True
        return True

    def lower_face(self):
        """Lower an entire face of a tile (all 4 vertices)"""
        # Sort the correct tile type
        if 2 in self:
            for k in range(len(self)):
                if self[k] == 2:
                    self[k] = 1
        elif 1 in self:
            self.array = [0, 0, 0, 0]
        else:
            self.height -= 1
        # Tile must not be reduced to below 0
        if self.height < 0:
            self.height = 0
            return 0
        else:
            # Return the actual lowering done, this will always be 1 unless we've reset the height for being negative
            return -1

    def lower_edge(self, v1, v2):
        """Lower a tile edge, takes two vertices as arguments which define the edge"""
        v1 = v1 % 4
        v2 = v2 % 4

        if self.array[v1] > self.array[v2]:
            return self.lower_vertex(v1)
        elif self.array[v1] < self.array[v2]:
            return self.lower_vertex(v2)
        else:
            return self.lower_vertex(v2)

    def lower_vertex(self, v):
        """Lower vertex, or if vertex is 0 lower entire tile then lower vertex"""
        v = v % 4
        if self.array[v] != 0:
            self.array[v] -= 1
        elif self.height != 0:
            self.height -= 1
            for k in range(len(self.array)):
                self.array[k] += 1
            self.array[v] -= 1
        else:
            # Cannot lower this vertex, return 0 to indicate this
            return 0
        self.correct_vertices(v)
        # Vertex has been lowered, return the amount we've modified by
        return -1

    def correct_vertices(self, v):
        """Ensure that vertices follow the rules, no more than 1 unit difference between neighbours
        Takes argument v, which is the vertex to keep fixed"""
        # Use % to ensure this stays within bounds of the array
        a = self.array[v]
        b1 = self.array[(v - 1) % 4]
        b2 = self.array[(v + 1) % 4]
        c = self.array[(v + 2) % 4]
        # First ensure that target vertex is no greater than 2 and no less than 0 (should not occur)
        while a > 2:
            a -= 1
            self.height += 1
        while a < 0:
            a += 1
            self.height -= 1
        # Next check to ensure that there is no greater than 1 level gap between vertices
        a_b1 = b1 - a
        a_b2 = b2 - a
        # Neighbour b1 less than 1 level below, set to one level below, or equal if a is 0
        if a_b1 < -1:
            b1 = a - 1
        elif a_b1 > 1:
            b1 = a + 1
        if a_b2 < -1:
            b2 = a - 1
        elif a_b2 > 1:
            b2 = a + 1
        # And check both b1 and b2 against c
        b1_c = c - b1
        if b1_c < -1:
            c = b1 - 1
        elif b1_c > 1:
            c = b1 + 1
        b2_c = c - b2
        if b2_c < -1:
            c = b2 - 1
        elif b2_c > 1:
            c = b2 + 1
        # Write them back to the array
        self.array[v] = a
        self.array[(v - 1) % 4] = b1
        self.array[(v + 1) % 4] = b2
        self.array[(v + 2) % 4] = c
        # Ensure no negative numbers in array
        for k in range(len(self.array)):
            if self.array[k] < 0:
                self.array[k] = 0
        # Check if there's a 0 in the array (if not, then all must be at least 1 and we can raise the tile)
        if 0 not in self.array:
            for k in range(len(self.array)):
                self.array[k] -= 1
            self.height += 1


class World(object):
    """Holds all world-related variables and methods"""

    # Constants
    SEA_LEVEL = 0
    # Display variables (need moving to world class?)
    dxoff = None  # Horizontal offset position of displayed area
    dyoff = None  # Vertical offset (from top)
    blah = None

    # Hitboxes for subtile selection
    # 0 = Nothing
    # 1 = Left vertex
    # 2 = Bottom vertex
    # 3 = Right vertex
    # 4 = Top vertex
    # 5 = Bottom-left edge
    # 6 = Bottom-right edge
    # 7 = Top-right edge
    # 8 = Top-left edge
    # 9 = Face

    type_lookup = [[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [1, 1, 0, 0], [0, 1, 1, 0],
                   [0, 0, 1, 1], [1, 0, 0, 1], [1, 1, 1, 1]]

    type = dict()

    # Flat tile
    type["0000"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 8, 8, 9, 9, 7, 7, 0],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Left vertex
    type["1000"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 8, 4, 4, 0, 0, 0],
                    [1, 1, 8, 4, 4, 7, 0, 0],
                    [1, 1, 8, 9, 9, 7, 7, 0],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 9, 3, 3],
                    [0, 0, 5, 9, 9, 6, 6, 0],
                    [0, 0, 0, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Bottom vertex
    type["0100"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 8, 8, 9, 9, 7, 7, 0],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 5, 2, 2, 6, 3, 3],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Right vertex
    type["0010"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 7, 0, 0],
                    [0, 0, 8, 4, 4, 7, 3, 3],
                    [0, 8, 8, 9, 9, 7, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 6, 6, 0],
                    [0, 5, 5, 9, 9, 6, 0, 0],
                    [0, 0, 5, 2, 2, 0, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Top vertex
    type["0001"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 1, 8, 9, 9, 7, 3, 0],
                    [1, 1, 8, 9, 9, 7, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Bottom-Left edge
    type["1100"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 8, 4, 4, 0, 0, 0],
                    [1, 1, 8, 4, 4, 7, 0, 0],
                    [1, 1, 8, 9, 9, 7, 7, 0],
                    [1, 1, 5, 9, 9, 9, 3, 3],
                    [0, 5, 5, 2, 2, 6, 3, 3],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Bottom-Right edge
    type["0110"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 7, 0, 0],
                    [0, 0, 8, 4, 4, 7, 3, 3],
                    [0, 8, 8, 9, 9, 7, 3, 3],
                    [1, 1, 9, 9, 9, 6, 3, 3],
                    [1, 1, 5, 2, 2, 6, 6, 0],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Top-Right edge
    type["0011"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 0, 8, 9, 9, 7, 3, 3],
                    [0, 8, 8, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 6, 6, 0],
                    [0, 5, 5, 9, 9, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Top-Left edge
    type["1001"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [1, 1, 8, 9, 9, 7, 0, 0],
                    [1, 1, 9, 9, 9, 7, 7, 0],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Right vertex down
    type["1101"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 8, 8, 9, 9, 7, 7, 0],
                    [1, 1, 9, 9, 9, 7, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 5, 9, 9, 6, 3, 3],
                    [0, 5, 5, 2, 2, 6, 3, 3],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0], ]
    # Top vertex down
    type["1110"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 8, 8, 4, 4, 7, 7, 0],
                    [1, 8, 8, 4, 4, 7, 7, 3],
                    [1, 1, 8, 4, 4, 7, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 5, 9, 9, 6, 3, 3],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0], ]
    # Left vertex down
    type["0111"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 8, 8, 9, 9, 7, 7, 0],
                    [1, 1, 8, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 5, 9, 9, 6, 3, 3],
                    [1, 1, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0], ]
    # Bottom vertex down
    type["1011"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 8, 8, 9, 9, 7, 7, 0],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 6, 6, 0],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Left vertex two-up
    type["2101"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 8, 4, 4, 0, 0, 0],
                    [1, 1, 8, 4, 4, 7, 7, 0],
                    [1, 1, 8, 4, 4, 7, 7, 3],
                    [1, 1, 8, 4, 4, 7, 3, 3],
                    [1, 1, 5, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 6, 3, 3],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0], ]
    # Bottom vertex two-up
    type["1210"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 8, 8, 4, 4, 7, 7, 0],
                    [1, 8, 8, 4, 4, 7, 7, 3],
                    [1, 1, 8, 4, 4, 7, 3, 3],
                    [1, 1, 5, 9, 9, 6, 3, 3],
                    [1, 1, 5, 2, 2, 6, 3, 3],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0], ]
    # Right vertex two-up
    type["0121"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 7, 0, 0],
                    [0, 8, 8, 4, 4, 7, 3, 3],
                    [1, 8, 8, 4, 4, 7, 3, 3],
                    [1, 1, 8, 4, 4, 7, 3, 3],
                    [1, 1, 9, 9, 9, 6, 3, 3],
                    [1, 1, 5, 9, 9, 6, 6, 0],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0], ]
    # Top vertex two-up
    type["1012"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 8, 8, 9, 9, 7, 7, 0],
                    [1, 1, 8, 9, 9, 7, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 6, 6, 0],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Left & Right vertices up
    type["1010"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [1, 1, 8, 4, 4, 7, 3, 3],
                    [1, 1, 8, 9, 9, 7, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [0, 5, 5, 9, 9, 6, 6, 0],
                    [0, 0, 5, 9, 9, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]
    # Bottom & Top vertices up
    type["0101"] = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 4, 4, 0, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 0, 8, 4, 4, 7, 0, 0],
                    [0, 1, 8, 9, 9, 7, 3, 0],
                    [1, 1, 8, 9, 9, 7, 3, 3],
                    [1, 1, 9, 9, 9, 9, 3, 3],
                    [1, 1, 5, 2, 2, 6, 3, 3],
                    [0, 5, 5, 2, 2, 6, 6, 0],
                    [0, 0, 5, 2, 2, 6, 0, 0],
                    [0, 0, 0, 2, 2, 0, 0, 0], ]

    array = None

    def __init__(self):
        if World.dxoff is None:
            World.dxoff = 0
        if World.dyoff is None:
            World.dyoff = 0
        if World.blah is None:
            World.blah = "meh"
        if World.array is None:
            World.array = self.make_array()

        World.WorldX = len(self.array)
        World.WorldY = len(self.array[0])

        # Width and Height of the world, in pixels
        World.WorldWidth = (World.WorldX + World.WorldY) * p2
        World.WorldWidth2 = int(World.WorldWidth / 2)
        World.WorldHeight = ((World.WorldX + World.WorldY) * p4) + p2
        # Width and Height of the world, in pixels
        World.WorldWidth = (World.WorldX + World.WorldY) * p2
        World.WorldWidth2 = int(World.WorldWidth / 2)
        World.WorldHeight = ((World.WorldX + World.WorldY) * p4) + p2

    # Tile structure [height, vertexheight[left, bottom, right, top], [path_start, path_end], highlightinfo]

    @staticmethod
    def make_array():
        """Generate a World array"""

        tile_map = [[[2, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [10, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [10, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [10, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0], [[0, 14], [2, 12]]], [0, [0, 0, 0, 0], [[0, 14], [2, 12]]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [2, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0], [[0, 14], [2, 12], [0, 12], [2, 14]]], [0, [0, 0, 0, 0], [[0, 14], [2, 12]]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [6, [0, 0, 0, 0]],
                     [6, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [2, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0], [[0, 14], [2, 12]]], [0, [0, 0, 0, 0], [[0, 14], [2, 12]]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 0, 0]], [0, [1, 1, 0, 0]], [0, [1, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [12, [0, 0, 0, 0]],
                     [6, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [1, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0], [[0, 14], [2, 12]]], [0, [0, 0, 0, 0], [[0, 17], [2, 15]]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 1, 0, 0]], [0, [1, 2, 1, 0]], [1, [1, 1, 0, 0]], [0, [2, 1, 0, 1]],
                     [0, [1, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [6, [0, 0, 0, 0]], [6, [0, 0, 0, 0]],
                     [6, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [1, [0, 0, 0, 0]], [1, [0, 0, 0, 0]], [1, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0], [[0, 14], [2, 12], [3, 14], [5, 12]]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 1, 1, 0]], [1, [0, 1, 1, 0]], [2, [0, 0, 0, 0]], [1, [1, 0, 0, 1]],
                     [0, [1, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [5, [0, 0, 1, 1]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0], [[0, 14], [2, 12]]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 1, 0]], [0, [0, 1, 2, 1]], [1, [0, 0, 1, 1]], [0, [1, 0, 1, 2]], [0, [0, 0, 0, 1]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [4, [0, 0, 1, 1]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0], [[0, 17], [2, 15]]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 1, 0]], [0, [0, 0, 1, 1]], [0, [0, 0, 0, 1]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [3, [0, 0, 1, 1]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0], [[6, 20], [8, 18]]], [0, [0, 0, 0, 0], [[6, 20], [8, 18]]],
                     [0, [0, 0, 0, 0], [[6, 20], [8, 18]]], [0, [0, 0, 0, 0], [[3, 20], [5, 18]]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[1, 13]]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [2, [0, 0, 1, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[1, 13]]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [1, [0, 0, 1, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 0, 0]], [0, [1, 1, 0, 0]], [0, [1, 1, 0, 0]],
                     [0, [1, 1, 0, 0]], [0, [1, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[1, 13]]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[7, 16]]], [0, [0, 0, 0, 0], [[7, 19]]],
                     [0, [0, 0, 0, 0], [[7, 19]]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 1, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 1, 0]], [1, [0, 0, 0, 0]], [1, [0, 0, 0, 0]],
                     [1, [0, 0, 0, 0]], [0, [1, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[1, 13]]],
                     [0, [0, 0, 0, 0], [[4, 16]]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 1, 0, 0]], [0, [1, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 1, 0]], [1, [0, 0, 0, 0]], [1, [0, 0, 0, 0]],
                     [1, [0, 0, 0, 0]], [0, [1, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[1, 13], [4, 13]]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 1, 0]], [0, [0, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 1, 0]], [1, [0, 0, 0, 0]], [1, [0, 0, 0, 0]],
                     [1, [0, 0, 0, 0]], [0, [1, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[1, 13]]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 1, 0]], [0, [0, 0, 1, 1]], [0, [0, 0, 1, 1]],
                     [0, [0, 0, 1, 1]], [0, [0, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0], [[1, 13]]],
                     [0, [0, 0, 0, 0]], [0, [1, 1, 1, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 1, 1]], [0, [0, 0, 0, 0]],
                     [0, [1, 0, 1, 1]], [0, [0, 0, 0, 0]], [0, [1, 1, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [1, 1, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 1, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 1, 1]],
                     [0, [0, 0, 0, 0]], [0, [1, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [1, 0, 1, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 1, 0, 1]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [1, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 1, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 1, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 1]], [0, [0, 0, 0, 0]], [0, [1, 2, 1, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 1, 2, 1]], [0, [0, 0, 0, 0]], [0, [1, 0, 1, 2]], [0, [0, 0, 0, 0]], [0, [2, 1, 0, 1]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ],
                    [[0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]],
                     [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], [0, [0, 0, 0, 0]], ], ]

        return tile_map

    @staticmethod
    def add_path(x, y, path):
        """Add a path to the World"""
        # This needs bounds checking/sanitisation etc. added
        try:
            World.array[x][y][2]
        except IndexError:
            World.array[x][y].append([path])
            # debug("(NEW) Adding path: %s to location: (%s,%s)" % (path, x, y))
        else:
            World.array[x][y][2].append(path)
            # debug("(EXISTING) Adding path: %s to location: (%s,%s)" % (path, x, y))
        return True

    @staticmethod
    def get_paths(x, y):
        """Return paths at specified tile coordinate"""
        try:
            World.array[x][y][2]
        except IndexError:
            return []
        else:
            return World.array[x][y][2]

    @staticmethod
    def get_4_neighbour_paths(x, y, override=None):
        """Return paths of 4 tiles edge-neighbouring this one
        If tile off world, or tile has no paths, return empty array for that tile"""
        paths = []
        for xx, yy in zip([x - 1, x, x + 1, x], [y, y + 1, y, y - 1]):
            if override and (xx, yy) in override:
                try:
                    override[(xx, yy)][2]
                except IndexError:
                    paths.append([])
                else:
                    paths.append(override[(xx, yy)][2])
            else:
                try:
                    World.array[xx][yy]
                except IndexError:
                    paths.append([])
                else:
                    try:
                        World.array[xx][yy][2]
                    except IndexError:
                        paths.append([])
                    else:
                        paths.append(World.array[xx][yy][2])
        return paths

    @staticmethod
    def get_4_overlap_paths(neighbour_paths):
        """Return paths of tiles to NESW which overlap the tile in question
        Takes a list of 4 sets of paths for the 4 points of the compass"""
        # 1. Look up neighbours to see if this tile needs to have any of their
        #    paths drawn on it too
        n, e, s, w = neighbour_paths
        # nps arranged as N, E, S, W
        ne = [3, 4, 5]
        se = [11, 10, 9]
        sw = [15, 16, 17]
        nw = [21, 22, 23]
        outs = []
        # Check all directions for neighbouring paths which need to be drawn
        for paths, tests in zip([n, e, s, w], [sw + se, nw + sw, ne + nw, se + ne]):
            paths_out = []
            for path in paths:
                for test in tests:
                    if test in path:
                        paths_out = paths
            outs.append(paths_out)
        return outs

    # Terrain can be modified in several ways
    # Easiest is a one-tile approach, this affects only one vertex/edge/face of a tile and has no effect on
    # neighbouring tiles
    # Next is one-tile approach which does affect neighbours, this is a "smooth" modification
    # Finally multi-tile smooth/sharp deformations

    # Functions in World are hooked into by functions in the GUI of the main program

    @staticmethod
    def set_offset(x, y=None):
        """Sets the offset of the display"""
        if y is None:
            x, y = x
        World.dxoff = x
        World.dyoff = y

    @staticmethod
    def get_offset():
        """Return the offset of the display"""
        return World.dxoff, World.dyoff

    @staticmethod
    def set_height(tgrid, x, y=None):
        """Sets the height of a tile"""
        if y is None:
            x, y = x
        World.array[x][y][0] = tgrid.height
        World.array[x][y][1] = tgrid.array

    @staticmethod
    def get_height(x, y=None):
        """Get height of a tile, return as TGrid object"""
        if y is None:
            x, y = x
        # Bounds checks
        if x > len(World.array) - 1 or y > len(World.array[0]) - 1 or x < 0 or y < 0:
            return None
        else:
            return TGrid(World.array[x][y][0], World.array[x][y][1])

    @staticmethod
    def get_neighbours(x, y=None):
        """Return an array of tiles neighbouring the tile specified"""
        if y is None:
            x, y = x
        out = []
        for a in range(x - 1, x + 1):
            for b in range(y - 1, y + 1):
                out.append(TGrid(World.array[a][b][0], World.array[a][b][1]))
        return out
