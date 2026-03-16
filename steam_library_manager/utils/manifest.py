#
# steam_library_manager/utils/manifest.py
# Parser for Steam depot manifest files (protobuf-based)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import struct
from typing import BinaryIO, Any

try:
    from .manifest_pb2 import Payload, Metadata, Signature
except ImportError:
    # Fallback for direct call
    from manifest_pb2 import Payload, Metadata, Signature

__all__ = ("load", "loads")

MSG_PAYLOAD = 0x71F617D0
MSG_METADATA = 0x1F4812BE
MSG_SIGNATURE = 0x1B81B817
MSG_EOF = 0x32C415AB

MSG_NAMES = {
    MSG_PAYLOAD: "payload",
    MSG_METADATA: "metadata",
    MSG_SIGNATURE: "signature",
}

MessageClass = {MSG_PAYLOAD: Payload, MSG_METADATA: Metadata, MSG_SIGNATURE: Signature}


def loads(data: bytes, wrapper=dict) -> dict[str, Any]:
    """Parse a Steam depot manifest from raw bytes."""
    parsed = wrapper()
    offset = 0
    int32 = struct.Struct("<I")

    while offset < len(data):
        msg_id = int32.unpack_from(data, offset)[0]
        offset += int32.size

        if msg_id == MSG_EOF:
            break

        msg_size = int32.unpack_from(data, offset)[0]
        offset += int32.size

        msg_data = data[offset : offset + msg_size]
        offset += msg_size

        if msg_id in MessageClass:
            message = MessageClass[msg_id]()
            message.ParseFromString(msg_data)
            # Convert Protobuf object to dict
            from google.protobuf.json_format import MessageToDict

            parsed[MSG_NAMES[msg_id]] = MessageToDict(message, preserving_proto_field_name=True)

    return parsed


def load(fp: BinaryIO, wrapper=dict) -> dict[str, Any]:
    """Parse a Steam depot manifest from a file object."""
    return loads(fp.read(), wrapper=wrapper)
