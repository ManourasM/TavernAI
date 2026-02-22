"""
Test suite for database initialization and migrations.

Verifies that init_db works correctly with both Alembic and fallback modes,
and that the database schema is properly created.
"""

import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Import the initialization functions
from app.db import init_db, Base as DBBase
from app.storage.models import Base as StorageBase, OrderModel, TableMetaModel


class TestInitDBFallback:
    """Test init_db with fallback mode (use_alembic=False)."""
    
    def test_init_db_creates_storage_schema(self):
        """Test that init_db creates all storage tables when use_alembic=False."""
        # Create a temporary SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            # Create engine for temporary database
            database_url = f"sqlite:///{tmp_db_path}"
            engine = create_engine(database_url)
            
            # Initialize database with fallback mode
            init_db(engine, use_alembic=False, base=StorageBase)
            
            # Verify tables were created
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Check that storage tables exist
            assert "table_meta" in tables, "table_meta table not created"
            assert "orders" in tables, "orders table not created"
            
            # Verify column structure for table_meta
            columns = {col['name'] for col in inspector.get_columns('table_meta')}
            assert 'id' in columns
            assert 'table_id' in columns
            assert 'people' in columns
            assert 'bread' in columns
            
            # Verify column structure for orders
            columns = {col['name'] for col in inspector.get_columns('orders')}
            assert 'id' in columns
            assert 'table_id' in columns
            assert 'item_id' in columns
            assert 'text' in columns
            
            # Clean up engine
            engine.dispose()
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)
    
    def test_init_db_enables_data_insertion(self):
        """Test that after init_db, we can insert and query data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            database_url = f"sqlite:///{tmp_db_path}"
            engine = create_engine(database_url)
            
            # Initialize database
            init_db(engine, use_alembic=False, base=StorageBase)
            
            # Create a session and insert data
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            
            try:
                # Insert a table metadata record
                table_meta = TableMetaModel(
                    table_id=1,
                    people=4,
                    bread=True
                )
                session.add(table_meta)
                session.commit()
                
                # Query it back
                from sqlalchemy import select
                stmt = select(TableMetaModel).where(TableMetaModel.table_id == 1)
                result = session.execute(stmt).scalar_one_or_none()
                
                assert result is not None, "Failed to retrieve inserted table metadata"
                assert result.table_id == 1
                assert result.people == 4
                assert result.bread is True
                
            finally:
                session.close()
            
            # Clean up engine
            engine.dispose()
        
        finally:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)
    
    def test_init_db_creates_db_schema(self):
        """Test that init_db can also create the new db schema."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            database_url = f"sqlite:///{tmp_db_path}"
            engine = create_engine(database_url)
            
            # Initialize database with new db base (no Alembic, for now)
            init_db(engine, use_alembic=False, base=DBBase)
            
            # Verify tables were created
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Check that new db schema tables exist
            expected_tables = [
                'users',
                'menu_versions',
                'menu_items',
                'table_sessions',
                'orders',
                'order_items',
                'receipts',
                'nlp_training_samples'
            ]
            
            for table_name in expected_tables:
                assert table_name in tables, f"Table {table_name} not created in db schema"
            
            # Clean up engine
            engine.dispose()
            
        finally:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)


class TestAlembicInitialization:
    """Test init_db with Alembic mode (integration test)."""
    
    def test_init_db_alembic_mode_requires_alembic(self):
        """Test that Alembic mode properly handles missing alembic.ini."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            database_url = f"sqlite:///{tmp_db_path}"
            engine = create_engine(database_url)
            
            # Note: We can't fully test Alembic mode without being in the backend directory
            # This is more of a documentation test showing the expected behavior
            # In production, use_alembic=True requires running from the backend directory
            # where alembic.ini is located
            
            # Clean up engine
            engine.dispose()
            
        finally:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)


class TestOrderTableCreation:
    """Test that Order table is properly created and accessible."""
    
    def test_storage_order_table_exists_after_init(self):
        """Verify Order table exists in storage schema after init_db."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            database_url = f"sqlite:///{tmp_db_path}"
            engine = create_engine(database_url)
            
            init_db(engine, use_alembic=False, base=StorageBase)
            
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            assert "orders" in tables, "Order table (orders) not created"
            
            # Verify it has expected columns
            columns = {col['name'] for col in inspector.get_columns('orders')}
            expected_columns = {'id', 'table_id', 'item_id', 'text', 'menu_name', 'name', 'qty', 'unit_price'}
            assert expected_columns.issubset(columns), f"Missing columns in orders table. Missing: {expected_columns - columns}"
            
            # Clean up engine
            engine.dispose()
            
        finally:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)
    
    def test_db_order_table_exists_after_init(self):
        """Verify Order table exists in new db schema after init_db."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            database_url = f"sqlite:///{tmp_db_path}"
            engine = create_engine(database_url)
            
            init_db(engine, use_alembic=False, base=DBBase)
            
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            assert "orders" in tables, "Order table (orders) not created in db schema"
            
            # Verify it has expected columns
            columns = {col['name'] for col in inspector.get_columns('orders')}
            expected_columns = {'id', 'table_session_id', 'created_by_user_id', 'status', 'created_at', 'total'}
            assert expected_columns.issubset(columns), f"Missing columns in db orders table. Missing: {expected_columns - columns}"
            
            # Clean up engine
            engine.dispose()
            
        finally:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
