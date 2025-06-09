I want to reverse-engineer the Cube 2: Sauerbraten map format, to write a converter from Valve 220 style Xonotic .map files that ignores Patches and only transforms brushes into the weird-ass voxel format of Cube 2. 

The file `test.py` is still included as a minimal example to generate a toy map.
`convert_map.py` reads `valve220_room.map` and writes a Red&nbsp;Eclipse
compatible `.mpz` map. Each brush is stored as one Cube&nbsp;2
"cube" whose edges are set to the brush bounds instead of spawning
many tiny voxels. Textures are mapped to the matching faces and the
player start stays where it belongs. The whole map is aligned so the
lowest brushes rest on a small solid base.

`voxel_fill.py` was removed in favour of this simpler box-based approach.

Try to use the files in the red-eclipse-code-src/ directory to understand how to make it work.

If necessary also check out hexdump.txt of empty-ish example map (it dumps the file "empty" as in repo) and severely_outdated_documentation.txt .

See actual_maps_from_game for raw data example (might be useful for .cfg files and texturing) don't try to load massive binary blobs from there.

Do not commit the generated map file `test1.mpz` (or any other `.mpz` files).
These binaries can be produced when running `test.py` but should remain
ignored by git. They may be safely deleted after testing.
