import csv
import itertools
import logging
from typing import Any, Dict, List
from io import StringIO


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
            config = {
                "host": os.getenv("DB_HOST"),
                "port": os.getenv("DB_PORT"),
                "database": os.getenv("DB_DATABASE"),
                "user": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD")
            }
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
        # install required packages if user imports this module
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2==2.9.10"])

        self.config = config
        self.conn_pool = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        import psycopg2.pool
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
        from psycopg2.extras import RealDictCursor
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
        from psycopg2 import sql
        query = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name))
        self.execute_query(query)

    def drop_schema(self, schema_name):
        from psycopg2 import sql
        query = sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name))
        self.execute_query(query)

    def fetch_all(self, query, params=None):
        return self.execute_query(query, params)

    def fetch_one(self, query, params=None):
        from psycopg2.extras import RealDictCursor
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
        """
        Create a table in the database with an auto-incrementing ID column.

        Parameters:
        table (str): The name of the table to create.
        columns (dict): A dictionary where keys are column names and values are their data types.

        Example:
            handler.create_table("new_table", {"column1": "TEXT", "column2": "INTEGER"})

        Returns:
        None
        """
        # Add id column as serial primary key if not present
        sequence_field = "id" if ("id" not in columns  and '"id"' not in columns) else "seq_id"
        columns_with_id = {sequence_field: "SERIAL PRIMARY KEY"}
        columns_with_id.update(columns)

        columns_clause = ', '.join([f"{key} {value}" for key, value in columns_with_id.items()])
        query = f"CREATE TABLE {table} ({columns_clause})"
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
            conn.commit()
        finally:
            self.release_connection(conn)

    def drop_table(self, table):
        query = f"DROP TABLE {table}"
        self.execute_query(query)

    def fetch_in_chunks(self, query, params=None, chunk_size=1000):
        from psycopg2.extras import RealDictCursor
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

    def insert_many(self, table: str, data: List[Dict[str, Any]], batch_size: int = 1000):
        """Insert multiple rows of data into a PostgreSQL table.

        This method efficiently inserts multiple records into a specified table using batch processing
        to optimize performance. It automatically handles connection management and provides progress logging.

        Args:
            table (str): Name of the target table to insert data into
            data (List[Dict]): List of dictionaries where each dictionary represents a row of data.
                               Dictionary keys should match column names of the target table.
            batch_size (int, optional): Number of records to insert in each batch. Defaults to 1000.

        Example:
            data = [
            ...     {"name": "John", "age": 30, "city": "New York"},
            ...     {"name": "Jane", "age": 25, "city": "Los Angeles"}
            ... ]
            db.insert_many("employees", data)

        Note:
            - All dictionaries in the data list must have the same keys
            - Column names are automatically escaped with double quotes
            - Progress is logged for every 1000 records processed

        Raises:
            psycopg2.Error: If there's an error during the database operation
        """
        if data:
            columns = ', '.join([f'"{key}"' for key in data[0].keys()])
            values = ', '.join(['%s'] * len(data[0]))
            query = f'INSERT INTO "{table}" ({columns}) VALUES ({values})'
            conn = self.get_connection()
            try:
                with conn.cursor() as cur:
                    for i in range(0, len(data), batch_size):
                        batch = data[i:i + batch_size]
                        params = [tuple(item.values()) for item in batch]
                        cur.executemany(query, params)
                        if i % 1000 == 0:
                            self.logger.info(f"Inserted {i + len(batch)} rows")
                conn.commit()
            finally:
                self.release_connection(conn)

    

    def copy_from_csv(self, table: str, csv_path: str, delimiter: str = ',', columns: List[str] = None) -> int:
        """
        Copies data from a CSV file into a specified PostgreSQL table.

        This method performs a bulk import of CSV data into a PostgreSQL table using the COPY command.
        It handles column mapping, validates column counts, and supports custom column selection.

        Args:
            table (str): Name of the target PostgreSQL table
            csv_path (str): Full path to the CSV file to import
            delimiter (str, optional): CSV delimiter character. Defaults to ','
            columns (List[str], optional): List of column names to import. If None, uses all non-sequence columns. Defaults to None

        Returns:
            int: Number of rows successfully imported

        Raises:
            ValueError: If table not found, column counts mismatch, or other validation errors
            Exception: For any database or file operation errors

        Example:
            db = PostgreSQLHandler(connection_params)
            # Import all columns
            rows = db.copy_from_csv('customers', '/path/to/customers.csv')
            print(f"Imported {rows} rows")
            
            # Import specific columns
            columns = ['first_name', 'last_name', 'email']
            rows = db.copy_from_csv('customers', '/path/to/customers.csv', columns=columns)

        Notes:
            - CSV must have a header row matching table column names
            - Empty values in CSV are treated as NULL
            - Auto-incrementing columns (sequences) are automatically excluded
            - Table and column names are case-insensitive
        """
        rows_imported = 0
        conn = self.get_connection()

        try:
            with conn.cursor() as cur:
                # Modified query to handle case sensitivity and schema
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = LOWER(%s)
                    AND table_schema = CURRENT_SCHEMA()
                    AND (column_default NOT LIKE 'nextval%%' OR column_default IS NULL)
                    ORDER BY ordinal_position
                """, (table.lower(),))

                table_columns = [col[0] for col in cur.fetchall()]
                table_column_count = len(table_columns)

                if table_column_count == 0:
                    raise ValueError(f"No columns found in table '{table}'. Check table name and schema.")

                with open(csv_path, 'r') as f:
                    header = f.readline().strip().split(delimiter)
                    csv_column_count = len(header)

                    if columns:
                        expected_columns = len(columns)
                        if csv_column_count != expected_columns:
                            raise ValueError(
                                f"CSV has {csv_column_count} columns but {expected_columns} were specified"
                            )
                        column_list = f"({','.join(columns)})"
                    else:
                        if csv_column_count != table_column_count:
                            raise ValueError(
                                f"CSV has {csv_column_count} columns but table has {table_column_count} (excluding sequence columns)"
                            )
                        column_list = f"({','.join(table_columns)})"

                    # make sure to add each column name inside double quotes
                    column_list = f"({','.join([f'"{col}"' for col in header])})"

                    # Reset file pointer to start
                    f.seek(0)
        
                    buffer = StringIO()
                    buffer.write(f.read())
                    buffer.seek(0)

                    cur.copy_expert(
                        f"COPY {table} {column_list} FROM STDIN WITH CSV DELIMITER '{delimiter}' NULL '' HEADER",
                        buffer
                    )
                    rows_imported = cur.rowcount

                conn.commit()
                self.logger.info(f"Successfully imported {rows_imported} rows into {table}")
                return rows_imported

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error importing CSV: {str(e)}")
            raise

        finally:
            conn.close()
