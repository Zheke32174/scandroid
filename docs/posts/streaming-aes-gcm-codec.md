# A streaming AES-GCM codec for multi-GiB Android backups

*2026-05-09*

Encrypting a vault snapshot is easy. Encrypting an entire phone's
worth of user content — Pictures, Music, Documents, multi-gigabyte
DCIM dirs — is harder than it looks. This is a writeup of the
chunked AES-GCM codec we built for the [understory] cluster's
device-snapshot backups.

[understory]: https://github.com/Zheke32174/scandroid#why-public

## The problem

The existing single-shot codec in `:common-backup` looks like this:

```kotlin
fun encrypt(plaintext: ByteArray, aad: ByteArray, key: KeyMaterial): ByteArray {
    val iv = randomBytes(12)
    val cipher = Cipher.getInstance("AES/GCM/NoPadding")
    cipher.init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(128, iv))
    cipher.updateAAD(aad)
    return iv + cipher.doFinal(plaintext)
}
```

Clean, well-tested, used for vault snapshots that fit in memory.
Tries to encrypt a 50 GiB Pictures directory and the process
either OOMs or the framework throws. `ByteArray` is the wrong
shape for this scale.

The constraint we need: encrypt `InputStream` → `OutputStream`
in fixed-size frames. Memory cost bounded by the frame size, not
by total payload. AES-GCM gives us authenticated encryption per
frame; we just have to glue the frames together in a way that
doesn't break authenticity.

## The format

```
header (cleartext, fixed-size + variable AAD region):
  +-------+--------+-----------------------------------------+
  | off   | size   | field                                   |
  +-------+--------+-----------------------------------------+
  |   0   |  8     | magic = "USTRSTRM" (ASCII)              |
  |   8   |  1     | version (0x01)                          |
  |   9   |  1     | flags (reserved, 0x00)                  |
  |  10   |  2     | reserved (0x0000)                       |
  |  12   |  4     | chunk_plaintext_size (BE, e.g. 1<<20)   |
  |  16   | 32     | argon2id salt                           |
  |  48   | 12     | nonce_prefix (random)                   |
  |  60   |  4     | aad_length (BE)                         |
  |  64   | aad_l  | external AAD (e.g. envelope header)     |
  |  64+  |        | sequence of chunks                      |
  +-------+--------+-----------------------------------------+

each chunk:
  +-------+--------+-----------------------------------------+
  |   0   |  4     | length (BE). High bit (0x80000000) set  |
  |       |        | iff this is the final chunk.            |
  |   4   | length & 0x7FFFFFFF | ciphertext + 16-byte tag   |
  +-------+--------+-----------------------------------------+
```

Plaintext flows in as a stream of bytes. The encoder reads up to
`chunk_plaintext_size` bytes, encrypts that buffer as a complete
AES-GCM block (with its own per-chunk IV + AAD), emits a
length-prefixed ciphertext frame, repeats. The final chunk gets
its high length bit set.

## Per-chunk IV: don't reuse, don't waste

AES-GCM is catastrophically broken if you reuse an `(IV, key)`
pair. Single-shot codecs solve this by generating a fresh random
IV per encryption. For a chunked stream that's wasteful — we'd
spend 12 bytes per chunk on randomness when we already have a
counter.

What we actually do:

```kotlin
private fun chunkIv(noncePrefix: ByteArray, counter: Int): ByteArray {
    val iv = noncePrefix.copyOf()  // 12 random bytes
    iv[8]  = (iv[8]  xor ((counter ushr 24) and 0xFF).toByte()).toByte()
    iv[9]  = (iv[9]  xor ((counter ushr 16) and 0xFF).toByte()).toByte()
    iv[10] = (iv[10] xor ((counter ushr 8)  and 0xFF).toByte()).toByte()
    iv[11] = (iv[11] xor (counter           and 0xFF).toByte()).toByte()
    return iv
}
```

The 12-byte `noncePrefix` is randomly generated per stream and
stored in the cleartext header. For chunk N, we XOR the trailing
4 bytes with the big-endian counter. Properties:

- **Within a stream**: at most 2³² distinct IVs (chunk index
  ranges over Int). At our default 1 MiB chunk, that's 4 PiB of
  plaintext per stream — sufficient.
- **Across streams**: independent random `noncePrefix` values
  give effectively independent IV space. The probability of two
  streams' IVs colliding is the birthday probability across
  12-byte random values, which is negligible at any realistic
  scale.
