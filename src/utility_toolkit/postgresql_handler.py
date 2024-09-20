import csv
import itertools
import logging

import psycopg2
from psycopg2 import pool
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from . import log


@log.class_log_decorator(exclude=["fetch_all", "execute_query"])
class PostgreSQLHandler:
    """
    A class used to interact with a PostgreSQL database.

    Attributes
    ----------
    config : dict
        A dictionary containing the connection parameters for the PostgreSQL database.
    conn : psycopg2.extensions.connection
        The connection object to the PostgreSQL database.

    Methods
    -------
    connect():
        Establishes a connection to the PostgreSQL database.
        Example:
            handler = PostgreSQLHandler(config)
            handler.connect()

    disconnect():
        Closes the connection to the PostgreSQL database.
        Example:
            handler.disconnect()

    execute_query(query: str, params: Optional[dict] = None):
        Executes a given SQL query and returns the result.
        Example:
            result = handler.execute_query("SELECT * FROM table_name WHERE condition")

    fetch_all(query: str, params: Optional[dict] = None):
        Fetches all rows from the result of a query.
        Example:
            rows = handler.fetch_all("SELECT * FROM table_name")

    fetch_one(query: str, params: Optional[dict] = None):
        Fetches one row from the result of a query.
        Example:
            row = handler.fetch_one("SELECT * FROM table_name WHERE condition")

    insert(table: str, data: dict):
        Inserts a row into a table.
        Example:
            handler.insert("table_name", {"column1": "value1", "column2": "value2"})

    update(table: str, data: dict, condition: str):
        Updates a row in a table.
        Example:
            handler.update("table_name", {"column1": "new_value"}, "column2 = 'value2'")

    delete(table: str, condition: str):
        Deletes a row from a table.
        Example:
            handler.delete("table_name", "column1 = 'value1'")

    create_table(table: str, columns: dict):
        Creates a new table.
        Example:
            handler.create_table("new_table", {"column1": "type1", "column2": "type2"})

    drop_table(table: str):
        Drops a table.
        Example:
            handler.drop_table("table_name")

    fetch_in_chunks(query: str, params: Optional[dict] = None, chunk_size: int = 1000):
        Fetches large result sets in chunks to avoid loading all rows into memory at once.
        Example:
            for chunk in handler.fetch_in_chunks("SELECT * FROM table_name"):
                process(chunk)

    upload_csv(table: str, csv_path: str, delimiter: str = ',', chunk_size: int = 1000):
        Uploads data from a CSV file to a table.
        Example:
            handler.upload_csv("table_name", "/path/to/file.csv")

    insert_many(table: str, data: List[dict]):
        Inserts multiple rows into a table.
        Example:
            handler.insert_many("table_name", [{"column1": "value1", "column2": "value2"}, {"column1": "value3", "column2": "value4"}])
    """

    def __init__(self, config):
        self.config = config
        self.conn_pool = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        self.conn_pool = psycopg2.pool.SimpleConnectionPool(1, 200, **self.config)

    def get_connection(self):
        if self.conn_pool:
            return self.conn_pool.getconn()

    def release_connection(self, conn):
        if self.conn_pool:
            self.conn_pool.putconn(conn)

    def disconnect(self):
        if self.conn_pool:
            self.conn_pool.closeall()

    def execute_query(self, query, params=None):
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if cur.description:  # Check if the cursor returned data
                result = cur.fetchall()
            else:
                result = None
        self.release_connection(conn)
        return result

    def begin_transaction(self):
        conn = self.get_connection()
        conn.autocommit = False
        return conn

    def commit_transaction(self, conn):
        conn.commit()
        self.release_connection(conn)

    def rollback_transaction(self, conn):
        conn.rollback()
        self.release_connection(conn)

    def create_schema(self, schema_name):
        query = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name))
        self.execute_query(query)

    def drop_schema(self, schema_name):
        query = sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name))
        self.execute_query(query)

    def fetch_all(self, query, params=None):
        return self.execute_query(query, params)

    def fetch_one(self, query, params=None):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def insert(self, table, data):
        columns = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({values})"
        self.execute_query(query, list(data.values()))

    def update(self, table, data, condition):
        set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        self.execute_query(query, list(data.values()))

    def delete(self, table, condition):
        query = f"DELETE FROM {table} WHERE {condition}"
        self.execute_query(query)

    def create_table(self, table, columns):
        columns_clause = ', '.join([f"{key} {value}" for key, value in columns.items()])
        query = f"CREATE TABLE {table} ({columns_clause})"
        self.execute_query(query)

    def drop_table(self, table):
        query = f"DROP TABLE {table}"
        self.execute_query(query)

    def fetch_in_chunks(self, query, params=None, chunk_size=1000):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            while True:
                rows = cur.fetchmany(chunk_size)
                if not rows:
                    break
                yield rows

    def upload_csv(self, table, csv_path, delimiter=',', chunk_size=1000):
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            while True:
                chunk = list(itertools.islice(reader, chunk_size))
                if not chunk:
                    break
                self.insert_many(table, chunk)

    def insert_many(self, table, data):
        if data:
            columns = ', '.join(data[0].keys())
            values = ', '.join(['%s'] * len(data[0]))
            query = f"INSERT INTO {table} ({columns}) VALUES ({values})"
            params = [tuple(item.values()) for item in data]
            with self.conn.cursor() as cur:
                cur.executemany(query, params)


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv(".env")

    query_unique_id = """
    select *
    from "qcpr_arf_AU"."MultimediaHfsLineNumber" a
    where "MultimediaHfsID"::int = 24599;
    """

    db_config = {
        'dbname': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432)
    }

    db = PostgreSQLHandler(db_config)
    db.connect()
    payload = db.fetch_all(query_unique_id)
    log.logging.info(f"payload count: {len(payload)}")
    db.disconnect()

    # connect to the database using pands
    import pandas as pd

    # Create a new instance of the PostgresSQL handler
    db = PostgreSQLHandler(db_config)

    # Connect to the database
    db.connect()

    query = f""" SELECT "SourceS3FileName", "DestinationFileName" FROM dbo.all_data_0365;"""

    df = pd.read_sql(query, db.get_connection())

    # Release the connection
    db.release_connection(db.get_connection())

    # better way to connect to the database
    # pipenv install sqlalchemy
    from sqlalchemy import create_engine

    # Create a new instance of the PostgresSQL handler
    db = PostgreSQLHandler(db_config)

    # Connect to the database
    db.connect()

    # Create an SQLAlchemy engine using the connection
    engine = create_engine(db.get_connection().dsn)

    query = f""" SELECT "SourceS3FileName", "DestinationFileName" FROM dbo.all_data_0365;"""

    df = pd.read_sql(query, engine)

    # Release the connection
    db.release_connection(db.get_connection())
