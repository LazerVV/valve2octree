"""Generate a tiny Red Eclipse map for experimentation.

The map demonstrates how a hidden container cube ("garbage" cube) can
be subdivided to place brushes anywhere inside the map. Two thin wall
segments meet at a corner and a small sloped cube shows how edge data
can create ramps without voxelising the entire map.
"""

import struct
import gzip
import os

# ---------------------------------------------------------------------------
# Constants used in the map header. These mirror the C++ structs in
# red-eclipse's source and are kept small for clarity.
# ---------------------------------------------------------------------------

MAP_VERSION = 45            # map format version to target
WORLD_SIZE = 512            # root cube size (2^9)
GAME_VERSION = 281          # VERSION_GAME from game/game.h
GAME_ID = b"fps\0"          # 3 byte string + NUL terminator
MAP_REVISION = 1

# Texture slots used by the accompanying configuration. Slot 0 is the sky and
# slot 1 will be the ground texture used for the solid cubes.
TEXTURE_SKY = 0
TEXTURE_GROUND = 1



def _pack_edges(sx, ex, sy, ey, sz, ez):
    """Return the 12 byte edge array for a normal cube."""
    edges = bytearray()
    for s, e in ((sx, ex), (sy, ey), (sz, ez)):
        val = (e << 4) | s
        for _ in range(4):
            edges.append(val)
    return bytes(edges)


def _pack_edge_list(pairs):
    """Pack 12 (start, end) pairs into Cube 2 edge bytes."""
    return bytes(((e << 4) | s) for s, e in pairs)


def _pack_cube(tex, edges=None):
    """Pack a cube. If edges is None a solid or empty cube is written."""
    if edges is None:
        # 2 = solid cube, 1 = empty cube. Here we assume solid if tex != TEXTURE_SKY
        typ = 2 if tex[0] != TEXTURE_SKY else 1
        return struct.pack("<B6H", typ, *tex)

    data = bytearray()
    data.append(3)  # normal cube with edge data
    data.extend(edges)
    data.extend(struct.pack("<6H", *tex))
    return bytes(data)


def _empty_cube():
    """Return an empty cube using the sky texture."""
    return _pack_cube([TEXTURE_SKY] * 6)


def _pack_children(children):
    """Pack a split cube with eight child cube blobs."""
    if len(children) != 8:
        raise ValueError("split cube needs exactly 8 children")
    return b"\x00" + b"".join(children)


def write_redeclipse_map(filename: str) -> None:
    """Create a tiny Red Eclipse .mpz map built from a hidden container cube.

    A large "garbage" cube sits below the playable space. It is subdivided
    once and two of its children become thin wall segments that meet in a
    corner. The remaining children stay empty so the container itself is
    invisible when the map is loaded.
    """

    try:
        # ------------------------------------------------------------------
        # Header (struct mapz) as defined in the engine source
        # ------------------------------------------------------------------
        header = struct.pack(
            "<4sii7i4s",
            b"MAPZ",           # magic
            MAP_VERSION,       # map format version
            44,                # sizeof(mapz)
            WORLD_SIZE,        # worldsize (must be power of two)
            1,                 # numents (only the player start)
            0,                 # numpvs
            0,                 # blendmap
            1,                 # numvslots (one default slot)
            GAME_VERSION,      # gamever
            MAP_REVISION,      # revision
            GAME_ID            # gameid
        )

        # --- empty map variables ------------------------------------------
        variables = struct.pack("<i", 0)

        # --- texture MRU list ---------------------------------------------
        texmru = struct.pack("<H", 1) + struct.pack("<H", 0)

        # --- single entity (ET_PLAYERSTART) -------------------------------
        # place the player roughly in the middle of the scene
        spawn_z = WORLD_SIZE / 2
        entbase = struct.pack(
            "<3fB3B",
            WORLD_SIZE / 2,     # x
            WORLD_SIZE / 2,     # y
            float(spawn_z),    # z
            3,                 # attr1: angle (yaw)
            0, 0, 0            # reserved
        )
        entattrs = struct.pack("<i7i", 7, *([0] * 7))
        entlinks = struct.pack("<i", 0)
        entity = entbase + entattrs + entlinks

        # --- default vslot -------------------------------------------------
        vslot = struct.pack("<ii", 0, -1)

        # --- minimal octree ------------------------------------------------
        # To place larger brushes without spawning huge numbers of voxels we
        # create a hidden "garbage" cube that sits below the visible part of
        # the map. Brushes are extruded from this container by subdividing it
        # further. Only the final cubes that represent the walls remain solid;
        # the intermediate cubes are empty so they won't show up while
        # playing.

        # child 0 of the root acts as the hidden container. All other root
        # children stay empty.

        garbage_children = []

        # indices 1 and 2 meet diagonally so their cubes overlap at one
        # corner, forming an L-shaped intersection. Index 5 contains a
        # simple sloped cube to demonstrate non‑axis aligned geometry.
        # All other children stay empty.
        for i in range(8):
            if i == 2:
                # wall running along the Y axis
                wall_y = _pack_edges(6, 8, 0, 8, 0, 8)
                garbage_children.append(_pack_cube([TEXTURE_GROUND] * 6, wall_y))
            elif i == 1:
                # wall running along the X axis
                wall_x = _pack_edges(0, 8, 6, 8, 0, 8)
                garbage_children.append(_pack_cube([TEXTURE_GROUND] * 6, wall_x))
            elif i == 5:
                # wedge rising from 0% to 25% height along the X axis
                slope = _pack_edge_list([
                    (0, 8), (0, 8), (0, 8), (0, 8),  # x edges
                    (0, 8), (0, 8), (0, 8), (0, 8),  # y edges
                    (0, 0), (0, 2), (0, 0), (0, 2)   # z edges
                ])
                garbage_children.append(_pack_cube([TEXTURE_GROUND] * 6, slope))
            else:
                garbage_children.append(_empty_cube())

        garbage_cube = _pack_children(garbage_children)

        children = [garbage_cube] + [_empty_cube() for _ in range(7)]

        octree = b"".join(children)

        data = header + variables + texmru + entity + vslot + octree

        with gzip.open(filename, "wb") as f:
            f.write(data)

        if os.path.exists(filename):
            print(f"Generated test map: {filename}")
        else:
            print(f"Failed to create {filename}")

    except Exception as exc:
        print(f"Error generating test map: {exc}")


def write_redeclipse_cfg(filename: str) -> None:
    """Write a simple map config referencing default.png."""
    try:
        with open(filename, "w", encoding="utf-8") as cfg:
            cfg.write("setshader stdworld\n")
            cfg.write("texture 0 textures/sky.png\n")
            cfg.write("setshader stdworld\n")
            cfg.write("texture 0 textures/edit/edit_1.png\n")
        print(f"Generated map config: {filename}")
    except Exception as exc:
        print(f"Error writing config: {exc}")

# Generate the test map
if __name__ == "__main__":
    output_file = "test1.mpz"
    cfg_file = "test1.cfg"
    write_redeclipse_map(output_file)
    write_redeclipse_cfg(cfg_file)
