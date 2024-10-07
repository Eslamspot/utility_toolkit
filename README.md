# Utility Toolkit

Utility Toolkit is a comprehensive Python package that provides a collection of tools for AWS operations, database handling (PostgreSQL and SQLite), and general utility functions.

## Installation

You can install Utility Toolkit using pip:
``` cmd
pip install utility_toolkit
```

## Features

- AWS Tools: Functions for interacting with various AWS services
- PostgreSQL Handler: Easy-to-use interface for PostgreSQL database operations
- SQLite Handler: Simplified SQLite database management
- General Tools: A collection of utility functions for common tasks

## Changes and What's New

- **Version 0.1.8** (Date: 2024-10-04)
  - Improved error handling in PostgreSQL and SQLite handlers.
  - Introduced new utility functions for dynamodb handler.
  - Enhance logging capabilities for better debugging.
  - Performance optimizations and bug fixes.

## Usage

Here are some quick examples of how to use Utility Toolkit:


```

python from utility_toolkit import aws_tools, postgresql_handler, sqlite_handler, general_tools

# AWS example

s3_content = aws_tools.get_s3_file_content('s3://my-bucket/my-file.txt')

# PostgreSQL example

with postgresql_handler.PostgreSQLConnection('my_db', 'user', 'password', 'localhost') as conn: results = conn.execute_query('SELECT * FROM my_table')

# SQLite example

with sqlite_handler.SQLiteConnection('my_database.db') as conn: conn.execute_query('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')

# General tools example

general_tools.create_directory_if_not_exists('my_new_directory')

```

For more detailed usage instructions, please refer to the documentation.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

```

6.  **Choose a License**

Choose an appropriate license (e.g., MIT License) and add it to the LICENSE file.

7.  **Create .gitignore**

Create a  `.gitignore`  file in the root directory:

```
__pycache__/
*.py[cod]
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.venv/
```