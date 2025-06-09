import struct
import gzip
import re
from typing import List, Dict

MAP_VERSION = 45
WORLD_SIZE = 512
GAME_VERSION = 281
GAME_ID = b"fps\0"
MAP_REVISION = 1

# orientation indices
ORIENT_INDEX = {
    'x-': 0,  # O_LEFT
    'x+': 1,  # O_RIGHT
    'y-': 2,  # O_BACK
    'y+': 3,  # O_FRONT
    'z-': 4,  # O_BOTTOM
    'z+': 5,  # O_TOP
}

VOXEL_SIZE = 16  # 32x32x32 grid
GRID_SIZE = WORLD_SIZE // VOXEL_SIZE

# basic floor texture for the helper cubes used to avoid culling
BASE_TEXTURE = "exx/base-crete01"

pattern = re.compile(r"\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)\s*([^\s]+)")

class Brush:
    def __init__(self):
        self.planes = []  # list of (points, texture)
        self.bounds = [None, None, None, None, None, None]  # xmin,xmax,ymin,ymax,zmin,zmax
        self.textures: Dict[str,str] = {}

    def add_plane(self, pts, texture):
        self.planes.append((pts, texture))
        xs, ys, zs = zip(*pts)
        if self.bounds[0] is None:
            self.bounds = [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]
        else:
            self.bounds[0] = min(self.bounds[0], min(xs))
            self.bounds[1] = max(self.bounds[1], max(xs))
            self.bounds[2] = min(self.bounds[2], min(ys))
            self.bounds[3] = max(self.bounds[3], max(ys))
            self.bounds[4] = min(self.bounds[4], min(zs))
            self.bounds[5] = max(self.bounds[5], max(zs))

    def finalize(self):
        xmin,xmax,ymin,ymax,zmin,zmax = self.bounds
        for pts, tex in self.planes:
            xs,ys,zs = zip(*pts)
            if all(x==xs[0] for x in xs):
                if xs[0]==xmin:
                    self.textures['x-']=tex
                elif xs[0]==xmax:
                    self.textures['x+']=tex
            elif all(y==ys[0] for y in ys):
                if ys[0]==ymin:
                    self.textures['y-']=tex
                elif ys[0]==ymax:
                    self.textures['y+']=tex
            elif all(z==zs[0] for z in zs):
                if zs[0]==zmin:
                    self.textures['z-']=tex
                elif zs[0]==zmax:
                    self.textures['z+']=tex


def parse_valve_map(fname: str) -> List[Brush]:
    brushes: List[Brush] = []
    cur: Brush | None = None
    in_world = False
    with open(fname) as f:
        for line in f:
            s = line.strip()
            if s.startswith('"classname" "worldspawn"'):
                in_world = True
                continue
            if not in_world:
                continue
            if s.startswith('// entity 1'):
                break
            if s == '{':
                cur = Brush()
                continue
            if s == '}' and cur is not None:
                cur.finalize()
                brushes.append(cur)
                cur = None
                continue
            if cur is not None and s.startswith('('):
                m = pattern.match(s)
                if m:
                    pts = [(int(m.group(i)), int(m.group(i+1)), int(m.group(i+2))) for i in (1,4,7)]
                    texture = m.group(10)
                    cur.add_plane(pts, texture)
    return brushes


def collect_bounds(brushes: List[Brush]):
    xs=[];ys=[];zs=[]
    for b in brushes:
        xmin,xmax,ymin,ymax,zmin,zmax = b.bounds
        xs.extend([xmin,xmax])
        ys.extend([ymin,ymax])
        zs.extend([zmin,zmax])
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)


