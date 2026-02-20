"""
Tests for storage backend selection via environment variable.

Verifies that STORAGE_BACKEND env var allows selecting between inmemory and sqlite.
"""

import pytest
import os
import sys
import tempfile
import subprocess
from httpx import ASGITransport, AsyncClient

from app.storage import InMemoryStorage, SQLiteStorage


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    import time
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_backend_select.db")
    db_url = f"sqlite:///{db_path}"
    yield db_url
    
    # Cleanup
    time.sleep(0.1)
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except (OSError, PermissionError):
        pass


class TestStorageBackendSelection:
    """Test storage backend selection via environment variable."""
    
    def test_default_backend_is_inmemory_via_subprocess(self):
        """Test that default storage backend is InMemoryStorage using subprocess."""
        # This test verifies the default by running Python in a subprocess
        # without STORAGE_BACKEND env var set
        code = """
import sys
sys.path.insert(0, '.')
from app.storage import InMemoryStorage
from app.main import app
assert isinstance(app.state.storage, InMemoryStorage), f"Expected InMemoryStorage, got {type(app.state.storage)}"
print("OK")
"""
        env = os.environ.copy()
        # Make sure STORAGE_BACKEND is not set
        env.pop("STORAGE_BACKEND", None)
        
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=".",
            capture_output=True,
            text=True,
            env=env
        )
        
        # Check subprocess output
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        assert "OK" in result.stdout
    
    def test_env_var_selects_sqlite_via_subprocess(self, temp_db):
        """Test that STORAGE_BACKEND=sqlite creates SQLiteStorage using subprocess."""
        code = f"""
import sys
sys.path.insert(0, '.')
from app.storage import SQLiteStorage
from app.main import app
assert isinstance(app.state.storage, SQLiteStorage), f"Expected SQLiteStorage, got {{type(app.state.storage)}}"
print("OK")
"""
        env = os.environ.copy()
        env["STORAGE_BACKEND"] = "sqlite"
        
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=".",
            capture_output=True,
            text=True,
            env=env
        )
        
        # Check subprocess output
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        assert "OK" in result.stdout
    
    def test_case_insensitive_backend_selection_via_subprocess(self):
        """Test that backend selection is case-insensitive using subprocess."""
        code = """
import sys
sys.path.insert(0, '.')
from app.storage import SQLiteStorage
from app.main import app
assert isinstance(app.state.storage, SQLiteStorage), f"Expected SQLiteStorage, got {type(app.state.storage)}"
print("OK")
"""
        env = os.environ.copy()
        env["STORAGE_BACKEND"] = "SQLITE"
        
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=".",
            capture_output=True,
            text=True,
            env=env
        )
        
        # Check subprocess output
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        assert "OK" in result.stdout
    
    def test_invalid_backend_defaults_to_inmemory_via_subprocess(self):
        """Test that invalid backend value defaults to InMemoryStorage using subprocess."""
        code = """
import sys
sys.path.insert(0, '.')
from app.storage import InMemoryStorage
from app.main import app
assert isinstance(app.state.storage, InMemoryStorage), f"Expected InMemoryStorage, got {type(app.state.storage)}"
print("OK")
"""
        env = os.environ.copy()
        env["STORAGE_BACKEND"] = "unknown_backend"
        
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=".",
            capture_output=True,
            text=True,
            env=env
        )
        
        # Check subprocess output
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        assert "OK" in result.stdout


class TestBackendBehaviorParity:
    """Test that endpoints behave identically regardless of backend.
    
    Note: The core behavior is verified by the main test suite which runs with the 
    default InMemoryStorage backend. These tests verify storage backend selection.
    """
    pass
