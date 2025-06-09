# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///


import io
import struct
import zlib
import base64
import json
import pathlib

PNG_HEADER = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def read_meta_zTxt(img: bytes) -> str | None:
    buffer = io.BytesIO(img)

    # Validate PNG signature
    signature = buffer.read(8)
    assert signature == PNG_HEADER, "Invalid PNG file"

    while True:
        header = buffer.read(8)
        if len(header) < 8:
            break  # EOF or malformed

        chunk_len, chunk_type = struct.unpack("!L 4s", header)
        chunk_data = buffer.read(chunk_len)
        _chunk_crc = buffer.read(4)

        if chunk_type == b"zTXt":
            try:
                # The format is: <keyword>\x00<compression_method><compressed_text>
                null_idx = chunk_data.index(b"\x00")
                keyword = chunk_data[:null_idx].decode("latin-1")
                compression_method = chunk_data[null_idx + 1]
                compressed_text = chunk_data[null_idx + 2 :]

                if keyword == "private_metadata" and compression_method == 0:
                    metadata = zlib.decompress(compressed_text).decode("latin-1")
                    return metadata
            except Exception as e:
                raise RuntimeError(f"Error parsing zTXt chunk: {e}")

        if chunk_type == b"IEND":
            break

    return None


img_bytes = pathlib.Path("output.png").read_bytes()
b64_metadata = read_meta_zTxt(img_bytes)
if b64_metadata is None:
    print("No metadata found.")
else:
    # Pad with "=" if needed for base64 decoding
    padding = "=" * (-len(b64_metadata) % 4)
    json_data = base64.b64decode(b64_metadata + padding).decode()
    metadata = json.loads(json_data)
    print("Decoded metadata:", metadata)