def build_grid(brushes: List[Brush], offset):
    grid = [[[{"solid":False, "tex":[0]*6} for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for b in brushes:
        xmin,xmax,ymin,ymax,zmin,zmax = b.bounds
        gx0 = int((xmin+offset[0])/VOXEL_SIZE)
        gx1 = int((xmax+offset[0]-1)/VOXEL_SIZE)
        gy0 = int((ymin+offset[1])/VOXEL_SIZE)
        gy1 = int((ymax+offset[1]-1)/VOXEL_SIZE)
        gz0 = int((zmin+offset[2])/VOXEL_SIZE)
        gz1 = int((zmax+offset[2]-1)/VOXEL_SIZE)

        # only draw a single voxel layer for each oriented face. this prevents
        # brushes from filling the entire room volume which made the map appear
        # solid previously.
        for orient, tex in b.textures.items():
            idx = ORIENT_INDEX[orient]
            if orient == 'x-':
                x = gx0
                for y in range(gy0, gy1 + 1):
                    for z in range(gz0, gz1 + 1):
                        cell = grid[z][y][x]
                        cell['solid'] = True
                        cell['tex'][idx] = tex
            elif orient == 'x+':
                x = gx1
                for y in range(gy0, gy1 + 1):
                    for z in range(gz0, gz1 + 1):
                        cell = grid[z][y][x]
                        cell['solid'] = True
                        cell['tex'][idx] = tex
            elif orient == 'y-':
                y = gy0
                for x in range(gx0, gx1 + 1):
                    for z in range(gz0, gz1 + 1):
                        cell = grid[z][y][x]
                        cell['solid'] = True
                        cell['tex'][idx] = tex
            elif orient == 'y+':
                y = gy1
                for x in range(gx0, gx1 + 1):
                    for z in range(gz0, gz1 + 1):
                        cell = grid[z][y][x]
                        cell['solid'] = True
                        cell['tex'][idx] = tex
            elif orient == 'z-':
                z = gz0
                for x in range(gx0, gx1 + 1):
                    for y in range(gy0, gy1 + 1):
                        cell = grid[z][y][x]
                        cell['solid'] = True
                        cell['tex'][idx] = tex
            elif orient == 'z+':
                z = gz1
                for x in range(gx0, gx1 + 1):
                    for y in range(gy0, gy1 + 1):
                        cell = grid[z][y][x]
                        cell['solid'] = True
                        cell['tex'][idx] = tex
    # add a solid base underneath the level so that the engine does not cull
    # the interior of our generated voxels
    base_thickness = 2  # two voxels ~= 32 units
    for z in range(base_thickness):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                cell = grid[z][y][x]
                cell['solid'] = True
                cell['tex'] = [BASE_TEXTURE]*6
    return grid


def gather_textures(grid):
    names={'sky':0}
    next_index=1
    for z in grid:
        for y in z:
            for cell in y:
                for tex in cell['tex']:
                    if isinstance(tex,str) and tex not in names:
                        names[tex]=next_index
                        next_index+=1
    return names


def encode_octree(grid, textures):
    def encode(depth,x0,y0,z0):
        if depth==0:
            cell=grid[z0][y0][x0]
            typ=2 if cell['solid'] else 1
            tex=[textures.get(t,0) for t in cell['tex']]
            return struct.pack('<B6H', typ, *tex)
        else:
            half=1<<(depth-1)
            data=b'\x00'
            for i in range(8):
                dx=i&1; dy=(i>>1)&1; dz=(i>>2)&1
                data+=encode(depth-1,x0+dx*half,y0+dy*half,z0+dz*half)
            return data
    depth=5
    return encode(depth,0,0,0)


def write_mpz(filename, grid, textures, spawn_pos):
    texslots=len(textures)
    header=struct.pack('<4sii7i4s', b'MAPZ', MAP_VERSION, 44, WORLD_SIZE,
                        1,0,0,texslots, GAME_VERSION, MAP_REVISION, GAME_ID)
    variables=struct.pack('<i',0)
    texmru=struct.pack('<H',texslots)+b''.join(struct.pack('<H',i) for i in range(texslots))
    ent=struct.pack('<3fB3B', *spawn_pos, 3,0,0,0)+struct.pack('<i7i',7,*([0]*7))+struct.pack('<i',0)
    vslots=b''.join(struct.pack('<ii',0,-1) for _ in range(texslots))
    octree=encode_octree(grid,textures)
    data=header+variables+texmru+ent+vslots+octree
    with gzip.open(filename,'wb') as f:
        f.write(data)


def write_cfg(filename, textures):
    with open(filename,'w') as f:
        f.write('setshader stdworld\n')
        f.write('texture 0 textures/sky.png\n')
        for name,idx in textures.items():
            if name=='sky':
                continue
            f.write('setshader stdworld\n')
            f.write(f'texture 0 textures/{name}.png\n')

def main():
    brushes=parse_valve_map('valve220_room.map')
    xmin,xmax,ymin,ymax,zmin,zmax=collect_bounds(brushes)
    # Align the level so that voxel boundaries match the original brush layout
    def snap(v):
        return round(v / VOXEL_SIZE) * VOXEL_SIZE
    offset=(snap(WORLD_SIZE/2 - (xmin+xmax)/2),
            snap(WORLD_SIZE/2 - (ymin+ymax)/2),
            snap(WORLD_SIZE/2 - (zmin+zmax)/2))
    grid=build_grid(brushes,offset)
    textures=gather_textures(grid)
    spawn=(144+offset[0], -144+offset[1], 16+offset[2])
    write_mpz('valve220_room.mpz',grid,textures,spawn)
    write_cfg('valve220_room.cfg',textures)

if __name__=='__main__':
    main()
