"""
Enhanced protocol module with length-prefix framing, MessagePack serialization,
and comprehensive message validation using JSON Schema.
"""

import struct
import json
from typing import Dict, Any, Optional

try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class ProtocolException(Exception):
    """Raised when protocol validation fails"""
    pass


# JSON Schema for message validation
MESSAGE_SCHEMAS = {
    "base": {
        "type": "object",
        "required": ["type", "id"],
        "properties": {
            "type": {
                "type": "string",
                "minLength": 1,
                "maxLength": 50
            },
            "id": {
                "type": ["string", "integer"],
                "minLength": 1,
                "maxLength": 100
            },
            "data": {
                "type": "object"
            }
        },
        "additionalProperties": False
    },

    "authenticate": {
        "type": "object",
        "required": ["type", "id", "data"],
        "properties": {
            "type": {"const": "authenticate"},
            "id": {"type": ["string", "integer"]},
            "data": {
                "type": "object",
                "required": ["token"],
                "properties": {
                    "token": {
                        "type": "string",
                        "minLength": 16,
                        "maxLength": 256
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    },

    "execute_code": {
        "type": "object",
        "required": ["type", "id", "data"],
        "properties": {
            "type": {"const": "execute_code"},
            "id": {"type": ["string", "integer"]},
            "data": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 102400  # 100KB max
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    },

    "list_layers": {
        "type": "object",
        "required": ["type", "id"],
        "properties": {
            "type": {"const": "list_layers"},
            "id": {"type": ["string", "integer"]},
            "data": {
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10000
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    },

    "get_features": {
        "type": "object",
        "required": ["type", "id", "data"],
        "properties": {
            "type": {"const": "get_features"},
            "id": {"type": ["string", "integer"]},
            "data": {
                "type": "object",
                "required": ["layer_id"],
                "properties": {
                    "layer_id": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 256
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10000
                    },
                    "bbox": {
                        "type": "object",
                        "required": ["xmin", "ymin", "xmax", "ymax"],
                        "properties": {
                            "xmin": {"type": "number"},
                            "ymin": {"type": "number"},
                            "xmax": {"type": "number"},
                            "ymax": {"type": "number"}
                        }
                    },
                    "filter_expression": {
                        "type": "string",
                        "maxLength": 10000
                    },
                    "attributes_only": {"type": "boolean"},
                    "simplify_tolerance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1000
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    },

    "load_layer": {
        "type": "object",
        "required": ["type", "id", "data"],
        "properties": {
            "type": {"const": "load_layer"},
            "id": {"type": ["string", "integer"]},
            "data": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 4096
                    },
                    "layer_name": {
                        "type": "string",
                        "maxLength": 256
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    },

    "response": {
        "type": "object",
        "required": ["type", "id", "success"],
        "properties": {
            "type": {"const": "response"},
            "id": {"type": ["string", "integer"]},
            "success": {"type": "boolean"},
            "data": {
                "type": ["object", "array", "string", "number", "boolean", "null"]
            },
            "error": {
                "type": "string",
                "maxLength": 1000
            }
        },
        "additionalProperties": False
    }
}


class ProtocolHandler:
    """Handles message serialization and deserialization with length-prefix protocol"""

    # Message header format: 4-byte unsigned int, big-endian
    MESSAGE_HEADER_FORMAT = '!I'
    HEADER_SIZE = struct.calcsize(MESSAGE_HEADER_FORMAT)

    # Maximum message size: 10MB (more conservative than before)
    MAX_MESSAGE_SIZE = 10 * 1024 * 1024

    def __init__(self, use_msgpack: bool = True, validate_schema: bool = True):
        """
        Initialize protocol handler

        Args:
            use_msgpack: Use MessagePack if available, otherwise use JSON
            validate_schema: Validate messages against JSON schema
        """
        self.use_msgpack = use_msgpack and HAS_MSGPACK
        self.validate_schema = validate_schema and HAS_JSONSCHEMA

        if self.validate_schema and not HAS_JSONSCHEMA:
            import warnings
            warnings.warn(
                "jsonschema not available, message validation disabled. "
                "Install with: pip install jsonschema"
            )

    def serialize(self, data: Dict[str, Any]) -> bytes:
        """
        Serialize data to bytes

        Args:
            data: Dictionary to serialize

        Returns:
            Serialized bytes

        Raises:
            ProtocolException: If serialization fails
        """
        try:
            if self.use_msgpack:
                return msgpack.packb(data, use_bin_type=True)
            else:
                return json.dumps(data).encode('utf-8')
        except (TypeError, ValueError) as e:
            raise ProtocolException(f"Serialization failed: {e}")

    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """
        Deserialize bytes to dictionary

        Args:
            data: Bytes to deserialize

        Returns:
            Deserialized dictionary

        Raises:
            ProtocolException: If deserialization fails
        """
        try:
            if self.use_msgpack:
                result = msgpack.unpackb(data, raw=False)
            else:
                result = json.loads(data.decode('utf-8'))

            if not isinstance(result, dict):
                raise ProtocolException(
                    f"Message must be a dictionary, got {type(result).__name__}"
                )

            return result
        except (TypeError, ValueError, UnicodeDecodeError) as e:
            raise ProtocolException(f"Deserialization failed: {e}")

    def validate_message(self, message: Dict[str, Any]) -> None:
        """
        Validate message structure against JSON schema

        Args:
            message: Message to validate

        Raises:
            ProtocolException: If validation fails
        """
        if not self.validate_schema:
            return

        # Check basic structure first
        if not isinstance(message, dict):
            raise ProtocolException("Message must be a dictionary")

        if "type" not in message:
            raise ProtocolException("Message must have 'type' field")

        if "id" not in message:
            raise ProtocolException("Message must have 'id' field")

        message_type = message.get("type")

        # Get appropriate schema
        schema = MESSAGE_SCHEMAS.get(message_type)
        if not schema:
            # Use base schema for unknown types
            schema = MESSAGE_SCHEMAS["base"]

        # Validate against schema
        try:
            validate(instance=message, schema=schema)
        except ValidationError as e:
            raise ProtocolException(f"Schema validation failed: {e.message}")

    def pack_message(self, message_dict: Dict[str, Any]) -> bytes:
        """
        Pack a message with length prefix

        Args:
            message_dict: Message dictionary to pack

        Returns:
            Packed message with length prefix

        Raises:
            ProtocolException: If message validation or packing fails
        """
        # Validate message structure
        self.validate_message(message_dict)

        # Serialize message
        message_bytes = self.serialize(message_dict)
        message_len = len(message_bytes)

        # Check size limit
        if message_len > self.MAX_MESSAGE_SIZE:
            raise ProtocolException(
                f"Message too large: {message_len} bytes "
                f"(max: {self.MAX_MESSAGE_SIZE})"
            )

        # Pack length as 4-byte header
        header = struct.pack(self.MESSAGE_HEADER_FORMAT, message_len)

        return header + message_bytes

    def send_message(self, socket, message_dict: Dict[str, Any]) -> None:
        """
        Send a message over a socket with length prefix

        Args:
            socket: Socket to send on
            message_dict: Message to send

        Raises:
            ProtocolException: If message is invalid or too large
            socket.error: If send fails
        """
        packed_message = self.pack_message(message_dict)
        socket.sendall(packed_message)

    def receive_message(
        self,
        socket,
        timeout: Optional[float] = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Receive a message from a socket with length prefix

        Args:
            socket: Socket to receive from
            timeout: Timeout in seconds (None for blocking)

        Returns:
            Received message dictionary or None if connection closed

        Raises:
            ProtocolException: If message is invalid or exceeds size limit
            socket.timeout: If timeout exceeded
            socket.error: If receive fails
        """
        if timeout is not None:
            socket.settimeout(timeout)

        try:
            # Read exact header size
            header_data = self._recv_exact(socket, self.HEADER_SIZE)
            if not header_data:
                return None

            # Unpack message length
            message_len = struct.unpack(self.MESSAGE_HEADER_FORMAT, header_data)[0]

            # Validate size
            if message_len > self.MAX_MESSAGE_SIZE:
                raise ProtocolException(
                    f"Message size {message_len} exceeds limit "
                    f"of {self.MAX_MESSAGE_SIZE}"
                )

            if message_len == 0:
                raise ProtocolException("Received message with zero length")

            # Read exact message size
            message_data = self._recv_exact(socket, message_len)
            if not message_data:
                return None

            # Deserialize
            message = self.deserialize(message_data)

            # Validate message structure
            self.validate_message(message)

            return message

        finally:
            if timeout is not None:
                socket.settimeout(None)  # Reset to blocking

    def _recv_exact(self, socket, num_bytes: int) -> Optional[bytes]:
        """
        Receive exactly num_bytes from socket

        Args:
            socket: Socket to receive from
            num_bytes: Number of bytes to receive

        Returns:
            Received bytes or None if connection closed

        Raises:
            socket.error: If receive fails
            ProtocolException: If connection closes prematurely
        """
        chunks = []
        bytes_received = 0

        while bytes_received < num_bytes:
            chunk = socket.recv(min(num_bytes - bytes_received, 8192))
            if not chunk:
                # Connection closed
                if bytes_received == 0:
                    return None
                raise ProtocolException(
                    f"Socket closed before message complete "
                    f"({bytes_received}/{num_bytes} bytes received)"
                )

            chunks.append(chunk)
            bytes_received += len(chunk)

        return b''.join(chunks)


class BufferedProtocolHandler(ProtocolHandler):
    """Protocol handler with internal buffer for non-blocking sockets"""

    def __init__(self, use_msgpack: bool = True, validate_schema: bool = True):
        super().__init__(use_msgpack, validate_schema)
        self.buffer = bytearray()
        self.expected_message_size = None

    def feed_data(self, data: bytes) -> None:
        """
        Feed data into the buffer

        Args:
            data: Bytes to add to buffer

        Raises:
            ProtocolException: If buffer exceeds maximum size
        """
        if len(self.buffer) + len(data) > self.MAX_MESSAGE_SIZE:
            raise ProtocolException(
                f"Buffer overflow: {len(self.buffer) + len(data)} bytes "
                f"exceeds maximum of {self.MAX_MESSAGE_SIZE}"
            )

        self.buffer.extend(data)

    def try_read_message(self) -> Optional[Dict[str, Any]]:
        """
        Try to read a complete message from the buffer

        Returns:
            Message dictionary if complete message available, None otherwise

        Raises:
            ProtocolException: If message is invalid or size exceeds limit
        """
        # Need at least header size
        if len(self.buffer) < self.HEADER_SIZE:
            return None

        # Parse message size if not already done
        if self.expected_message_size is None:
            header_data = bytes(self.buffer[:self.HEADER_SIZE])
            self.expected_message_size = struct.unpack(
                self.MESSAGE_HEADER_FORMAT,
                header_data
            )[0]

            # Validate size
            if self.expected_message_size > self.MAX_MESSAGE_SIZE:
                self.clear_buffer()
                raise ProtocolException(
                    f"Message size {self.expected_message_size} exceeds limit "
                    f"of {self.MAX_MESSAGE_SIZE}"
                )

            if self.expected_message_size == 0:
                self.clear_buffer()
                raise ProtocolException("Received message with zero length")

        # Check if we have the complete message
        total_size = self.HEADER_SIZE + self.expected_message_size
        if len(self.buffer) < total_size:
            return None

        # Extract message data
        message_data = bytes(
            self.buffer[self.HEADER_SIZE:total_size]
        )

        # Remove processed data from buffer
        del self.buffer[:total_size]
        self.expected_message_size = None

        # Deserialize
        message = self.deserialize(message_data)

        # Validate message structure
        self.validate_message(message)

        return message

    def clear_buffer(self) -> None:
        """Clear the internal buffer"""
        self.buffer.clear()
        self.expected_message_size = None

    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        return len(self.buffer)
