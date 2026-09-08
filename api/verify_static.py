"""Static verification — run without DB."""
import sys, os
sys.path.insert(0, ".")

# ---- Models ----
from app.models import Base, User, Show, Season, Episode, Artwork, PublishRun, ContentIssue, ShowCategory
tables = sorted(Base.metadata.tables.keys())
print("Tables in metadata:", tables)
assert set(tables) == {
    "users", "shows", "show_categories", "seasons",
    "episodes", "artwork", "publish_runs", "content_issues"
}, f"Unexpected tables: {tables}"

# ---- JWT ----
from app.auth.jwt import create_access_token, decode_access_token, extract_role
token = create_access_token({"sub": "test-id", "role": "admin"})
payload = decode_access_token(token)
assert payload["sub"] == "test-id"
assert payload["role"] == "admin"
assert extract_role(token) == "admin"
assert extract_role("bad.token.here") is None
print("JWT OK")

# ---- Storage ----
import tempfile
from app.storage.local import LocalDiskStorage
with tempfile.TemporaryDirectory() as td:
    s = LocalDiskStorage(root=td, base_url="http://localhost/media")
    s.put("test/file.txt", b"hello", "text/plain")
    assert s.get("test/file.txt") == b"hello"
    assert s.exists("test/file.txt")
    assert not s.exists("nope.txt")
    assert s.url_for("test/file.txt") == "http://localhost/media/test/file.txt"
    s.atomic_pointer_write("ptr.json", b'{"v": 1}')
    assert s.get("ptr.json") == b'{"v": 1}'
    s.atomic_pointer_write("ptr.json", b'{"v": 2}')
    assert s.get("ptr.json") == b'{"v": 2}'
print("Storage OK")

# ---- Artwork validator ----
asset_dir = r"c:\Users\Rahul\OneDrive\Desktop\PebloAssessment\assets"
from app.services.artwork_validator import validate_artwork

tests = [
    ("poster", "poster_good.jpg", True),
    ("poster", "poster_wrong_ratio.jpg", False),
    ("banner", "banner_good.jpg", True),
    ("banner", "banner_too_big.png", False),
    ("thumbnail", "thumb_good.jpg", True),
    ("thumbnail", "thumb_tiny.jpg", False),
]
for kind, fname, expected_valid in tests:
    data = open(os.path.join(asset_dir, fname), "rb").read()
    r = validate_artwork(kind, data)
    status = "PASS" if r.valid == expected_valid else "FAIL"
    print(f"  [{status}] {fname} -> valid={r.valid}, errors={r.errors}")
    assert r.valid == expected_valid, f"Expected valid={expected_valid} for {fname}"
print("Artwork validator OK")

print("\nAll static checks PASSED")
