"""Generate a tiny Red Eclipse map for experimentation."""

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



def write_redeclipse_map(filename: str) -> None:
    """Create a minimal Red Eclipse .mpz map with a single player start."""

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
        # place the player roughly in the middle above the ground cubes
        spawn_z = WORLD_SIZE / 2 + 50
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
        # Create the root cube with eight children. The lower four octants are
        # solid ground blocks using the ground texture. The upper four are
        # empty "air" using the sky texture.
        octree = b"".join(
            struct.pack(
                "<B6H",
                2 if i < 4 else 1,                     # cube type
                *(
                    [TEXTURE_GROUND] * 6
                    if i < 4 else
                    [TEXTURE_SKY] * 6
                )
            )
            for i in range(8)
        )

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
            cfg.write("texture 1 textures/edit/edit_1.png\n")
        print(f"Generated map config: {filename}")
    except Exception as exc:
        print(f"Error writing config: {exc}")

# Generate the test map
if __name__ == "__main__":
    output_file = "test1.mpz"
    cfg_file = "test1.cfg"
    write_redeclipse_map(output_file)
    write_redeclipse_cfg(cfg_file)
