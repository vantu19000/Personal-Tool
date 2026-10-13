"""Smoke test for the Hash Calculator tool (run with: python tests/smoke_hash_calculator.py)."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# 1. Tool page renders
r = client.get("/tools/hash-calculator")
assert r.status_code == 200, r.status_code
assert "Hash Calculator" in r.text

# 2. Dashboard lists the tool
r = client.get("/")
assert r.status_code == 200
assert "/tools/hash-calculator" in r.text

# 3. Compute: multiple strings + 2 files, multiple algorithms
text = "hello world\nChào Việt Nam\nabc123\n\n   \n"
data = {
    "text": text,
    "algorithms": "md5,sha256,sha3_256",
}
files = {
    "file_0": ("a.txt", b"file-a-content", "text/plain"),
    "file_1": ("b.bin", b"\x00\x01\x02binary", "application/octet-stream"),
}
r = client.post("/tools/hash-calculator/compute", data=data, files=files)
assert r.status_code == 200, r.text
body = r.json()
assert body["ok"], body
assert body["algorithms"] == ["md5", "sha256", "sha3_256"]

strings = body["strings"]
assert len(strings) == 3, strings  # blank/whitespace-only lines skipped
assert strings[0]["value"] == "hello world"
assert strings[1]["value"] == "Chào Việt Nam"

for s in strings:
    expected = {a: hashlib.new(a, s["value"].encode("utf-8")).hexdigest() for a in body["algorithms"]}
    assert s["hashes"] == expected, s
assert strings[0]["hashes"]["md5"] == hashlib.md5(b"hello world").hexdigest()

files_out = body["files"]
assert len(files_out) == 2
assert files_out[0]["name"] == "a.txt"
assert files_out[0]["size"] == len(b"file-a-content")
assert files_out[0]["hashes"]["md5"] == hashlib.md5(b"file-a-content").hexdigest()
assert files_out[1]["hashes"]["sha256"] == hashlib.sha256(b"\x00\x01\x02binary").hexdigest()

# 4. Default algorithm = md5 when none selected
r = client.post("/tools/hash-calculator/compute", data={"text": "x", "algorithms": ""})
body = r.json()
assert body["ok"] and body["algorithms"] == ["md5"], body
assert body["strings"][0]["hashes"]["md5"] == hashlib.md5(b"x").hexdigest()

# 5. Unsupported algorithm is rejected
r = client.post("/tools/hash-calculator/compute", data={"text": "x", "algorithms": "crc32"})
body = r.json()
assert body["ok"] is False and "crc32" in body["error"], body

# 6. Nothing provided -> friendly error
r = client.post("/tools/hash-calculator/compute", data={"text": "   \n  ", "algorithms": "md5"})
body = r.json()
assert body["ok"] is False, body

# 7. Large file (3 MiB) is hashed correctly chunk-by-chunk
blob = bytes(range(256)) * (3 * 1024 * 1024 // 256)
r = client.post(
    "/tools/hash-calculator/compute",
    data={"text": "", "algorithms": "md5,sha256"},
    files={"file_0": ("big.bin", blob, "application/octet-stream")},
)
body = r.json()
assert body["ok"], body
assert body["files"][0]["size"] == len(blob)
assert body["files"][0]["hashes"]["md5"] == hashlib.md5(blob).hexdigest()
assert body["files"][0]["hashes"]["sha256"] == hashlib.sha256(blob).hexdigest()

print("All smoke tests passed ✔")
print("  md5('hello world') =", hashlib.md5(b"hello world").hexdigest())