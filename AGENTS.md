I want to reverse-engineer the Cube 2: Sauerbraten map format, to write a converter from Valve 220 style Xonotic .map files that ignores Patches and only transforms brushes into the weird-ass voxel format of Cube 2. 

The file test.py is your main concern now. 

It tries to create a simple map with a single cube or something to demonstrate that the map format is understood and can be loaded by red eclipse.

Try to use the files in the red-eclipse-code-src/ directory to understand how to make it work.

If necessary also check out hexdump.txt of empty-ish example map (it dumps the file "empty" as in repo) and severely_outdated_documentation.txt .

The correct map version is 45, don't use something else.

Do not commit the generated map file `test1.mpz` (or any other `.mpz` files).
These binaries can be produced when running `test.py` but should remain
ignored by git. They may be safely deleted after testing.
