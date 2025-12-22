"""
Schema Generator - Single Source of Truth

Generates database schemas for both DuckDB and PostgreSQL from SQLAlchemy models.
This eliminates the need to maintain separate schema.py and postgres_schema.py files.
"""

import logging
from typing import Optional
from sqlalchemy import inspect
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql, sqlite

from .models import Base

logger = logging.getLogger(__name__)

# Module-level variable for schema creation (to avoid circular imports)
_schema_db = None


def set_schema_db(db):
    """Set the database connection for schema creation (used by factory during init)."""
    global _schema_db
    _schema_db = db


def clear_schema_db():
    """Clear the schema db after initialization is complete."""
    global _schema_db
    _schema_db = None


def get_db_connection():
    """Get database connection, avoiding circular imports during initialization."""
    global _schema_db
    if _schema_db is not None:
        return _schema_db
    from .factory import get_db_connection as factory_get_db
    return factory_get_db()


def _sqlalchemy_type_to_duckdb(column):
    """Convert SQLAlchemy column type to DuckDB type string."""
    col_type = column.type
    type_name = col_type.__class__.__name__.upper()
    
    # Map SQLAlchemy types to DuckDB types
    type_mapping = {
        'VARCHAR': 'VARCHAR',
        'STRING': 'VARCHAR',
        'TEXT': 'TEXT',
        'INTEGER': 'INTEGER',
        'BIGINTEGER': 'BIGINT',
        'FLOAT': 'DOUBLE',
        'DOUBLE': 'DOUBLE',
        'BOOLEAN': 'BOOLEAN',
        'DATE': 'DATE',
        'DATETIME': 'TIMESTAMP',
        'TIMESTAMP': 'TIMESTAMP',
        'JSON': 'JSON',
    }
    
    return type_mapping.get(type_name, 'VARCHAR')


def _sqlalchemy_type_to_postgres(column):
    """Convert SQLAlchemy column type to PostgreSQL type string."""
    col_type = column.type
    type_name = col_type.__class__.__name__.upper()
    
    # Map SQLAlchemy types to PostgreSQL types
    type_mapping = {
        'VARCHAR': 'VARCHAR(255)',
        'STRING': 'VARCHAR(255)',
        'TEXT': 'TEXT',
        'INTEGER': 'INTEGER',
        'BIGINTEGER': 'BIGINT',
        'FLOAT': 'DOUBLE PRECISION',
        'DOUBLE': 'DOUBLE PRECISION',
        'BOOLEAN': 'BOOLEAN',
        'DATE': 'DATE',
        'DATETIME': 'TIMESTAMP',
        'TIMESTAMP': 'TIMESTAMP',
        'JSON': 'JSONB',
    }
    
    return type_mapping.get(type_name, 'VARCHAR(255)')


def generate_create_table_duckdb(model_class):
    """Generate DuckDB CREATE TABLE statement from SQLAlchemy model."""
    table_name = model_class.__tablename__
    columns = []
    primary_keys = []
    
    # Get columns from the model
    mapper = inspect(model_class)
    for column in mapper.columns:
        col_def = f"{column.name} {_sqlalchemy_type_to_duckdb(column)}"
        
        if not column.nullable:
            col_def += " NOT NULL"
        
        if column.default is not None and hasattr(column.default, 'arg'):
            if column.default.arg == 'CURRENT_TIMESTAMP' or str(column.default.arg) == 'now()':
                col_def += " DEFAULT CURRENT_TIMESTAMP"
        
        columns.append(col_def)
        
        # Track primary key columns
        if column.primary_key:
            primary_keys.append(column.name)
    
    # Add primary key constraint
    if primary_keys:
        pk_constraint = f"PRIMARY KEY ({', '.join(primary_keys)})"
        columns.append(pk_constraint)
    
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    "
    sql += ",\n    ".join(columns)
    sql += "\n)"
    
    return sql


