const TON_BOC_MAGIC = [0xb5, 0xee, 0x9c, 0x72];
const MAX_SINGLE_CELL_COMMENT_BYTES = 123;

function crc32c(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ ((crc & 1) ? 0x82f63b78 : 0);
    }
  }
  crc = (~crc) >>> 0;
  return new Uint8Array([
    crc & 0xff,
    (crc >>> 8) & 0xff,
    (crc >>> 16) & 0xff,
    (crc >>> 24) & 0xff,
  ]);
}

function concatBytes(...chunks) {
  const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return result;
}

function bytesToBase64(bytes) {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

export function encodeTonTextCommentPayload(comment) {
  const textBytes = new TextEncoder().encode(comment || "");
  if (textBytes.length > MAX_SINGLE_CELL_COMMENT_BYTES) {
    throw new Error("Memo слишком длинный для TON transfer payload");
  }

  // TON text comment payload is a single ordinary cell:
  // 32-bit zero opcode followed by UTF-8 comment bytes.
  const data = new Uint8Array(4 + textBytes.length);
  data.set(textBytes, 4);

  const cell = new Uint8Array(2 + data.length);
  cell[0] = 0x00;
  cell[1] = data.length * 2;
  cell.set(data, 2);

  const header = new Uint8Array([
    ...TON_BOC_MAGIC,
    0x41, // no index, CRC32C enabled, one-byte counters
    0x01, // offsets are encoded in one byte
    0x01, // cells count
    0x01, // roots count
    0x00, // absent cells count
    cell.length,
    0x00, // root cell index
  ]);
  const bocWithoutChecksum = concatBytes(header, cell);
  return bytesToBase64(concatBytes(bocWithoutChecksum, crc32c(bocWithoutChecksum)));
}
