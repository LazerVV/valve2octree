import struct
import gzip
import os


def write_redeclipse_map(filename: str) -> None:
    """Create a minimal Red Eclipse .mpz map with one player start."""

    try:
        # --- map header -----------------------------------------------------
        # struct mapz in little endian
        header = struct.pack(
            "<4sii7i4s",
            b"MAPZ",    # magic
            45,         # map version used by old RE maps
            44,         # sizeof(mapz)
            512,        # worldsize (2^9)
            1,          # numents
            0,          # numpvs
            0,          # blendmap
            1,          # numvslots (one default slot)
            281,        # gamever (VERSION_GAME from game/game.h)
            1,          # revision
            b"fps\0"    # gameid
        )

        # --- empty map variables ------------------------------------------
        variables = struct.pack("<i", 0)

        # --- texture MRU list ---------------------------------------------
        texmru = struct.pack("<H", 1) + struct.pack("<H", 0)

        # --- single entity (ET_PLAYERSTART) -------------------------------
        entbase = struct.pack("<3fB3B", 100.0, 100.0, 100.0, 3, 0, 0, 0)
        entattrs = struct.pack("<i7i", 7, *([0] * 7))
        entlinks = struct.pack("<i", 0)
        entity = entbase + entattrs + entlinks

        # --- default vslot -------------------------------------------------
        vslot = struct.pack("<ii", 0, -1)

        # --- minimal octree: root with 8 cubes ----------------------------
        # first four cubes are solid, the rest empty (like new empty maps)
        octree = b"".join(
            struct.pack("<B6H", 2 if i < 4 else 1, 0, 0, 0, 0, 0, 0)
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
