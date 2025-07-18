from google.cloud import ndb
import os
import pickle
import json
from datetime import datetime

# In-memory database for local development
class LocalDB:
    def __init__(self):
        self.data = {}
        self.load_from_disk()
    
    def load_from_disk(self):
        try:
            if os.path.exists('local_db.pickle'):
                with open('local_db.pickle', 'rb') as f:
                    self.data = pickle.load(f)
        except Exception as e:
            print(f"Error loading database: {e}")
            self.data = {}
    
    def save_to_disk(self):
        try:
            with open('local_db.pickle', 'wb') as f:
                pickle.dump(self.data, f)
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def put(self, entity):
        kind = entity.__class__.__name__
        if kind not in self.data:
            self.data[kind] = {}
        
        # Generate a unique ID if needed
        if not hasattr(entity, 'id') or entity.id is None:
            entity.id = len(self.data[kind]) + 1
        
        # Store the entity
        self.data[kind][entity.id] = entity
        self.save_to_disk()
        return entity.id
    
    def get(self, kind, entity_id):
        if kind in self.data and entity_id in self.data[kind]:
            return self.data[kind][entity_id]
        return None
    
    def delete(self, kind, entity_id):
        if kind in self.data and entity_id in self.data[kind]:
            del self.data[kind][entity_id]
            self.save_to_disk()
            return True
        return False
    
    def query(self, kind, filters=None):
        results = []
        if kind in self.data:
            for entity_id, entity in self.data[kind].items():
                if filters is None:
                    results.append(entity)
                else:
                    # Apply filters
                    match = True
                    for field, op, value in filters:
                        if not hasattr(entity, field):
                            match = False
                            break
                        
                        entity_value = getattr(entity, field)
                        
                        if op == '==':
                            if entity_value != value:
                                match = False
                                break
                        elif op == '>':
                            if entity_value <= value:
                                match = False
                                break
                        elif op == '<':
                            if entity_value >= value:
                                match = False
                                break
                        elif op == '>=':
                            if entity_value < value:
                                match = False
                                break
                        elif op == '<=':
                            if entity_value > value:
                                match = False
                                break
                    
                    if match:
                        results.append(entity)
        
        return results

# Global database instance
local_db = LocalDB()

# Mock context manager for NDB
class MockContext:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Create a mock NDB client
class MockClient:
    def context(self):
        return MockContext()

# Instantiate the mock client
client = MockClient()

# Override NDB model methods to use our local database
def monkey_patch_ndb():
    original_put = ndb.Model.put
    original_query = ndb.query.Query
    
    def mock_put(self, *args, **kwargs):
        return local_db.put(self)
    
    def mock_query(self, *args, **kwargs):
        # Simplified mock query implementation
        kind = self._kind
        filters = []
        
        # Build filters based on query parameters
        if hasattr(self, '_filters'):
            for filter_spec in self._filters:
                property_name = filter_spec.name
                op = '=='  # Default operation
                value = filter_spec.value
                filters.append((property_name, op, value))
        
        results = local_db.query(kind, filters)
        return results
    
    ndb.Model.put = mock_put
    ndb.query.Query._execute_query = mock_query