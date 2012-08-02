from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Sequence

Base = declarative_base()

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id      = Column(Integer, Sequence('subscription_id_seq'), primary_key=True)
    sr_id   = Column(String, index=True)
    contact = Column(String)
    updated = Column(DateTime)


class UpdateInfoItem(Base):
    __tablename__ = 'updateinfo'
    
    key   = Column(String, primary_key=True)
    value = Column(String)
