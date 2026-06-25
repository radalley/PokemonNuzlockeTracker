import argparse
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "Frontend" / "public" / "sprites" / "trainers" / "gen4"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def set_apng_plays_once(path):
    data = bytearray(path.read_bytes())
    if data[:8] != PNG_SIGNATURE:
        return None

    offset = 8
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = bytes(data[offset + 4:offset + 8])
        payload_start = offset + 8
        payload_end = payload_start + length
        crc_start = payload_end
        crc_end = crc_start + 4

        if chunk_type == b"acTL":
            if length != 8:
                raise ValueError(f"Unexpected acTL length in {path}: {length}")
            frames, plays = struct.unpack(">II", data[payload_start:payload_end])
            if plays == 1:
                return False
            data[payload_start:payload_end] = struct.pack(">II", frames, 1)
            crc = zlib.crc32(chunk_type + data[payload_start:payload_end]) & 0xFFFFFFFF
            data[crc_start:crc_end] = struct.pack(">I", crc)
            path.write_bytes(data)
            return True

        offset = crc_end

    return None


def main():
    parser = argparse.ArgumentParser(description="Set Gen IV APNG trainer sprites to play once instead of looping.")
    parser.add_argument("--sprite-dir", default=str(DEFAULT_DIR))
    args = parser.parse_args()

    sprite_dir = Path(args.sprite_dir)
    animated = 0
    updated = 0
    already_once = 0
    for path in sorted(sprite_dir.glob("*.png")):
        result = set_apng_plays_once(path)
        if result is None:
            continue
        animated += 1
        if result:
            updated += 1
        else:
            already_once += 1

    print(f"animated_apng_files: {animated}")
    print(f"updated_to_play_once: {updated}")
    print(f"already_play_once: {already_once}")


if __name__ == "__main__":
    main()
