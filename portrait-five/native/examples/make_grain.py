"""Generate the neutral paper grain used by the poster native example (no third-party assets)."""
from pathlib import Path
import argparse
import random
import struct
import zlib


def make_grain(path):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag+data))
    rng = random.Random(624)
    size = 192
    data = b"".join(b"\x00" + bytes(rng.randrange(50, 206) for _ in range(size)) for _ in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 0, 0, 0, 0)
    with Path(path).open("xb") as file:
        file.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR",header) + chunk(b"IDAT",zlib.compress(data)) + chunk(b"IEND",b""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    make_grain(parser.parse_args().output)
