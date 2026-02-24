"""
Canonical relational database models for TavernAI.

These models represent the full relational schema and are used by Alembic
for migration generation. They are kept separate from storage adapters.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """System users: staff, waiters, admin."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    roles = Column(JSON, default=[], nullable=False)  # e.g., ["waiter", "kitchen"]
    pin = Column(String(6), nullable=True)  # Optional PIN for quick login
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    menu_versions = relationship("MenuVersion", back_populates="created_by")
    table_sessions = relationship("TableSession", back_populates="waiter")
    orders = relationship("Order", back_populates="created_by_user")
    nlp_corrections = relationship("NLPTrainingSample", back_populates="corrected_by")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class MenuVersion(Base):
    """Version history for menus."""
    
    __tablename__ = "menu_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    json_blob = Column(JSON, nullable=False)  # Full menu structure snapshot
    
    # Composite index for common queries
    __table_args__ = (
        Index("idx_menu_versions_created", "created_at"),
        Index("idx_menu_versions_user", "created_by_user_id"),
    )
    
    # Relationships
    created_by = relationship("User", back_populates="menu_versions")
    items = relationship("MenuItem", back_populates="menu_version", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MenuVersion(id={self.id}, created_at={self.created_at})>"


class MenuItem(Base):
    """Items in a specific menu version."""
    
    __tablename__ = "menu_items"
    
    id = Column(Integer, primary_key=True, index=True)
    menu_version_id = Column(Integer, ForeignKey("menu_versions.id"), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # ID from external menu source
    name = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False)  # Stored as cents (int) for accuracy
    category = Column(String(100), nullable=False, index=True)  # kitchen, grill, drinks, etc.
    station = Column(String(100), nullable=False)  # Destination station
    extra_data = Column(JSON, nullable=True)  # Extra data: allergens, prep_time, etc.
    is_active = Column(Boolean, default=True, nullable=False)  # Soft-delete flag
    
    __table_args__ = (
        Index("idx_menu_items_category", "category"),
        Index("idx_menu_items_station", "station"),
    )
    
    # Relationships
    menu_version = relationship("MenuVersion", back_populates="items")
    order_items = relationship("OrderItem", back_populates="menu_item")
    # Note: NLPTrainingSample has two FK to MenuItem (predicted and corrected)
    # so we cannot have a simple back_populates. Left as forward-only relationship in NLPTrainingSample.
    
    def __repr__(self):
        return f"<MenuItem(id={self.id}, name={self.name}, price={self.price})>"


class TableSession(Base):
    """Session for a restaurant table (open/close lifecycle)."""
    
    __tablename__ = "table_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    table_label = Column(String(50), nullable=False)  # "Table 1", "Bar 5", etc.
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    closed_at = Column(DateTime, nullable=True)
    waiter_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    __table_args__ = (
        Index("idx_table_sessions_opened", "opened_at"),
        Index("idx_table_sessions_waiter", "waiter_user_id"),
    )
    
    # Relationships
    waiter = relationship("User", back_populates="table_sessions")
    orders = relationship("Order", back_populates="table_session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TableSession(id={self.id}, table={self.table_label}, opened={self.opened_at})>"


class Order(Base):
    """Restaurant order for a table."""
    
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    table_session_id = Column(Integer, ForeignKey("table_sessions.id"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, confirmed, ready, served, closed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    total = Column(Integer, nullable=True)  # Total in cents
    
    __table_args__ = (
        Index("idx_orders_table_session", "table_session_id"),
        Index("idx_orders_created_by", "created_by_user_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_created", "created_at"),
    )
    
    # Relationships
    table_session = relationship("TableSession", back_populates="orders")
    created_by_user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id={self.id}, table_session_id={self.table_session_id}, status={self.status})>"


class OrderItem(Base):
    """Individual item in an order."""
    
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True, index=True)  # Nullable for free-text items
    name = Column(String(255), nullable=False)  # Item name or free-text
    text = Column(String(500), nullable=True)  # Original user input text (e.g., "2κ παιδακια")
    qty = Column(Integer, nullable=False, default=1)
    unit = Column(String(50), nullable=True)  # kg, liter, pcs, etc.
    unit_price = Column(Integer, nullable=False)  # Price in cents
    line_total = Column(Integer, nullable=False)  # qty * unit_price
    category = Column(String(50), nullable=True)  # kitchen, grill, drinks (for routing)
    status = Column(String(50), default="pending", nullable=False)  # pending, preparing, ready, served, cancelled
    
    __table_args__ = (
        Index("idx_order_items_order", "order_id"),
        Index("idx_order_items_menu_item", "menu_item_id"),
        Index("idx_order_items_status", "status"),
    )
    
    # Relationships
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, name={self.name}, qty={self.qty}, status={self.status})>"


class Receipt(Base):
    """Receipt/invoice for an order."""
    
    __tablename__ = "receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    printed_at = Column(DateTime, nullable=True)
    content = Column(Text, nullable=False)  # Full receipt text/HTML
    
    # Relationships
    order = relationship("Order", back_populates="receipts")
    
    def __repr__(self):
        return f"<Receipt(id={self.id}, order_id={self.order_id})>"


class NLPTrainingSample(Base):
    """Training data for NLP order classification."""
    
    __tablename__ = "nlp_training_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(String(500), nullable=False)
    predicted_menu_item_id = Column(String(255), nullable=True, index=True)
    corrected_menu_item_id = Column(String(255), nullable=True)
    corrected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_nlp_samples_created", "created_at"),
        Index("idx_nlp_samples_corrected_by", "corrected_by_user_id"),
    )
    
    # Relationships
    corrected_by = relationship("User", back_populates="nlp_corrections")
    
    def __repr__(self):
        return f"<NLPTrainingSample(id={self.id}, text={self.raw_text[:50]}...)>"
