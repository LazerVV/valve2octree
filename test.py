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
            45,         # MAPVERSION from engine/world.h
            44,         # sizeof(mapz)
            512,        # worldsize (2^9)
            1,          # numents
            0,          # numpvs
            0,          # blendmap
            0,          # numvslots (none)
            281,        # gamever (VERSION_GAME from game/game.h)
            1,          # revision
            b"fps\0"    # gameid
        )

        # --- empty map variables ------------------------------------------
        variables = struct.pack("<i", 0)

        # --- texture MRU list ---------------------------------------------
        texmru = struct.pack("<H", 0)

        # --- single entity (ET_PLAYERSTART) -------------------------------
        entbase = struct.pack("<3fB3B", 100.0, 100.0, 100.0, 3, 0, 0, 0)
        entattrs = struct.pack("<i7i", 7, *([0] * 7))
        entlinks = struct.pack("<i", 0)
        entity = entbase + entattrs + entlinks

        # --- minimal octree: root with 8 cubes ----------------------------
        # first four cubes are solid, the rest empty (like new empty maps)
        octree = b"".join(
            struct.pack("<B6H", 2 if i < 4 else 1, 0, 0, 0, 0, 0, 0)
            for i in range(8)
        )

        data = header + variables + texmru + entity + octree

        with gzip.open(filename, "wb") as f:
            f.write(data)

        if os.path.exists(filename):
            print(f"Generated test map: {filename}")
        else:
            print(f"Failed to create {filename}")

    except Exception as exc:
        print(f"Error generating test map: {exc}")

# Generate the test map
if __name__ == "__main__":
    output_file = "test1.mpz"
    write_redeclipse_map(output_file)
