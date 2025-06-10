from __future__ import annotations
# Experimental converter that voxelises brushes at high resolution
# then rebuilds larger cubes when writing the final octree.
# This demonstrates a simple approach to "successive voxellization"
# followed by merging ("un-voxellisation").

import struct
import gzip
import re
from typing import List, Dict, Tuple

MAP_VERSION = 45
WORLD_SIZE = 512
GAME_VERSION = 281
GAME_ID = b"fps\0"
MAP_REVISION = 1

ORIENT_INDEX = {
    'x-': 0,
    'x+': 1,
    'y-': 2,
    'y+': 3,
    'z-': 4,
    'z+': 5,
}

MAX_DEPTH = 5
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
def gather_textures(leaves: List[Leaf]):
    names={"sky":0}
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


class Leaf:
    def __init__(self, depth:int, ix:int, iy:int, iz:int, start, end, textures:Dict[str,str]):
        self.depth=depth
        self.ix=ix; self.iy=iy; self.iz=iz
        self.start=start
        self.end=end
        self.textures=textures

def point_in_brush(pt, brush:Brush) -> bool:
    x,y,z = pt
    for plane, _ in brush.planes:
        p0,p1,p2 = plane
        v1 = (p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2])
        v2 = (p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2])
        nx = v1[1]*v2[2] - v1[2]*v2[1]
        ny = v1[2]*v2[0] - v1[0]*v2[2]
        nz = v1[0]*v2[1] - v1[1]*v2[0]
        if (x-p0[0])*nx + (y-p0[1])*ny + (z-p0[2])*nz > 0:
            return False
    return True

def voxellize_brush(brush:Brush, offset) -> List[Leaf]:
    leaves=[]
    step = WORLD_SIZE >> MAX_DEPTH
    xmin,xmax,ymin,ymax,zmin,zmax = brush.bounds
    x0=int(xmin+offset[0]); x1=int(xmax+offset[0])
    y0=int(ymin+offset[1]); y1=int(ymax+offset[1])
    z0=int(zmin+offset[2]); z1=int(zmax+offset[2])
    gx0=(x0//step)*step
    gx1=((x1+step-1)//step)*step
    gy0=(y0//step)*step
    gy1=((y1+step-1)//step)*step
    gz0=(z0//step)*step
    gz1=((z1+step-1)//step)*step
    for x in range(gx0,gx1,step):
        for y in range(gy0,gy1,step):
            for z in range(gz0,gz1,step):
                cx=x+step/2
                cy=y+step/2
                cz=z+step/2
                if point_in_brush((cx-offset[0],cy-offset[1],cz-offset[2]), brush):
                    ix=x//step
                    iy=y//step
                    iz=z//step
                    leaves.append(Leaf(MAX_DEPTH, ix, iy, iz, [0,0,0], [8,8,8], brush.textures))
    return leaves

class Node:
    def __init__(self):
        self.children={}
        self.leaf:Leaf|None=None

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

def merge(node:Node):
    if node.leaf:
        return node
    for i in range(8):
        child=node.children.get(i)
        if child:
            merge(child)
    if len(node.children)==8:
        first=node.children[0]
        if all(c.leaf and c.leaf.textures==first.leaf.textures for c in node.children.values()):
            tex=first.leaf.textures
            depth=first.leaf.depth-1
            ix=first.leaf.ix//2
            iy=first.leaf.iy//2
            iz=first.leaf.iz//2
            node.children={}
            node.leaf=Leaf(depth,ix,iy,iz,[0,0,0],[8,8,8],tex)
    return node

def encode_node(node:Node, textures:Dict[str,int]) -> bytes:
    if node.leaf:
        leaf=node.leaf
        edges=[]
        for d in range(3):
            start=leaf.start[d]
            end=leaf.end[d]
            val=(end<<4)|start
            for _ in range(4):
                edges.append(val)
        solid=all(e==0x88 for e in edges)
        typ=2 if solid else 3
        data=bytearray()
        data.append(typ)
        if typ==3:
            data.extend(bytes(edges))
        for orient in ('x-','x+','y-','y+','z-','z+'):
            t=leaf.textures.get(orient,BASE_TEXTURE)
            data.extend(struct.pack('<H', textures.get(t,0)))
        return bytes(data)
    if not node.children:
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
    leaves=[]
    for b in brushes:
        leaves.extend(voxellize_brush(b, offset))
    textures=gather_textures(leaves)
    build_tree(leaves)
    merge(root)
    start_origin,_=parse_player_start('valve220_room.map')
    spawn=(start_origin[0]+offset[0], start_origin[1]+offset[1], start_origin[2]+offset[2])
    write_mpz('valve220_room_vx.mpz', root, textures, spawn)
    write_cfg('valve220_room_vx.cfg', textures)

if __name__=='__main__':
    main()
