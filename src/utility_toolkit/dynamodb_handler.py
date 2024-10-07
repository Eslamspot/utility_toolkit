import logging
from typing import Dict, List, Any, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import time

try:
    from . import log
except ImportError:
    import log

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@log.class_log_decorator()
class DynamoDBHandler:
    """
    A handler class for interacting with Amazon DynamoDB.

    This class provides methods for common DynamoDB operations such as CRUD operations,
    querying, scanning, batch operations, and table management.

    Attributes:
        dynamodb (boto3.resources.factory.dynamodb.ServiceResource): The DynamoDB resource.
        table (boto3.resources.factory.dynamodb.Table): The DynamoDB table.

    Example:
        # Create a DynamoDBHandler instance
        handler = DynamoDBHandler('my-table', 'us-east-2')

        # Create an item
        handler.create_item({'id': '1', 'name': 'John Doe'})

        # Get an item
        item = handler.get_item({'id': '1'})
        print(item)
    """

    def __init__(self, table_name: str, region_name: str = 'us-east-2', profile_name: str = None):
        """
        Initialize the DynamoDBHandler.

        Args:
            table_name (str): The name of the DynamoDB table.
            region_name (str, optional): The AWS region name. Defaults to 'us-east-2'.
        profile_name (str, optional): The AWS profile to use. If None, default credentials will be used.

        Example:
            handler = DynamoDBHandler('my-table', 'us-east-2', 'my-aws-profile')
        """
        if profile_name:
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
            self.dynamodb = session.resource('dynamodb')
        else:
            self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.table = self.dynamodb.Table(table_name)

    def create_item(self, item: Dict[str, Any]) -> bool:
        """
        Create a new item in the DynamoDB table.

        Args:
            item (Dict[str, Any]): The item to be created.

        Returns:
            bool: True if the item was created successfully, False otherwise.

        Example:
            success = handler.create_item({'id': '1', 'name': 'John Doe', 'age': 30})
            if success:
                print("Item created successfully")
        """
        try:
            response = self.table.put_item(Item=item)
            return response['ResponseMetadata']['HTTPStatusCode'] == 200
        except ClientError as e:
            logger.error(f"Error creating item: {e}")
            return False

    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the DynamoDB table.

        Args:
            key (Dict[str, Any]): The primary key of the item to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The retrieved item, or None if not found.

        Example:
            item = handler.get_item({'id': '1'})
            if item:
                print(f"Retrieved item: {item}")
            else:
                print("Item not found")
        """
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error retrieving item: {e}")
            return None

    def update_item(self, key: Dict[str, Any], update_expression: str, expression_values: Dict[str, Any],
                    condition_expression: str = None) -> bool:
        """
        Update an existing item in the DynamoDB table.

        Args:
            key (Dict[str, Any]): The primary key of the item to update.
            update_expression (str): The update expression.
            expression_values (Dict[str, Any]): The expression attribute values.
            condition_expression (str, optional): A condition expression for the update.

        Returns:
            bool: True if the item was updated successfully, False otherwise.

        Example:
            success = handler.update_item(
                {'id': '1'},
                'SET age = :val1, address = :val2',
                {':val1': 31, ':val2': '123 Main St'},
                'attribute_exists(id)'
            )
            if success:
                print("Item updated successfully")
        """
        try:
            update_params = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values,
                'ReturnValues': "UPDATED_NEW"
            }
            if condition_expression:
                update_params['ConditionExpression'] = condition_expression

            response = self.table.update_item(**update_params)
            return response['ResponseMetadata']['HTTPStatusCode'] == 200
        except ClientError as e:
            logger.error(f"Error updating item: {e}")
            return False

    def delete_item(self, key: Dict[str, Any]) -> bool:
        """
        Delete an item from the DynamoDB table.

        Args:
            key (Dict[str, Any]): The primary key of the item to delete.

        Returns:
            bool: True if the item was deleted successfully, False otherwise.

        Example:
            success = handler.delete_item({'id': '1'})
            if success:
                print("Item deleted successfully")
        """
        try:
            response = self.table.delete_item(Key=key)
            return response['ResponseMetadata']['HTTPStatusCode'] == 200
        except ClientError as e:
            logger.error(f"Error deleting item: {e}")
            return False

    def query_items(self, key_condition_expression: Key, filter_expression: Optional[Attr] = None,
                    index_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query items from the DynamoDB table.

        Args:
            key_condition_expression (Key): The key condition expression for the query.
            filter_expression (Optional[Attr]): The filter expression for the query.
            index_name (Optional[str]): The name of the index to query.

        Returns:
            List[Dict[str, Any]]: A list of items matching the query.

        Example:
            from boto3.dynamodb.conditions import Key, Attr

            # Query items with a key condition
            key_condition_expression = Key('status').eq('completed')
            items = handler.query_items(key_condition_expression, index_name='StatusProjectIndex')

            # Query items with a key condition and filter
            key_condition_expression = Key('status').eq('completed')
            filter_expression = Attr('s3_path').eq('s3://bitbucket/file_8.html')
            items = handler.query_items(
                key_condition_expression,
                filter_expression,
                index_name='StatusProjectIndex',
                index_name='StatusProjectIndex'
            )

            print(f"Retrieved {len(items)} items")

            # more advanced example
            key_condition_expression = Key('project_id').eq('123') & Key('status').eq('completed')
            filter_expression = Attr('s3_path').eq('s3://bitbucket/file_8.html')

            # Query the GSI
            failed_items = handler.query_items(
              key_condition_expression=key_condition_expression,
              filter_expression=filter_expression,
              index_name='StatusProjectIndex'
            )

            # Print the results
            print(f"Found {len(failed_items)} items with status 'failed':")
        """
        try:
            query_params = {
                'KeyConditionExpression': key_condition_expression
            }
            if filter_expression:
                query_params['FilterExpression'] = filter_expression
            if index_name:
                query_params['IndexName'] = index_name

            response = self.table.query(**query_params)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error querying items: {e}")
            return []

    def query_items_with_pagination(self, key_condition_expression: Key, filter_expression: Optional[Attr] = None,
                                    index_name: Optional[str] = None, limit: int = 1000,
                                    last_evaluated_key: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Query items from the DynamoDB table with pagination support.

        Args:
            key_condition_expression (Key): The key condition expression for the query.
            filter_expression (Optional[Attr]): The filter expression for the query.
            index_name (Optional[str]): The name of the index to query.
            limit (int): The maximum number of items to return.
            last_evaluated_key (Optional[Dict[str, Any]]): The primary key of the item where the previous query operation stopped.

        Returns:
            Dict[str, Any]: A dictionary containing the items and the last evaluated key.

        Example:
            from boto3.dynamodb.conditions import Key, Attr

            # Initial query
            result = handler.query_items_with_pagination(
                Key('id').begins_with('user_'),
                filter_expression=Attr('age').gte(30),
                limit=100
            )
            items = result['Items']
            last_key = result['LastEvaluatedKey']

            # Subsequent queries
            while last_key:
                result = handler.query_items_with_pagination(
                    Key('id').begins_with('user_'),
                    filter_expression=Attr('age').gte(30),
                    limit=100,
                    last_evaluated_key=last_key
                )
                items.extend(result['Items'])
                last_key = result['LastEvaluatedKey']

            print(f"Retrieved {len(items)} items in total")
        """
        try:
            query_params = {
                'KeyConditionExpression': key_condition_expression,
                'Limit': limit
            }
            if filter_expression:
                query_params['FilterExpression'] = filter_expression
            if index_name:
                query_params['IndexName'] = index_name
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.query(**query_params)
            return {
                'Items': response.get('Items', []),
                'LastEvaluatedKey': response.get('LastEvaluatedKey')
            }
        except ClientError as e:
            logger.error(f"Error querying items with pagination: {e}")
            return {'Items': [], 'LastEvaluatedKey': None}


    def scan_items(self, filter_expression: Optional[Attr] = None, index_name: Optional[str] = None) -> List[
        Dict[str, Any]]:
        """
        Scan items from the DynamoDB table.

        Args:
            filter_expression (Optional[Attr]): The filter expression for the scan.
            index_name (Optional[str]): The name of the index to scan.

        Returns:
            List[Dict[str, Any]]: A list of items matching the scan.

        Example:
            from boto3.dynamodb.conditions import Attr

            # Scan all items
            all_items = handler.scan_items()

            # Scan items with a filter
            active_users = handler.scan_items(Attr('status').eq('failed'))

            print(f"Retrieved {len(active_users)} active users")
        """
        try:
            scan_params = {}
            if filter_expression:
                scan_params['FilterExpression'] = filter_expression
            if index_name:
                scan_params['IndexName'] = index_name

            response = self.table.scan(**scan_params)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error scanning items: {e}")
            return []

    def scan_items_with_pagination(self, filter_expression: Optional[Attr] = None,
                                   index_name: Optional[str] = None,
                                   limit: int = 1000,
                                   last_evaluated_key: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scan items from the DynamoDB table with pagination support.

        Args:
        filter_expression (Optional[Attr]): The filter expression for the scan.
        index_name (Optional[str]): The name of the index to scan.
        limit (int): The maximum number of items to return.
        last_evaluated_key (Optional[Dict[str, Any]]): The primary key of the item where the previous scan operation stopped.

        Returns:
        Dict[str, Any]: A dictionary containing the items and the last evaluated key.

        Example:
        # Initial scan
        result = handler.scan_items_with_pagination(
            filter_expression=Attr('age').gte(30),
            limit=100
        )
        items = result['Items']
        last_key = result['LastEvaluatedKey']

        # Subsequent scans
        while last_key:
            result = handler.scan_items_with_pagination(
                filter_expression=Attr('age').gte(30),
                limit=100,
                last_evaluated_key=last_key
            )
            items.extend(result['Items'])
            last_key = result['LastEvaluatedKey']

        print(f"Retrieved {len(items)} items in total")
        """
        try:
            start_time = time.time()
            scan_params = {
                'Limit': limit
            }
            if filter_expression:
                scan_params['FilterExpression'] = filter_expression
            if index_name:
                scan_params['IndexName'] = index_name
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.scan(**scan_params)
            end_time = time.time()

            self._update_metrics('scan_items_with_pagination', end_time - start_time, len(response.get('Items', [])))

            return {
                'Items': response.get('Items', []),
                'LastEvaluatedKey': response.get('LastEvaluatedKey')
            }
        except ClientError as e:
            logger.error(f"Error scanning items with pagination: {e}")
            self._update_metrics('scan_items_with_pagination', 0, 0, error=True)
            return {'Items': [], 'LastEvaluatedKey': None}

    def batch_read_items(self, keys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Read multiple items from the DynamoDB table in a batch.

        Args:
        keys (List[Dict[str, Any]]): A list of primary keys of the items to read.

        Returns:
        List[Dict[str, Any]]: A list of retrieved items.

        Example:
        keys_to_read = [
            {'id': '1'},
            {'id': '2'},
            {'id': '3'}
        ]
        items = handler.batch_read_items(keys_to_read)
        print(f"Retrieved {len(items)} items")
        """
        try:
            start_time = time.time()
            response = self.dynamodb.batch_get_item(
                RequestItems={
                    self.table.name: {
                        'Keys': keys
                    }
                }
            )
            end_time = time.time()

            items = response.get('Responses', {}).get(self.table.name, [])
            self._update_metrics('batch_read_items', end_time - start_time, len(items))

            return items
        except ClientError as e:
            logger.error(f"Error batch reading items: {e}")
            self._update_metrics('batch_read_items', 0, 0, error=True)
            return []

    def update_item_conditional(self, key: Dict[str, Any], update_expression: str,
                                expression_values: Dict[str, Any],
                                condition_expression: str) -> bool:
        """
        Update an existing item in the DynamoDB table with a condition.

        Args:
        key (Dict[str, Any]): The primary key of the item to update.
        update_expression (str): The update expression.
        expression_values (Dict[str, Any]): The expression attribute values.
        condition_expression (str): A condition expression for the update.

        Returns:
        bool: True if the item was updated successfully, False otherwise.

        Example:
        success = handler.update_item_conditional(
            {'id': '1'},
            'SET age = :val1, address = :val2',
            {':val1': 31, ':val2': '123 Main St'},
            'attribute_exists(id) AND age < :val1'
        )
        if success:
            print("Item updated successfully")
        """
        try:
            start_time = time.time()
            response = self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression=condition_expression,
                ReturnValues="UPDATED_NEW"
            )
            end_time = time.time()

            success = response['ResponseMetadata']['HTTPStatusCode'] == 200
            self._update_metrics('update_item_conditional', end_time - start_time, 1 if success else 0)

            return success
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info("Conditional update failed: condition not met")
            else:
                logger.error(f"Error updating item conditionally: {e}")
            self._update_metrics('update_item_conditional', 0, 0, error=True)
            return False

    def delete_item_conditional(self, key: Dict[str, Any], condition_expression: str) -> bool:
        """
        Delete an item from the DynamoDB table with a condition.

        Args:
        key (Dict[str, Any]): The primary key of the item to delete.
        condition_expression (str): A condition expression for the delete operation.

        Returns:
        bool: True if the item was deleted successfully, False otherwise.

        Example:
        success = handler.delete_item_conditional(
            {'id': '1'},
            'attribute_exists(id) AND age > :val'
        )
        if success:
            print("Item deleted successfully")
        """
        try:
            start_time = time.time()
            response = self.table.delete_item(
                Key=key,
                ConditionExpression=condition_expression,
                ReturnValues="ALL_OLD"
            )
            end_time = time.time()

            success = response['ResponseMetadata']['HTTPStatusCode'] == 200
            self._update_metrics('delete_item_conditional', end_time - start_time, 1 if success else 0)

            return success
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info("Conditional delete failed: condition not met")
            else:
                logger.error(f"Error deleting item conditionally: {e}")
            self._update_metrics('delete_item_conditional', 0, 0, error=True)
            return False

    def _update_metrics(self, operation: str, latency: float, item_count: int, error: bool = False):
        """
        Update metrics for the given operation.

        Args:
        operation (str): The name of the operation.
        latency (float): The operation latency in seconds.
        item_count (int): The number of items affected by the operation.
        error (bool): Whether an error occurred during the operation.
        """
        # This is a basic implementation. In a production environment, you might want to use
        # a more sophisticated metrics collection system like CloudWatch or Prometheus.
        if not hasattr(self, '_metrics'):
            self._metrics = {}

        if operation not in self._metrics:
            self._metrics[operation] = {
                'count': 0,
                'latency_sum': 0,
                'item_count_sum': 0,
                'error_count': 0
            }

        self._metrics[operation]['count'] += 1
        self._metrics[operation]['latency_sum'] += latency
        self._metrics[operation]['item_count_sum'] += item_count
        if error:
            self._metrics[operation]['error_count'] += 1

    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Get the current metrics for all operations.

        Returns:
        Dict[str, Dict[str, float]]: A dictionary of metrics for each operation.

        Example:
        metrics = handler.get_metrics()
        for operation, stats in metrics.items():
            print(f"Operation: {operation}")
            print(f"  Average Latency: {stats['avg_latency']:.3f} seconds")
            print(f"  Success Rate: {stats['success_rate']:.2%}")
            print(f"  Average Item Count: {stats['avg_item_count']:.2f}")
        """
        if not hasattr(self, '_metrics'):
            return {}

        result = {}
        for operation, stats in self._metrics.items():
            result[operation] = {
                'avg_latency': stats['latency_sum'] / stats['count'] if stats['count'] > 0 else 0,
                'success_rate': (stats['count'] - stats['error_count']) / stats['count'] if stats['count'] > 0 else 0,
                'avg_item_count': stats['item_count_sum'] / stats['count'] if stats['count'] > 0 else 0
            }
        return result

    def batch_write_items(self, items: List[Dict[str, Any]]) -> bool:
        """
        Write multiple items to the DynamoDB table in a batch.

        Args:
            items (List[Dict[str, Any]]): A list of items to write.

        Returns:
            bool: True if all items were written successfully, False otherwise.

        Example:
            items_to_write = [
                {'id': '2', 'name': 'Jane Doe', 'age': 28},
                {'id': '3', 'name': 'Bob Smith', 'age': 35},
                {'id': '4', 'name': 'Alice Johnson', 'age': 42}
            ]
            success = handler.batch_write_items(items_to_write)
            if success:
                print("All items written successfully")
        """
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Error batch writing items: {e}")
            return False

    def create_table_if_not_exists(self, key_schema: List[Dict[str, str]],
                                   attribute_definitions: List[Dict[str, str]],
                                   billing_mode: str = 'PAY_PER_REQUEST',
                                   provisioned_throughput: Optional[Dict[str, int]] = None,
                                   global_secondary_indexes: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Create a new DynamoDB table if it doesn't already exist.

        Args:
            key_schema (List[Dict[str, str]]): The key schema for the table.
            attribute_definitions (List[Dict[str, str]]): Attribute definitions for the table.
            billing_mode (str): The billing mode for the table. Can be 'PROVISIONED' or 'PAY_PER_REQUEST'.
            provisioned_throughput (Optional[Dict[str, int]]): Provisioned throughput for the table.
            global_secondary_indexes (Optional[List[Dict[str, Any]]]): List of global secondary indexes.

        Returns:
            bool: True if the table was created or already exists, False if there was an error.

        Example:
            key_schema = [
                {'AttributeName': 'id', 'KeyType': 'HASH'},
                {'AttributeName': 'date', 'KeyType': 'RANGE'}
            ]
            attribute_definitions = [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'date', 'AttributeType': 'S'}
            ]
            # For on-demand table
            success = handler.create_table_if_not_exists(key_schema, attribute_definitions, billing_mode='PAY_PER_REQUEST')
            # For provisioned table
            provisioned_throughput = {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
            success = handler.create_table_if_not_exists(key_schema, attribute_definitions,
                                                         billing_mode='PROVISIONED',
                                                         provisioned_throughput=provisioned_throughput)
            if success:
                print("Table is ready for use")
        Help:
            Key Schema:
            Defines the primary key of the table.
            Specifies the attributes that make up the primary key (partition key and optionally a sort key).
            Example:
            key_schema = [
                {'AttributeName': 'id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'date', 'KeyType': 'RANGE'}  # Sort key (optional)
            ]
            Attribute Definitions:
            Describes the data types of the attributes used in the key schema.
            Ensures that the attributes used in the key schema are defined with their types.
            Example:
            attribute_definitions = [
                {'AttributeName': 'id', 'AttributeType': 'S'},  # 'S' for String
                {'AttributeName': 'date', 'AttributeType': 'S'}  # 'S' for String
            ]
            Provisioned Throughput:
            Specifies the read and write capacity units for the table.
            Determines the maximum number of reads and writes per second that the table can handle.
            Example:
            provisioned_throughput = {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        """
        assert len(key_schema) in [1, 2], "Key schema must have 1 or 2 elements"
        try:
            if not self.table_exists():
                logger.info(f"Table {self.table.name} does not exist. Creating...")
                create_params = {
                    'TableName': self.table.name,
                    'KeySchema': key_schema,
                    'AttributeDefinitions': attribute_definitions,
                    'BillingMode': billing_mode
                }
                if billing_mode == 'PROVISIONED':
                    if not provisioned_throughput:
                        raise ValueError("provisioned_throughput is required for PROVISIONED billing mode")
                    create_params['ProvisionedThroughput'] = provisioned_throughput
                if global_secondary_indexes:
                    create_params['GlobalSecondaryIndexes'] = global_secondary_indexes

                self.dynamodb.create_table(**create_params)
                self.table.meta.client.get_waiter('table_exists').wait(TableName=self.table.name)
                logger.info(f"Table {self.table.name} created successfully.")
                return True
            else:
                logger.info(f"Table {self.table.name} already exists.")
                return True
        except ClientError as e:
            logger.error(f"Error creating table if not exists: {e}")
            return False

    def delete_table(self) -> bool:
        """
        Delete the DynamoDB table.

        Returns:
            bool: True if the table was deleted successfully, False otherwise.

        Example:
            success = handler.delete_table()
            if success:
                print("Table deleted successfully")
        """
        try:
            self.table.delete()
            self.table.meta.client.get_waiter('table_not_exists').wait(TableName=self.table.name)
            return True
        except ClientError as e:
            logger.error(f"Error deleting table: {e}")
            return False

    def describe_table(self) -> Optional[Dict[str, Any]]:
        """
        Describe the DynamoDB table.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the table description, or None if an error occurred.

        Example:
            table_description = handler.describe_table()
            if table_description:
                print(f"Table name: {table_description['Table']['TableName']}")
                print(f"Item count: {table_description['Table']['ItemCount']}")
                print(f"Table size in bytes: {table_description['Table']['TableSizeBytes']}")
        """
        try:
            return self.table.meta.client.describe_table(TableName=self.table.name)
        except ClientError as e:
            logger.error(f"Error describing table: {e}")
            return None

    def table_exists(self) -> bool:
        """
        Check if the DynamoDB table exists.

        Returns:
            bool: True if the table exists, False otherwise.

        Example:
            if handler.table_exists():
                print("Table exists")
            else:
                print("Table does not exist")
        """
        try:
            self.dynamodb.Table(self.table.name).load()
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            logger.error(f"Error checking if table exists: {e}")
            raise

    def update_table(self, key_schema: Optional[List[Dict[str, str]]] = None,
                     attribute_definitions: Optional[List[Dict[str, str]]] = None,
                     billing_mode: Optional[str] = None,
                     provisioned_throughput: Optional[Dict[str, int]] = None,
                     global_secondary_indexes: Optional[List[Dict[str, Any]]] = None,
                     global_secondary_index_updates: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Update the DynamoDB table configuration.

        Args:
        key_schema (Optional[List[Dict[str, str]]]): The updated key schema for the table.
        attribute_definitions (Optional[List[Dict[str, str]]]): Updated attribute definitions for the table.
        billing_mode (Optional[str]): The updated billing mode for the table. Can be 'PROVISIONED' or 'PAY_PER_REQUEST'.
        provisioned_throughput (Optional[Dict[str, int]]): Updated provisioned throughput for the table.
        global_secondary_indexes (Optional[List[Dict[str, Any]]]): List of new global secondary indexes to create.
        global_secondary_index_updates (Optional[List[Dict[str, Any]]]): Updates for existing global secondary indexes.

        Returns:
        bool: True if the table was updated successfully, False otherwise.

        Example:
        # Update the table to PAY_PER_REQUEST billing mode
        success = handler.update_table(billing_mode='PAY_PER_REQUEST')

        # Update provisioned throughput
        success = handler.update_table(
            billing_mode='PROVISIONED',
            provisioned_throughput={'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
        )

        # Add a new GSI
        new_gsi = {
            'IndexName': 'NewGSI',
            'KeySchema': [{'AttributeName': 'NewAttribute', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'},
            'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        }
        success = handler.update_table(
            attribute_definitions=[{'AttributeName': 'NewAttribute', 'AttributeType': 'S'}],
            global_secondary_indexes=[new_gsi]
        )

        if success:
            print("Table updated successfully")
        """
        try:
            update_params = {'TableName': self.table.name}

            if attribute_definitions:
                update_params['AttributeDefinitions'] = attribute_definitions

            if billing_mode:
                update_params['BillingMode'] = billing_mode

            if billing_mode == 'PROVISIONED':
                if not provisioned_throughput:
                    raise ValueError("provisioned_throughput is required for PROVISIONED billing mode")
                update_params['ProvisionedThroughput'] = provisioned_throughput

            if global_secondary_indexes:
                update_params['GlobalSecondaryIndexUpdates'] = [
                    {'Create': gsi} for gsi in global_secondary_indexes
                ]

            if global_secondary_index_updates:
                if 'GlobalSecondaryIndexUpdates' in update_params:
                    update_params['GlobalSecondaryIndexUpdates'].extend(global_secondary_index_updates)
                else:
                    update_params['GlobalSecondaryIndexUpdates'] = global_secondary_index_updates

            if update_params:
                self.table.meta.client.update_table(**update_params)
                self.table.meta.client.get_waiter('table_exists').wait(TableName=self.table.name)
                logger.info(f"Table {self.table.name} updated successfully.")
                return True
            else:
                logger.info("No updates to apply.")
                return True
        except ClientError as e:
            logger.error(f"Error updating table: {e}")
            return False