def generate_create_table_postgres(model_class):
    """Generate PostgreSQL CREATE TABLE statement from SQLAlchemy model."""
    table_name = model_class.__tablename__
    columns = []
    primary_keys = []
    
    # Get columns from the model
    mapper = inspect(model_class)
    for column in mapper.columns:
        col_def = f"{column.name} {_sqlalchemy_type_to_postgres(column)}"
        
        if not column.nullable:
            col_def += " NOT NULL"
        
        if column.default is not None and hasattr(column.default, 'arg'):
            if column.default.arg == 'CURRENT_TIMESTAMP' or str(column.default.arg) == 'now()':
                col_def += " DEFAULT CURRENT_TIMESTAMP"
        
        columns.append(col_def)
        
        # Track primary key columns
        if column.primary_key:
            primary_keys.append(column.name)
    
    # Add primary key constraint
    if primary_keys:
        pk_constraint = f"PRIMARY KEY ({', '.join(primary_keys)})"
        columns.append(pk_constraint)
    
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    "
    sql += ",\n    ".join(columns)
    sql += "\n)"
    
    return sql


def generate_indexes(model_class, dialect='duckdb'):
    """Generate CREATE INDEX statements from SQLAlchemy model."""
    indexes = []
    
    if hasattr(model_class, '__table_args__'):
        table_args = model_class.__table_args__
        if isinstance(table_args, tuple):
            for arg in table_args:
                if hasattr(arg, '__class__') and arg.__class__.__name__ == 'Index':
                    idx_name = arg.name
                    idx_columns = ', '.join([col.name for col in arg.columns])
                    sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {model_class.__tablename__}({idx_columns})"
                    indexes.append(sql)
    
    return indexes


def create_all_tables_duckdb():
    """Create all tables in DuckDB from SQLAlchemy models."""
    db = get_db_connection()
    logger.info("Creating DuckDB schema from SQLAlchemy models...")
    
    # Get all model classes
    models = [
        model for model in Base.__subclasses__()
    ]
    
    for model in models:
        try:
            # Create table
            create_sql = generate_create_table_duckdb(model)
            db.execute(create_sql)
            logger.info(f"[OK] Created table: {model.__tablename__}")
            
            # Create indexes
            for index_sql in generate_indexes(model, 'duckdb'):
                db.execute(index_sql)
                logger.info(f"  - Created index: {index_sql.split('IF NOT EXISTS ')[1].split(' ON')[0]}")
        
        except Exception as e:
            logger.error(f"Error creating table {model.__tablename__}: {e}")
            raise
    
    logger.info("DuckDB schema created successfully from SQLAlchemy models!")


def create_all_tables_postgres():
    """Create all tables in PostgreSQL from SQLAlchemy models."""
    db = get_db_connection()
    logger.info("Creating PostgreSQL schema from SQLAlchemy models...")
    
    # Get all model classes
    models = [
        model for model in Base.__subclasses__()
    ]
    
    for model in models:
        try:
            # Create table
            create_sql = generate_create_table_postgres(model)
            db.execute(create_sql)
            logger.info(f"[OK] Created table: {model.__tablename__}")
            
            # Create indexes
            for index_sql in generate_indexes(model, 'postgres'):
                db.execute(index_sql)
                logger.info(f"  - Created index: {index_sql.split('IF NOT EXISTS ')[1].split(' ON')[0]}")
        
        except Exception as e:
            logger.error(f"Error creating table {model.__tablename__}: {e}")
            raise
    
    logger.info("PostgreSQL schema created successfully from SQLAlchemy models!")


def create_all_tables():
    """
    Create all tables using the appropriate dialect.
    
    This is the main entry point called by the database factory.
    Automatically detects whether to use DuckDB or PostgreSQL syntax.
    """
    import os
    
    backend_type = os.getenv('DATABASE_BACKEND', 'duckdb').lower()
    
    if backend_type == 'postgresql':
        create_all_tables_postgres()
    else:
        create_all_tables_duckdb()