- **No coordination required**: each stream carries its own
  `noncePrefix` in the header. The decoder reads it back and
  reconstructs the same per-chunk IVs.

Why XOR rather than concatenation? Concatenation would force a
specific layout — the counter has to go at a fixed offset within
the IV. XOR keeps the IV's full 12 bytes random-looking even at
counter=0; nothing about the IV reveals its structure to a
ciphertext-only attacker.

## Per-chunk AAD: defending against reorder + truncation

The first naive design we sketched was: just emit per-chunk GCM
ciphertext, framed by length prefixes. The decoder reads each
frame, runs `cipher.doFinal`, gets plaintext.

That's broken.

An attacker who can modify the ciphertext file (without the key)
can:

- **Swap two chunks**: chunks 5 and 6 each verify under their own
  GCM tags, but the decoder now produces plaintext in the wrong
  order. Particularly nasty for our use case, where the plaintext
  is a packed stream of `[path][content]` tuples; swapping chunks
  can splice file content under the wrong path.
- **Drop the final chunk**: each remaining chunk verifies under
  its own tag. The decoder cleanly exhausts its input and returns
  whatever it managed to decrypt. The user thinks they have a
  complete backup; they have everything except the last 1 MiB.

GCM tags only authenticate one block at a time. To authenticate
relationships *between* blocks, you have to mix the relationship
into each block's AAD.

Our per-chunk AAD:

```
chunk_aad = external_aad || counter_be32 || final_flag_byte
```

