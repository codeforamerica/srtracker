# Copyright (C) 2012, Code for America
# This is open source software, released under a standard 3-clause
# BSD-style license; see the file LICENSE for details.

import uuid
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Sequence

Base = declarative_base()

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id      = Column(Integer, Sequence('subscription_id_seq'), primary_key=True)
    sr_id   = Column(String, index=True)
    method  = Column(String)
    contact = Column(String)
    key     = Column(String, index=True)
    
    def __init__(self, **kwargs):
        # if we aren't being initialized with a unique key, create one
        if 'key' not in kwargs:
            self.key = self.generate_uuid()
            
        super(Subscription, self).__init__(**kwargs)
    
    def generate_uuid(self):
        '''Generate a unique key for this subscription.'''
        return str(uuid.uuid4()).replace('-', '')


class TokenSubscription(Base):
    __tablename__ = 'tokensubscriptions'
    
    id      = Column(Integer, Sequence('tokensubscription_id_seq'), primary_key=True)
    token   = Column(String, index=True)
    method  = Column(String)
    contact = Column(String)


class UpdateInfoItem(Base):
    __tablename__ = 'updateinfo'
    
    key   = Column(String, primary_key=True)
    value = Column(String)
