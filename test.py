import struct
import gzip
import os

def write_redeclipse_map(filename):
    try:
        # Map header (mapz struct, 36 bytes)
        header = struct.pack(
            "<4siiiiiiiii4s",
            b"MAPZ",  # head (4 bytes)
            45,      # version (MAPVERSION for Red Eclipse, 4 bytes)
            36,      # headersize (4 bytes)
            512,     # worldsize (2^9, 4 bytes)
            1,       # numents (one player start, 4 bytes)
            0,       # numpvs (4 bytes)
            0,       # blendmap (4 bytes)
            1,       # numvslots (one minimal slot, 4 bytes)
            1200,    # gamever (Red Eclipse 1.2, try 2000 for 2.0, 4 bytes)
            1,       # revision (4 bytes)
            b"cube"  # gameid (4 bytes, try cube for Red Eclipse)
        )

        # World variables (one dummy variable: maptitle)
        variables = struct.pack("<i", 1) + struct.pack("<B16sB16s", 0, b"maptitle", 0, b"Test Map")  # numvars=1, key/val (1+16+1+16=34 bytes)

        # Texture MRU (one default texture)
        texmru = struct.pack("<H", 1) + struct.pack("<H", 0)  # nummru = 1, texture index = 0 (2 + 2=4 bytes)

        # Entity (ET_PLAYERSTART at 100, 100, 100)
        entity = struct.pack(
            "<fffi4i",
            100.0, 100.0, 100.0,  # x, y, z (safer position, 3x4=12 bytes)
            3,                    # entity type (ET_PLAYERSTART, try 3, 4 bytes)
            0, 0, 0, 0            # attrs (4x4=16 bytes)
        )  # total: 12+4+16=32 bytes
        entity_attrs = struct.pack("<i", 4)  # numattr = 4 (4 bytes)
        entity_links = struct.pack("<i", 0)  # no links (4 bytes)

        # VSlot (minimal, with one shader param)
        vslot = struct.pack(
            "<iiHi",
            0,  # changed (no changes, 4 bytes)
            -1, # prev (no previous slot, 4 bytes)
            4,  # params length (4 bytes for one param, 2 bytes)
            0   # shader param (dummy, 4 bytes)
        )  # total: 4+4+2+4=14 bytes

        # Octree (single solid cube, minimal)
        octree = struct.pack(
            "<B6H",
            2,       # OCTSAV_SOLID (1 byte)
            0, 0, 0, 0, 0, 0  # 6 texture indices (all 0, 6x2=12 bytes)
        )  # total: 1+12=13 bytes

        # Combine all data
        data = header + variables + texmru + entity + entity_attrs + entity_links + vslot + octree

        # Validate data size
        expected_size = 36 + 34 + 4 + 32 + 4 + 4 + 14 + 13  # header + vars + texmru + entity + attrs + links + vslot + octree
        if len(data) != expected_size:
            print(f"Error: Data size mismatch (expected {expected_size}, got {len(data)})")
            return

        # Write to gzip file
        with gzip.open(filename, "wb") as f:
            f.write(data)

        # Verify file creation
        if os.path.exists(filename):
            print(f"Generated test map: {filename}")
            with open(filename, "rb") as f:
                magic = f.read(2)
                if magic == b"\x1f\x8b":
                    print("File is valid gzip format")
                    with gzip.open(filename, "rb") as gf:
                        decompressed = gf.read(4)
                        if decompressed == b"MAPZ":
                            print("Decompressed file starts with valid MAPZ header")
                        else:
                            print(f"Warning: Decompressed file has invalid header: {decompressed}")
                else:
                    print(f"Error: File is not valid gzip format (starts with {magic.hex()})")
        else:
            print(f"Error: Failed to create {filename}")

    except Exception as e:
        print(f"Error generating test map: {e}")

# Generate the test map
if __name__ == "__main__":
    output_file = "test1.mpz"
    write_redeclipse_map(output_file)
