import time
import uuid


def uuid7str() -> str:
	"""Generate a UUIDv7 string (time-ordered UUID).

	UUIDv7 features:
	- Time-ordered (monotonic within same millisecond)
	- 48-bit timestamp (milliseconds since epoch)
	- 74 bits of randomness
	- Lexicographically sortable
	"""
	# Get current timestamp in milliseconds
	timestamp_ms = int(time.time() * 1000)

	# Generate random parts
	rand1 = uuid.uuid4().int >> 12  # Use upper bits for less collision risk
	rand2 = uuid.uuid4().int

	# UUIDv7 format (128 bits total):
	# bits 0-47: timestamp_ms (48 bits)
	# bits 48-51: version = 7 (4 bits, value 0x7)
	# bits 52-63: rand_a (12 bits)
	# bits 64-65: variant = 10 (2 bits, value 0x2)
	# bits 66-127: rand_b (62 bits)

	# Build the 128-bit integer
	uuid_int = (timestamp_ms << 80) | (7 << 76) | ((rand1 & 0xFFF) << 64)
	uuid_int = uuid_int | (0x8000000000000000) | (rand2 & 0x3FFFFFFFFFFFFFFF)

	return str(uuid.UUID(int=uuid_int))
