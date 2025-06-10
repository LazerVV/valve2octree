import struct
import gzip
import re
from typing import List, Dict, Tuple

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

MAX_DEPTH = 5  # octree depth

BASE_TEXTURE = "exx/base-crete01"

pattern = re.compile(r"\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)\s*([^\s]+)")

class Brush:
    def __init__(self):
        self.planes: List[Tuple[Tuple[int,int,int], ...]] = []
        self.bounds = [None, None, None, None, None, None]
        self.textures: Dict[str, str] = {}

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

        v1 = (pts[1][0]-pts[0][0], pts[1][1]-pts[0][1], pts[1][2]-pts[0][2])
        v2 = (pts[2][0]-pts[0][0], pts[2][1]-pts[0][1], pts[2][2]-pts[0][2])
        nx = v1[1]*v2[2] - v1[2]*v2[1]
        ny = v1[2]*v2[0] - v1[0]*v2[2]
        nz = v1[0]*v2[1] - v1[1]*v2[0]
        ax, ay, az = abs(nx), abs(ny), abs(nz)
        if ax >= ay and ax >= az:
            orient = 'x+' if nx > 0 else 'x-'
        elif ay >= ax and ay >= az:
            orient = 'y+' if ny > 0 else 'y-'
        else:
            orient = 'z+' if nz > 0 else 'z-'

        self.textures[orient] = texture

    def finalize(self):
        pass

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

def parse_player_start(fname: str):
    origin = (0.0,0.0,0.0)
    angle = 0.0
    with open(fname) as f:
        capture=False
        for line in f:
            s=line.strip()
            if s.startswith('// entity 1'):
                capture=True
                continue
            if capture:
                if s.startswith('//'):
                    break
                if s.startswith('"origin"'):
                    parts = s.split('"')[3].split()
                    origin = tuple(float(p) for p in parts)
                elif s.startswith('"angle"'):
                    angle=float(s.split('"')[3])
        return origin,angle

def collect_bounds(brushes: List[Brush]):
    xs=[];ys=[];zs=[]
    for b in brushes:
        xmin,xmax,ymin,ymax,zmin,zmax = b.bounds
        xs.extend([xmin,xmax])
        ys.extend([ymin,ymax])
        zs.extend([zmin,zmax])
    return min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)

class Leaf:
    def __init__(self, depth:int, ix:int, iy:int, iz:int, start, end, textures:Dict[str,str]):
        self.depth=depth
        self.ix=ix; self.iy=iy; self.iz=iz
        self.start=start
        self.end=end
        self.textures=textures

def choose_depth(x0,x1,y0,y1,z0,z1):
    for depth in range(0, MAX_DEPTH+1):
        size=WORLD_SIZE>>depth
        step=size//8
        if all(v%step==0 for v in (x0,x1,y0,y1,z0,z1)):
            if (x0//size)==((x1-1)//size) and (y0//size)==((y1-1)//size) and (z0//size)==((z1-1)//size):
                return depth
    return MAX_DEPTH

def brushes_to_leaves(brushes: List[Brush], offset) -> List[Leaf]:
    leaves=[]
    for b in brushes:
        xmin,xmax,ymin,ymax,zmin,zmax=b.bounds
        x0=int(xmin+offset[0]); x1=int(xmax+offset[0])
        y0=int(ymin+offset[1]); y1=int(ymax+offset[1])
        z0=int(zmin+offset[2]); z1=int(zmax+offset[2])
        depth=choose_depth(x0,x1,y0,y1,z0,z1)
        size=WORLD_SIZE>>depth
        step=size//8
        ix=x0//size; iy=y0//size; iz=z0//size
        start=[round((x0-ix*size)/step), round((y0-iy*size)/step), round((z0-iz*size)/step)]
        end=[round((x1-ix*size)/step), round((y1-iy*size)/step), round((z1-iz*size)/step)]
        start=[max(0,min(8,s)) for s in start]
        end=[max(0,min(8,e)) for e in end]
        leaves.append(Leaf(depth,ix,iy,iz,start,end,b.textures))
    return leaves

def gather_textures(leaves: List[Leaf]):
    names={'sky':0}
    next_index=1
    for leaf in leaves:
        for tex in leaf.textures.values():
            if tex not in names:
                names[tex]=next_index
                next_index+=1
    names[BASE_TEXTURE]=names.get(BASE_TEXTURE,next_index)
    if BASE_TEXTURE not in names:
        names[BASE_TEXTURE]=next_index
    return names

class Node:
    def __init__(self):
        self.children={}  # index -> Node
        self.leaf: Leaf|None=None

root=Node()

def insert_leaf(leaf:Leaf):
    node=root
    for d in range(leaf.depth):
        shift=MAX_DEPTH-1-d
        idx=((leaf.ix>>shift)&1) | (((leaf.iy>>shift)&1)<<1) | (((leaf.iz>>shift)&1)<<2)
        if idx not in node.children:
            node.children[idx]=Node()
        node=node.children[idx]
    node.leaf=leaf

def build_tree(leaves:List[Leaf]):
    for l in leaves:
        insert_leaf(l)


def encode_node(node:Node, textures:Dict[str,int]) -> bytes:
    if node.leaf:
        leaf=node.leaf
        edges=[]
        for d in range(3):
            start=leaf.start[d]
            end=leaf.end[d]
            val=(end<<4)|start
            for x in (0,1):
                for y in (0,1):
                    edges.append(val)
        solid=all(e==0x88 for e in edges)
        typ=2 if solid else 3
        data=bytearray()
        data.append(typ)
        if typ==3:
            data.extend(bytes(edges))
        for orient in ('x-','x+','y-','y+','z-','z+'):
            t=leaf.textures.get(orient,'sky')
            data.extend(struct.pack('<H', textures.get(t,0)))
        return bytes(data)
    if not node.children:
        # empty cube
        return struct.pack('<B6H',1,*([0]*6))
    out=b'\x00'
    for i in range(8):
        child=node.children.get(i)
        if child is None:
            out+=struct.pack('<B6H',1,*([0]*6))
        else:
            out+=encode_node(child,textures)
    return out

def write_mpz(filename, rootnode:Node, textures:Dict[str,int], spawn_pos):
    texslots=len(textures)
    header=struct.pack('<4sii7i4s', b'MAPZ', MAP_VERSION, 44, WORLD_SIZE,
                        1,0,0,texslots, GAME_VERSION, MAP_REVISION, GAME_ID)
    variables=struct.pack('<i',0)
    texmru=struct.pack('<H',texslots)+b''.join(struct.pack('<H',i) for i in range(texslots))
    ent=struct.pack('<3fB3B', *spawn_pos, 3,0,0,0)+struct.pack('<i7i',7,*([0]*7))+struct.pack('<i',0)
    vslots=b''.join(struct.pack('<ii',0,-1) for _ in range(texslots))
    octree=encode_node(rootnode, textures)
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
    def snap(v:float)->float:
        return round(v/16)*16
    offset=(
        snap(WORLD_SIZE/2-(xmin+xmax)/2),
        snap(WORLD_SIZE/2-(ymin+ymax)/2),
        16 - zmin
    )
    leaves=brushes_to_leaves(brushes, offset)
    textures=gather_textures(leaves)
    build_tree(leaves)
    start_origin,_=parse_player_start('valve220_room.map')
    spawn=(start_origin[0]+offset[0], start_origin[1]+offset[1], start_origin[2]+offset[2])
    write_mpz('valve220_room.mpz', root, textures, spawn)
    write_cfg('valve220_room.cfg', textures)

if __name__=='__main__':
    main()
