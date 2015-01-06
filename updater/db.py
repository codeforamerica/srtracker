# Copyright (C) 2012-2015, Code for America
# This is open source software, released under a standard 3-clause
# BSD-style license; see the file LICENSE for details.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

class DB(object):
    _connection = None
    _engine = None
    Session = None
    
    def __init__(self, connection_string=None):
        self.set_connection(connection_string)
    
    def set_connection(self, connection_string):
        if self._connection:
            raise 'This DB already has a connection string. It cannot be re-set.'
        elif connection_string:
            self._connection = connection_string
            self._engine = create_engine(self._connection)
            self.Session = sessionmaker(bind=self._engine)
    
    def create(self, ModelClass):
        ModelClass.metadata.create_all(bind=self._engine)
    
    @contextmanager
    def session(self):
        instance = self.Session()
        yield instance
        instance.commit()
    
    # alias session() for convenience:
    # now you can do "with db() as s:"
    __call__ = session
