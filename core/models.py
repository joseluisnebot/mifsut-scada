from sqlalchemy import Column, String, JSON, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True)
    template = Column(String, nullable=False)
    protocol = Column(String, nullable=False)
    connection = Column(JSON, nullable=False)
    poll_interval_ms = Column(String, default="1000")
    created_at = Column(DateTime, server_default=func.now())
