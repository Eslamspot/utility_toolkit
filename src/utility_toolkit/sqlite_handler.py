import csv
import gzip
import logging
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Union


from . import log



@log.class_log_decorator(
    exclude=["_insert_chunk", "_read_csv_in_chunks", "_read_txt_in_chunks", "execute_custom_query"])
class DatabaseHandler:
    """
    A class to handle database operations for a SQLite database.

    Attributes:
        connection (sqlite3.Connection): The SQLite connection object.
        cursor (sqlite3.Cursor): The SQLite cursor object.
        db_file_path (Path or str): The path to the SQLite database file.
    """

    def __init__(self, db_name: Path or str, conn=None):
        """
        Initialize the DatabaseHandler with a database name or connection.

        Args:
            db_name (Path or str): The name or path of the SQLite database.
            conn (sqlite3.Connection, optional): An existing SQLite connection. Defaults to None.
        """
        if conn:
            self.connection = conn
        else:
            self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.setup_status_table()
        self.db_file_path = db_name

    def setup_status_table(self):
        """
        Create the status table if it does not exist and insert default status values.
        """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS status (
                status_id INTEGER PRIMARY KEY,
                status_name TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            INSERT OR IGNORE INTO status (status_id, status_name) VALUES
            (1, 'new'),
            (2, 'processing'),
            (3, 'processed'),
            (4, 'failed')
        ''')
        self.connection.commit()

    def create_table(self, table_name: str, columns: List[str]):
        """
        Create a new table with the specified columns.

        Args:
            table_name (str): The name of the table to create.
            columns (List[str]): A list of column names for the table.
        """
        columns_with_types = ', '.join([f"{column} TEXT" for column in columns])
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {columns_with_types},
                status_id INTEGER,
                error_message TEXT,
                FOREIGN KEY (status_id) REFERENCES status (status_id)
            )
        ''')
        self.connection.commit()

    def _insert_chunk(self, table_name: str, columns: List[str], chunk: List[Dict[str, str]]):
        """
        Insert a chunk of data into the specified table.

        Args:
            table_name (str): The name of the table to insert data into.
            columns (List[str]): A list of column names for the table.
            chunk (List[Dict[str, str]]): A list of dictionaries representing the data to insert.
        """
        question_marks = ', '.join(['?'] * len(columns))
        values = [tuple(row.values()) for row in chunk]
        query = f'INSERT INTO {table_name} ({", ".join(columns)}, status_id) VALUES ({question_marks}, 1)'
        self.cursor.executemany(query, values)

    def _read_csv_in_chunks(self, file_path: str, chunk_size: int):
        """
        Read a CSV file in chunks.

        Args:
            file_path (str): The path to the CSV file.
            chunk_size (int): The number of rows per chunk.

        Yields:
            List[Dict[str, str]]: A chunk of data from the CSV file.
        """
        open_file = gzip.open if file_path.lower().endswith('.gz') else open
        with open_file(file_path, 'rt', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            chunk = []
            for row in reader:
                chunk.append(row)
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk

    def _read_txt_in_chunks(self, file_path: str, delimiter: str, chunk_size: int):
        """
        Read a text file in chunks.

        Args:
            file_path (str): The path to the text file.
            delimiter (str): The delimiter used to split the text file.
            chunk_size (int): The number of lines per chunk.

        Yields:
            List[List[str]]: A chunk of data from the text file.
        """
        open_file = gzip.open if file_path.lower().endswith('.gz') else open
        with open_file(file_path, 'rt', encoding='utf-8') as file:
            chunk = []
            for line in file:
                columns = line.strip().split(delimiter)
                if columns:
                    chunk.append(columns)
                    if len(chunk) >= chunk_size:
                        yield chunk
                        chunk = []
            if chunk:
                yield chunk

    def import_data_from_csv(self, table_name: str, file_path: str, chunk_size: int = 1000,
                             columns_rename: dict = None):
        """
        Import data from a CSV file into the specified table.

        Args:
            table_name (str): The name of the table to import data into.
            file_path (str): The path to the CSV file.
            chunk_size (int, optional): The number of rows per chunk. Defaults to 1000.
            columns_rename (dict, optional): A dictionary to rename columns. Defaults to None.
        """
        for chunk in self._read_csv_in_chunks(file_path, chunk_size):
            columns = chunk[0].keys()
            if columns_rename:
                columns = [columns_rename.get(column, column) for column in columns]
            self._insert_chunk(table_name, columns, chunk)
        logging.info(f"Database Location: {self.db_file_path}")
        logging.info(f"Data imported from {file_path}")
        logging.info(f"Data imported to {table_name}")
        query = f"SELECT COUNT(*) FROM {table_name}"
        logging.info(f"There are {self.cursor.execute(query).fetchone()[0]} records in {table_name}")
        self.connection.commit()

    def import_data_from_txt(self, table_name: str, file_path: str, delimiter: str, chunk_size: int = 1000):
        """
        Import data from a text file into the specified table.

        Args:
            table_name (str): The name of the table to import data into.
            file_path (str): The path to the text file.
            delimiter (str): The delimiter used to split the text file.
            chunk_size (int, optional): The number of lines per chunk. Defaults to 1000.
        """
        for chunk in self._read_txt_in_chunks(file_path, delimiter, chunk_size):
            # Assuming each line is a single column of data called 'data'.
            data_chunk = [{'s3_file_path': column[0]} for column in chunk]
            self._insert_chunk(table_name, ['s3_file_path'], data_chunk)
        try:
            self.connection.commit()
        except sqlite3.OperationalError as e:
            logging.error(f"An error occurred: {e}")

    def add_record(self, table_name: str, data: Dict[str, str]):
        """
        Add a record to the specified table.

        Args:
            table_name (str): The name of the table to add a record to.
            data (Dict[str, str]): A dictionary representing the data to add.
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())

        self.cursor.execute(f'''
            INSERT INTO {table_name} ({columns}, status_id)
            VALUES ({placeholders}, 1)
        ''', values)
        self.connection.commit()

    def read_records(self, table_name: str, status: str = None):
        """
        Read records from the specified table.

        Args:
            table_name (str): The name of the table to read records from.
            status (str, optional): The status to filter records by. Defaults to None.

        Returns:
            List[tuple]: A list of records from the table.
        """
        if status:
            self.cursor.execute(f'''
                SELECT * FROM {table_name} 
                INNER JOIN status ON {table_name}.status_id = status.status_id
                WHERE status.status_name = ?
            ''', (status,))
        else:
            self.cursor.execute(f'SELECT * FROM {table_name}')
        return self.cursor.fetchall()

    def update_record(self, table_name: str, record_id: Union[int, str, List[Union[int, str]]], status: str,
                      error_message: str = ''):
        """
        Update the status and error message of a record in the specified table.

        Args:
            table_name (str): The name of the table to update a record in.
            record_id (Union[int, str, List[Union[int, str]]]): The ID(s) of the record(s) to update.
            status (str): The new status of the record.
            error_message (str, optional): The error message to set. Defaults to ''.
        """
        if isinstance(record_id, list):
            record_id = ','.join([str(id) for id in record_id])
            query = f'''
                UPDATE {table_name}
                SET status_id = (SELECT status_id FROM status WHERE status_name = ?),
                    error_message = ?
                WHERE id IN ({record_id})
            '''
        else:
            query = f'''
                UPDATE {table_name}
                SET status_id = (SELECT status_id FROM status WHERE status_name = ?),
                    error_message = ?
                WHERE id = ?
            '''
        params = (status, error_message, record_id) if not isinstance(record_id, list) else (status, error_message)
        self.cursor.execute(query, params)
        self.connection.commit()

    def execute_custom_query(self, query: str, params: Union[tuple, list] = ()) -> object:
        """
        Execute a custom SQL query.

        Args:
            query (str): The SQL query to execute.
            params (Union[tuple, list], optional): The parameters for the SQL query. Defaults to ().

        Returns:
            object: The result of the query if it is a SELECT query, otherwise the number of affected rows.
        """
        self.cursor.execute(query, params)
        if query.strip().upper().startswith("SELECT"):
            return self.cursor.fetchall()
        else:
            self.connection.commit()
            return self.cursor.rowcount  # Number of affected rows

    def delete_record(self, table_name: str, record_id: int):
        """
        Delete a record from the specified table.

        Args:
            table_name (str): The name of the table to delete a record from.
            record_id (int): The ID of the record to delete.
        """
        self.cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (record_id,))
        self.connection.commit()

    def close(self):
        """
        Close the database connection.
        """
        self.connection.close()


if __name__ == "__main__":
    # TODO: We need to user this part if we want to get source from csv file
    # load data from csv file
    project_name = os.getenv('PROJECT_NAME').replace(" ", "_").replace("-", "_")
    # check if project start with number rais error
    assert not project_name[0].isdigit(), "Project name should start with letter"
    csv_file_path = Path("./data/s3_path.csv")
    columns_rename = {'source_path': 's3_file_path', 'destination_path': 'new_s3_path'}
    sqlite_path = Path(os.getenv('RESULT_FOLDER_PATH')) / f'{project_name}.db'
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    db_handler = DatabaseHandler(sqlite_path)
    db_handler.create_table(table_name=project_name, columns=['s3_file_path', 'new_s3_path'])
    db_handler.import_data_from_csv(table_name=project_name, file_path=str(csv_file_path),
                                    columns_rename=columns_rename)
