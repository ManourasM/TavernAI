"""
SQLAlchemy ORM models for TavernAI persistence.

Defines database schema for orders and table metadata.
Maps to SQLite (or other SQL databases) via SQLAlchemy 2.0.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TableMetaModel(Base):
    """Table metadata: people count, bread preference."""
    
    __tablename__ = "table_meta"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, nullable=False)
    people = Column(Integer, nullable=True)
    bread = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("table_id", name="uq_table_meta_table_id"),
        Index("idx_table_meta_table_id", "table_id"),
    )
    
    def to_dict(self):
        """Convert to dictionary matching storage interface."""
        return {
            "people": self.people,
            "bread": self.bread
        }


class OrderModel(Base):
    """Order item stored in database."""
    
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, nullable=False)
    item_id = Column(String(36), nullable=False)  # UUID string
    text = Column(String, nullable=False)  # Original user text
    menu_name = Column(String, nullable=True)  # Matched menu name
    name = Column(String, nullable=True)  # Parsed name (legacy)
    qty = Column(Float, nullable=True)  # Quantity (can be float for kg/liters)
    unit_price = Column(Float, nullable=True)  # Price per unit
    line_total = Column(Float, nullable=True)  # qty * unit_price
    menu_id = Column(String, nullable=True)  # Menu item ID
    category = Column(String, nullable=False)  # kitchen / grill / drinks
    status = Column(String, default="pending")  # pending / done / cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Composite index for common queries
    __table_args__ = (
        UniqueConstraint("item_id", name="uq_orders_item_id"),
        Index("idx_orders_table_id", "table_id"),
        Index("idx_orders_item_id", "item_id"),
        Index("idx_table_status", "table_id", "status"),
    )
    
    def to_dict(self):
        """Convert to dictionary matching storage interface and items returned by endpoints."""
        return {
            "id": self.item_id,
            "table": self.table_id,
            "text": self.text,
            "menu_name": self.menu_name,
            "name": self.name,
            "qty": self.qty,
            "unit_price": self.unit_price,
            "line_total": self.line_total,
            "menu_id": self.menu_id,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
