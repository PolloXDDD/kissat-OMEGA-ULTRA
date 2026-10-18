#!/usr/bin/env python3
"""Exact reproducible SHA3-256 24-round / 64-bit-message collision CNF.
SHA-256: 249ad83e8f3198d1dcc580cfaec023c5078ba24378fe7337c798158b338bcead
310636 variables; 1156185 clauses. Verified byte-for-byte against original upload.
"""
import argparse
import hashlib
from pathlib import Path

RC=[0x0000000000000001,0x0000000000008082,0x800000000000808a,0x8000000080008000,
0x000000000000808b,0x0000000080000001,0x8000000080008081,0x8000000000008009,
0x000000000000008a,0x0000000000000088,0x0000000080008009,0x000000008000000a,
0x000000008000808b,0x800000000000008b,0x8000000000008089,0x8000000000008003,
0x8000000000008002,0x8000000000000080,0x000000000000800a,0x800000008000000a,
0x8000000080008081,0x8000000000008080,0x0000000080000001,0x8000000080008008]
RHO=[[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],
     [28,55,25,21,56],[27,20,39,8,14]]
HASH="249ad83e8f3198d1dcc580cfaec023c5078ba24378fe7337c798158b338bcead"

class Gen:
    def __init__(self,out):
        self.v=128
        self.n=0
        self.f=out
    def clause(self,*xs):
        self.f.write(" ".join(map(str,xs))+" 0\n")
        self.n+=1
    def new(self):
        self.v+=1
        return self.v
    def xor(self,a,b):
        c=self.new()
        self.clause(a,b,-c)
        self.clause(-a,-b,-c)
        self.clause(-a,b,c)
        self.clause(a,-b,c)
        return c
    def andnot(self,a,b):
        c=self.new()
        self.clause(a,-b,c)
        self.clause(-a,-c)
        self.clause(b,-c)
        return c
    def neg(self,a):
        c=self.new()
        self.clause(-a,-c)
        self.clause(a,c)
        return c
    def state(self,base):
        a=[]
        for i in range(1600):
            if i<64:
                v=base+i
            else:
                v=self.new()
                self.clause(v if i in (65,66,1087) else -v)
            a.append(v)
        return a
    @staticmethod
    def index(x,y,z):
        return (x+5*y)*64+z
    def permute(self,a):
        X=self.index
        for rc in RC:
            C=[0]*320
            for x in range(5):
                for z in range(64):
                    c=a[X(x,0,z)]
                    for y in range(1,5):
                        c=self.xor(c,a[X(x,y,z)])
                    C[x*64+z]=c
            D=[0]*320
            for x in range(5):
                for z in range(64):
                    D[x*64+z]=self.xor(C[((x-1)%5)*64+z],
                                         C[((x+1)%5)*64+(z-1)%64])
            T=[0]*1600
            for x in range(5):
                for y in range(5):
                    for z in range(64):
                        T[X(x,y,z)]=self.xor(a[X(x,y,z)],D[x*64+z])
            B=[0]*1600
            for x in range(5):
                for y in range(5):
                    for z in range(64):
                        B[X(y,(2*x+3*y)%5,(z+RHO[x][y])%64)]=T[X(x,y,z)]
            A=[0]*1600
            for y in range(5):
                for z in range(64):
                    for x in range(5):
                        t=self.andnot(B[X((x+1)%5,y,z)],B[X((x+2)%5,y,z)])
                        A[X(x,y,z)]=self.xor(B[X(x,y,z)],t)
            for z in range(64):
                if (rc>>z)&1:
                    A[X(0,0,z)]=self.neg(A[X(0,0,z)])
            a=A
        return a

def generate(out):
    out.write("c SHA-3/256 collision search\n")
    out.write("c Keccak-f[1600], 24 rounds, SIN REDUCIR\n")
    out.write("c Messages: 64 bits each\n")
    out.write("c msg1 vars: 1..64\n")
    out.write("c msg2 vars: 65..128\n")
    out.write("p cnf 310636 1156185\n")
    g=Gen(out)
    a=g.permute(g.state(1))
    b=g.permute(g.state(65))
    for i in range(256):
        g.clause(a[i],-b[i])
        g.clause(-a[i],b[i])
    diff=[g.xor(i+1,i+65) for i in range(64)]
    g.clause(*diff)
    assert (g.v,g.n)==(310636,1156185)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("output",nargs="?",default="benchmarks/sha3_collision_5.cnf")
    a=p.parse_args()
    path=Path(a.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="\n") as out:
        generate(out)
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    digest=h.hexdigest()
    print(f"generated={path} bytes={path.stat().st_size} sha256={digest}")
    if digest!=HASH:
        raise SystemExit(f"ERROR: generator differs from verified input (wanted {HASH})")

if __name__=="__main__":
    main()