- `external_aad` is the caller-supplied AAD from the cleartext
  header. In the device-snapshot case, this is a deterministic
  encoding of the parent envelope's identity — `(appId,
  schemaVersion, createdAtMs, label)`. Mixing it in every chunk
  binds the stream to the envelope.
- `counter_be32` makes chunk 5 and chunk 6 carry different AADs.
  Swap them: each one's GCM tag was computed under its real
  counter; the decoder verifies them under the swapped counters;
  both fail. Drop one: subsequent chunks now decrypt under the
  wrong counter; they fail too.
- `final_flag_byte` is `0x01` for the last chunk, `0x00`
  otherwise. The encoder knows which chunk is final and sets the
  flag accordingly. Drop the final chunk + try to pass the
  previous one off as final: GCM rejects it because its tag was
  computed with `final_flag = 0x00`.

```kotlin
private fun chunkAad(externalAad: ByteArray, counter: Int, isFinal: Boolean): ByteArray {
    val out = ByteArray(externalAad.size + 4 + 1)
    System.arraycopy(externalAad, 0, out, 0, externalAad.size)
    out[externalAad.size + 0] = ((counter ushr 24) and 0xFF).toByte()
    out[externalAad.size + 1] = ((counter ushr 16) and 0xFF).toByte()
    out[externalAad.size + 2] = ((counter ushr 8) and 0xFF).toByte()
    out[externalAad.size + 3] = (counter and 0xFF).toByte()
    out[externalAad.size + 4] = if (isFinal) 0x01 else 0x00
    return out
}
```

Cost: 5 extra bytes of AAD per chunk. AAD doesn't appear in the
ciphertext; it just feeds GCM's tag computation. Free.

## The look-ahead trick

The `final_flag_byte` mechanism above has a subtle requirement:
the encoder has to set it on the *current* chunk, not the next
one. Which means at write-time, the encoder must already know
whether the chunk it's about to emit is the last one.

Naive implementation: read all of the input into memory, count
the chunks, emit them in a loop. Defeats the streaming property.

Look-ahead instead:

```kotlin
var read = readFully(plaintext, buf, 0, chunkSize)  // initial read
var counter = 0
while (true) {
    val nextBuf = ByteArray(chunkSize)
    val nextRead = if (read == chunkSize) readFully(plaintext, nextBuf, 0, chunkSize)
                   else 0
    val isFinal = (read < chunkSize) || nextRead == 0
    writeChunk(out, key, noncePrefix, counter, buf, read, externalAad, isFinal)
    if (isFinal) break
    System.arraycopy(nextBuf, 0, buf, 0, nextRead)
    read = nextRead
    counter++
}
```

We always have one chunk's worth of plaintext "in flight"
(`buf`) plus an optional next chunk in `nextBuf`. Memory cost:
two buffers — bounded. We read ahead just far enough to know
whether the current chunk is the last, then emit it with the
correct `final_flag`.

This pattern shows up a lot in streaming protocols. It's worth
calling out because it's the difference between "this codec
streams" and "this codec quietly buffers everything before
emitting."

## Edge case: empty plaintext

What does the encoder produce when given an empty `InputStream`?

- `read = readFully(...)` returns 0.
- `isFinal = (0 < chunkSize)` is true.
- `writeChunk(..., len=0, isFinal=true)` is called.
- `cipher.doFinal(buf, 0, 0)` returns the 16-byte GCM tag and
  nothing else.
- The resulting frame is `[4-byte length = 16 | 0x80000000][16
  bytes tag]`.

The decoder must accept this. Our first cut had a defensive
check `if (ctLen <= GCM_TAG_BYTES) throw IOException(...)` —
that rejected the legitimate empty-plaintext case (where ctLen
== GCM_TAG_BYTES exactly). One of the unit tests caught it. Fix:
`<` instead of `<=`. The decoder's invariant is "ciphertext must
be at least as long as the GCM tag," not "must be longer than."

The thing this teaches: when you write a streaming codec, your
edge cases are 0, 1, exactly chunkSize, exactly chunkSize+1, and
N×chunkSize for small N. All of those want unit tests.

## What's NOT in the format

A lot of what I've shipped before in this kind of project, and
deliberately left out here:

- **No compression**. The codec encrypts whatever you give it.
  The caller decides whether to compress upstream. Mixing
  compression and encryption in one layer is a CRIME (compression
  ratio side-channel) waiting to happen.
- **No checksums beyond GCM**. The 128-bit GCM tag is already an
  authenticated check; CRC32 or SHA256 atop it would just slow
  things down without adding security.
- **No magic per chunk**. Just per stream. The chunk's length
  prefix + GCM tag are enough for the decoder; redundant per-chunk
  magic would only help misuse cases (manually editing a stream),
  and we don't want to support those.
- **No version per chunk**. The whole stream's version is in the
  header. If the format ever changes meaningfully, we bump the
  magic so old readers can't half-parse a new file.

## Threat properties, summarized

| Property | Mechanism |
|---|---|
| Confidentiality | AES-256-GCM per chunk |
| Per-chunk integrity | 128-bit GCM tag |
| Reorder resistance | counter in chunk AAD |
| Truncation resistance | final-flag in chunk AAD |
| Cross-stream IV reuse | independent random nonce_prefix per stream |
| Header tampering | argon2id salt + chunk_size in header are inputs to per-chunk decryption — a tampered header makes every chunk fail |
| Cross-stream substitution | external_aad (envelope identity) bound into chunk AAD — a stream from snapshot A under snapshot B's envelope fails on chunk 0 |

The single thing the codec doesn't defend against is a passive
attacker observing how many chunks the file has + how big each
ciphertext frame is. That's traffic analysis territory; padding
to fixed chunk size handles it but costs a lot of disk space at
GiB scale. Out of scope for this version.

## Compatibility

This is intentionally NOT a `BackupCodec` (the buffer-in /
buffer-out interface used elsewhere in the cluster). The two
formats coexist. Single-shot vault snapshots stay on the buffer
codec; multi-GiB device snapshots use the streaming codec. Same
suite, two tools, picked per use case.

The Wave B-2 wiring that consumed this codec lives in the
`backups` module of understory: `DeviceSnapshotService` writes a
`device-<ts>.usbe` JSON envelope (small, settings + manifest)
plus an opt-in `device-<ts>.usbs` streaming companion (large,
file contents). Bound together via the `external_aad`
mechanism above.

## Code

- Codec: [`StreamingAesGcmCodec.kt`][src] in
  [understory/android/common-backup][repo].
- Tests: [`StreamingAesGcmCodecTest.kt`][test] — 17 tests
  covering round-trip + tamper-detection + chunk-boundary
  edges. All passing.

[src]: https://github.com/Zheke32174/understory/blob/master/android/common-backup/src/main/java/com/understory/backup/StreamingAesGcmCodec.kt
[test]: https://github.com/Zheke32174/understory/blob/master/android/common-backup/src/test/java/com/understory/backup/StreamingAesGcmCodecTest.kt
[repo]: https://github.com/Zheke32174/understory

The understory repo is private. The codec design is in the open
because the format itself isn't a secret — what matters is the
key, which never leaves the user's device.
