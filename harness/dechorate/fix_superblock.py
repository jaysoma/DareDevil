#!/usr/bin/env python3
"""dEchorate_rirs_gzip7.hdf5 as published on Zenodo (md5 8b42a0e99766acce8a100130774bd5b3) has a version-0 superblock
whose end-of-file address (bytes 40-47) reads 2048, so HDF5 refuses every object past the first 2 KB ("addr overflow,
eoa = 2048"). This writes the file's real size there, in place. Idempotent.

usage: python3 fix_superblock.py path/to/dEchorate_rirs_gzip7.hdf5
"""
import os
import struct
import sys

path = sys.argv[1]
size = os.path.getsize(path)
with open(path, 'r+b') as fh:
    head = fh.read(48)
    assert head[:8] == b'\x89HDF\r\n\x1a\n' and head[8] == 0 and head[13] == 8, 'not a version-0 superblock with 8-byte offsets'
    eoa = struct.unpack('<Q', head[40:48])[0]
    if eoa != size:
        fh.seek(40)
        fh.write(struct.pack('<Q', size))
    print(f'end-of-file address {eoa} -> {size}')
