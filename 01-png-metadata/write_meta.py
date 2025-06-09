# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///


import base64
import io
import json
import pathlib
import struct
import zlib

PNG_HEADER = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def add_meta_zTxt(img: bytes, metadata: str) -> bytes:
    # Ref: https://www.w3.org/TR/png/#11textinfo

    input_buffer = io.BytesIO(img)
    output_buffer = io.BytesIO()

    signature = input_buffer.read(8)

    # Validate PNG signature
    # Ref: https://www.w3.org/TR/PNG-Rationale.html#R.PNG-file-signature
    assert signature == PNG_HEADER, "Invalid PNG file. Unable to verify signature."
    output_buffer.write(signature)

    # PNG provides tEXt, iTXt and zTXt chunks for storing text strings associated with an image.
    # Out of these, we found that tEXt and iTXt were stripped by MS Word/Google Docs on image insert.
    # So we'll go ahead with a zTXt based metadata chunk
    chunk_type = b"zTXt"
    chunk_data = (
        "private_metadata".encode("latin-1")
        + b"\x00\x00"
        + zlib.compress(metadata.encode("latin-1"))
    )
    chunk_crc = zlib.crc32(chunk_type + chunk_data) & 0xFF
    metadata_chunk = (
        struct.pack("!L", len(chunk_data))
        + chunk_type
        + chunk_data
        + struct.pack("!L", chunk_crc)
    )

    written = False
    chunk_type = ""
    while chunk_type != b"IEND":
        header = input_buffer.read(8)
        chunk_len, chunk_type = struct.unpack("!L 4s", header)
        chunk_data = input_buffer.read(chunk_len)
        chunk_crc = input_buffer.read(4)

        # We need to insert our metadata chunk before IDAT chunks.
        # Text chunks inserted after IDAT chunks are sometimes ignored by certain tools
        if (
            not written
            and chunk_type
            in (
                b"IDAT",  # Image data - Actual image data
                b"IEND",  # Image trailer - This occurs at the end of the image. Our last resort to inject metadata
            )
        ):
            output_buffer.write(metadata_chunk)
            written = True

        output_buffer.write(header)
        output_buffer.write(chunk_data)
        output_buffer.write(chunk_crc)

        crc = struct.unpack("!L", chunk_crc)[0]
        expected_crc = zlib.crc32(header[4:8] + chunk_data, 0)
        assert crc == expected_crc, "Bad CRC reading PNG chunk"

    return output_buffer.getvalue()


input_img = pathlib.Path("input.png").read_bytes()

metadata = {"author": "winwinashwin", "sig": 0xDFD2C67DC29EC85FA4E8D54EA4091488}
print(f"Metadata: {metadata}")

data = (
    base64.b64encode(json.dumps(metadata, separators=(",", ":")).encode())
    .decode("utf-8")
    .rstrip("=")
)
print(f"Encoded metadata: {data}")
output_img = add_meta_zTxt(input_img, data)

pathlib.Path("output.png").write_bytes(output_img)
