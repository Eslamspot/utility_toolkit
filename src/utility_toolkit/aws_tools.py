import datetime
import json
import typing
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

import boto3
import chardet
from botocore.exceptions import ClientError

from . import log


# You might need to set up AWS credentials or use a credentials file
# boto3.setup_default_session(profile_name='your_profile_name')

@log.log_decorator()
def create_s3_bucket(bucket_name: str, region: str = 'us-east-1') -> bool:
    """
    Create an S3 bucket in a specified region.

    Args:
        bucket_name (str): Name of the bucket to create.
        region (str): Region to create the bucket in. Defaults to 'us-east-1'.

    Returns:
        bool: True if bucket was created, False otherwise.

    Example:
        success = create_s3_bucket('my-new-bucket', 'us-west-2')
        if success:
            print("Bucket created successfully")
    """
    try:
        s3_client = boto3.client('s3', region_name=region)
        location = {'LocationConstraint': region}
        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except ClientError as e:
        print(f"An error occurred: {e}")
        return False
    return True


@log.log_decorator()
def upload_file_to_s3(file_path: str or Path, bucket_name: str, object_name: str = None) -> bool:
    """
    Upload a file to an S3 bucket.

    Args:
        file_path (str or Path): Path to the file to upload.
        bucket_name (str): Name of the bucket to upload to.
        object_name (str, optional): S3 object name. If not specified, file_name is used.

    Returns:
        bool: True if file was uploaded, False otherwise.

    Example:
        success = upload_file_to_s3('local/path/to/file.txt', 'my-bucket', 'remote/path/file.txt')
        if success:
            print("File uploaded successfully")
    """
    if object_name is None:
        object_name = Path(file_path).name

    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(str(file_path), bucket_name, object_name)
    except ClientError as e:
        print(f"An error occurred: {e}")
        return False
    return True


@log.log_decorator()
def download_file_from_s3(bucket_name: str, object_name: str, file_path: str or Path) -> bool:
    """
    Download a file from an S3 bucket.

    Args:
        bucket_name (str): Name of the bucket to download from.
        object_name (str): S3 object name to download.
        file_path (str or Path): Path to save the downloaded file.

    Returns:
        bool: True if file was downloaded, False otherwise.

    Example:
        success = download_file_from_s3('my-bucket', 'remote/path/file.txt', 'local/path/to/file.txt')
        if success:
            print("File downloaded successfully")
    """
    s3_client = boto3.client('s3')
    try:
        s3_client.download_file(bucket_name, object_name, str(file_path))
    except ClientError as e:
        print(f"An error occurred: {e}")
        return False
    return True


@log.log_decorator()
def list_s3_buckets() -> list:
    """
    List all S3 buckets for the authenticated account.

    Returns:
        list: A list of bucket names.

    Example:
        buckets = list_s3_buckets()
        for bucket in buckets:
            print(bucket)
    """
    s3_client = boto3.client('s3')
    try:
        response = s3_client.list_buckets()
        return [bucket['Name'] for bucket in response['Buckets']]
    except ClientError as e:
        print(f"An error occurred: {e}")
        return []


@log.log_decorator()
def create_dynamodb_table(table_name: str, key_schema: list, attribute_definitions: list,
                          provisioned_throughput: dict) -> bool:
    """
    Create a DynamoDB table.

    Args:
        table_name (str): Name of the table to create.
        key_schema (list): The key schema for the table.
        attribute_definitions (list): Attribute definitions for the table.
        provisioned_throughput (dict): Provisioned throughput for the table.

    Returns:
        bool: True if table was created, False otherwise.

    Example:
        key_schema = [{'AttributeName': 'id', 'KeyType': 'HASH'}]
        attribute_definitions = [{'AttributeName': 'id', 'AttributeType': 'S'}]
        provisioned_throughput = {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        success = create_dynamodb_table('my-table', key_schema, attribute_definitions, provisioned_throughput)
        if success:
            print("Table created successfully")
    """
    dynamodb = boto3.client('dynamodb')
    try:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput=provisioned_throughput
        )
    except ClientError as e:
        print(f"An error occurred: {e}")
        return False
    return True


@log.log_decorator()
def send_sqs_message(queue_url: str, message_body: str) -> bool:
    """
    Send a message to an SQS queue.

    Args:
        queue_url (str): URL of the SQS queue.
        message_body (str): Body of the message to send.

    Returns:
        bool: True if message was sent, False otherwise.

    Example:
        success = send_sqs_message('https://sqs.us-east-1.amazonaws.com/123456789012/my-queue', 'Hello, SQS!')
        if success:
            print("Message sent successfully")
    """
    sqs_client = boto3.client('sqs')
    try:
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=message_body)
    except ClientError as e:
        print(f"An error occurred: {e}")
        return False
    return True


@log.log_decorator()
def invoke_lambda_function(function_name: str, payload: dict) -> dict:
    """
    Invoke an AWS Lambda function.

    Args:
        function_name (str): Name or ARN of the Lambda function.
        payload (dict): Payload to pass to the Lambda function.

    Returns:
        dict: Response from the Lambda function.

    Example:
        response = invoke_lambda_function('my-function', {'key': 'value'})
        print(f"Lambda response: {response}")
    """
    lambda_client = boto3.client('lambda')
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        return json.loads(response['Payload'].read())
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {}


@log.log_decorator()
def create_ec2_instance(image_id: str, instance_type: str, key_name: str, security_group_ids: list) -> dict:
    """
    Create an EC2 instance.

    Args:
        image_id (str): The ID of the AMI to use for the instance.
        instance_type (str): The type of instance to launch.
        key_name (str): The name of the key pair to use for the instance.
        security_group_ids (list): A list of security group IDs to associate with the instance.

    Returns:
        dict: Information about the created instance.

    Example:
        instance = create_ec2_instance('ami-0c55b159cbfafe1f0', 't2.micro', 'my-key-pair', ['sg-0123456789abcdef0'])
        print(f"Created instance with ID: {instance['InstanceId']}")
    """
    ec2_client = boto3.client('ec2')
    try:
        response = ec2_client.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            KeyName=key_name,
            SecurityGroupIds=security_group_ids,
            MinCount=1,
            MaxCount=1
        )
        return response['Instances'][0]
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {}


@log.log_decorator()
def create_rds_instance(db_instance_identifier: str, db_engine: str, db_engine_version: str,
                        db_instance_class: str, master_username: str, master_password: str,
                        allocated_storage: int) -> dict:
    """
    Create an RDS instance.

    Args:
        db_instance_identifier (str): The DB instance identifier.
        db_engine (str): The name of the database engine to be used for this instance.
        db_engine_version (str): The version number of the database engine.
        db_instance_class (str): The compute and memory capacity of the DB instance.
        master_username (str): The name for the master user.
        master_password (str): The password for the master user.
        allocated_storage (int): The amount of storage (in gibibytes) to allocate for the DB instance.

    Returns:
        dict: Information about the created RDS instance.

    Example:
        rds_instance = create_rds_instance('mydb', 'mysql', '5.7', 'db.t2.micro', 'admin', 'password123', 20)
        print(f"Created RDS instance: {rds_instance['DBInstanceIdentifier']}")
    """
    rds_client = boto3.client('rds')
    try:
        response = rds_client.create_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            Engine=db_engine,
            EngineVersion=db_engine_version,
            DBInstanceClass=db_instance_class,
            MasterUsername=master_username,
            MasterUserPassword=master_password,
            AllocatedStorage=allocated_storage,
            PubliclyAccessible=False
        )
        return response['DBInstance']
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {}


@log.log_decorator()
def create_cloudformation_stack(stack_name: str, template_body: str, parameters: list = None) -> str:
    """
    Create a CloudFormation stack.

    Args:
        stack_name (str): The name that's associated with the stack.
        template_body (str): The structure that contains the template body.
        parameters (list, optional): A list of Parameter structures.

    Returns:
        str: The unique identifier for this stack.

    Example:
        with open('template.yaml', 'r') as template_file:
            template_body = template_file.read()
        stack_id = create_cloudformation_stack('my-stack', template_body)
        print(f"Created stack with ID: {stack_id}")
    """
    cf_client = boto3.client('cloudformation')
    try:
        response = cf_client.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=parameters or []
        )
        return response['StackId']
    except ClientError as e:
        print(f"An error occurred: {e}")
        return ""


@log.log_decorator()
def publish_sns_message(topic_arn: str, message: str, subject: str = None) -> str:
    """
    Publish a message to an SNS topic.

    Args:
        topic_arn (str): The ARN of the SNS topic.
        message (str): The message you want to send.
        subject (str, optional): The subject line for the message.

    Returns:
        str: The unique identifier for the published message.

    Example:
        message_id = publish_sns_message('arn:aws:sns:us-east-1:123456789012:MyTopic', 'Hello, SNS!', 'Test Message')
        print(f"Published message with ID: {message_id}")
    """
    sns_client = boto3.client('sns')
    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=subject
        )
        return response['MessageId']
    except ClientError as e:
        print(f"An error occurred: {e}")
        return ""


@log.log_decorator()
def put_cloudwatch_metric(namespace: str, metric_name: str, dimensions: list, value: float, unit: str) -> bool:
    """
    Put a single data point in a CloudWatch metric.

    Args:
        namespace (str): The namespace for the metric data.
        metric_name (str): The name of the metric.
        dimensions (list): A list of dimensions for the metric data.
        value (float): The value for the metric.
        unit (str): The unit of the metric.

    Returns:
        bool: True if the metric was put successfully, False otherwise.

    Example:
        dimensions = [{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}]
        success = put_cloudwatch_metric('AWS/EC2', 'CPUUtilization', dimensions, 70.0, 'Percent')
        if success:
            print("Metric put successfully")
    """
    cw_client = boto3.client('cloudwatch')
    try:
        cw_client.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Dimensions': dimensions,
                    'Value': value,
                    'Unit': unit
                }
            ]
        )
        return True
    except ClientError as e:
        print(f"An error occurred: {e}")
        return False


@log.log_decorator()
def create_iam_user(username: str, path: str = '/') -> dict:
    """
    Create a new IAM user.

    Args:
        username (str): The name of the user to create.
        path (str, optional): The path for the user name. Defaults to '/'.

    Returns:
        dict: Information about the created user.

    Example:
        user = create_iam_user('newuser')
        print(f"Created user: {user['UserName']}")
    """
    iam_client = boto3.client('iam')
    try:
        response = iam_client.create_user(
            UserName=username,
            Path=path
        )
        return response['User']
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {}


@log.log_decorator()
def create_vpc(cidr_block: str) -> dict:
    """
    Create a new VPC.

    Args:
        cidr_block (str): The IPv4 network range for the VPC, in CIDR notation.

    Returns:
        dict: Information about the created VPC.

    Example:
        vpc = create_vpc('10.0.0.0/16')
        print(f"Created VPC with ID: {vpc['VpcId']}")
    """
    ec2_client = boto3.client('ec2')
    try:
        response = ec2_client.create_vpc(
            CidrBlock=cidr_block
        )
        return response['Vpc']
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {}


@log.log_decorator()
def create_ecs_cluster(cluster_name: str) -> str:
    """
    Create a new ECS cluster.

    Args:
        cluster_name (str): The name of the cluster to create.

    Returns:
        str: The Amazon Resource Name (ARN) of the cluster.

    Example:
        cluster_arn = create_ecs_cluster('my-cluster')
        print(f"Created ECS cluster with ARN: {cluster_arn}")
    """
    ecs_client = boto3.client('ecs')
    try:
        response = ecs_client.create_cluster(
            clusterName=cluster_name
        )
        return response['cluster']['clusterArn']
    except ClientError as e:
        print(f"An error occurred: {e}")
        return ""


@log.log_decorator()
def create_elastic_beanstalk_application(application_name: str, description: str = '') -> dict:
    """
    Create a new Elastic Beanstalk application.

    Args:
        application_name (str): The name of the application to create.
        description (str, optional): A description of the application.

    Returns:
        dict: Information about the created application.

    Example:
        app = create_elastic_beanstalk_application('my-app', 'My first Beanstalk app')
        print(f"Created Elastic Beanstalk application: {app['ApplicationName']}")
    """
    eb_client = boto3.client('elasticbeanstalk')
    try:
        response = eb_client.create_application(
            ApplicationName=application_name,
            Description=description
        )
        return response['Application']
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {}


@log.log_decorator()
def create_route53_hosted_zone(domain_name: str, comment: str = '') -> dict:
    """
    Create a new Route 53 hosted zone.

    Args:
        domain_name (str): The name of the domain to create the hosted zone for.
        comment (str, optional): Any comments you want to include about the hosted zone.

    Returns:
        dict: Information about the created hosted zone.

    Example:
        zone = create_route53_hosted_zone('example.com', 'Hosted zone for example.com')
        print(f"Created Route 53 hosted zone with ID: {zone['HostedZone']['Id']}")
    """
    route53_client = boto3.client('route53')
    try:
        response = route53_client.create_hosted_zone(
            Name=domain_name,
            CallerReference=str(datetime.datetime.now()),
            HostedZoneConfig={
                'Comment': comment
            }
        )
        return response
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {}


@log.log_decorator()
def get_s3_file_content(s3_path: str, is_binary: bool = False, encoding: str = 'utf-8') -> typing.Union[str, bytes]:
    """
    Get the content of a file stored in an S3 bucket using an S3 path.

    Args:
        s3_path (str): The S3 path of the file (e.g., 's3://bucket-name/path/to/file.txt').
        is_binary (bool, optional): Whether the file should be treated as binary. Defaults to False.
        encoding (str, optional): The encoding to use when decoding text files. Defaults to 'utf-8'.

    Returns:
        Union[str, bytes]: The content of the file as a string (for text files) or bytes (for binary files).

    Raises:
        ValueError: If the provided S3 path is invalid.
        ClientError: If there's an error retrieving the file from S3.

    Example:
        try:
            # For text files
            text_content = get_s3_file_content('s3://my-bucket/path/to/textfile.txt')
            print(f"Text file content: {text_content}")

            # For binary files
            binary_content = get_s3_file_content('s3://my-bucket/path/to/binaryfile.bin', is_binary=True)
            print(f"Binary file size: {len(binary_content)} bytes")
        except (ValueError, ClientError) as e:
            print(f"An error occurred: {e}")
    """
    # Parse the S3 path
    parsed_url = urlparse(s3_path)
    if parsed_url.scheme != 's3':
        raise ValueError(f"Invalid S3 path: {s3_path}. Path should start with 's3://'")

    bucket_name = parsed_url.netloc
    object_key = parsed_url.path.lstrip('/')

    if not bucket_name or not object_key:
        raise ValueError(f"Invalid S3 path: {s3_path}. Unable to extract bucket name or object key.")

    s3_client = boto3.client('s3')
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response['Body'].read()

        if is_binary:
            return file_content
        else:
            return file_content.decode(encoding)
    except ClientError as e:
        print(f"An error occurred: {e}")
        raise e


@log.log_decorator()
def get_s3_file_content(s3_path: str) -> Union[str, bytes]:
    """
    Get the content of a file stored in an S3 bucket using an S3 path.
    Automatically detects whether the file is text or binary.

    Args:
        s3_path (str): The S3 path of the file (e.g., 's3://bucket-name/path/to/file.txt').

    Returns:
        Union[str, bytes]: The content of the file as a string (for text files) or bytes (for binary files).

    Raises:
        ValueError: If the provided S3 path is invalid.
        ClientError: If there's an error retrieving the file from S3.

    Example:
        try:
            content = get_s3_file_content('s3://my-bucket/path/to/myfile.txt')
            if isinstance(content, str):
                print(f"Text file content: {content}")
            else:
                print(f"Binary file size: {len(content)} bytes")
        except (ValueError, ClientError) as e:
            print(f"An error occurred: {e}")
    """
    # Parse the S3 path
    parsed_url = urlparse(s3_path)
    if parsed_url.scheme != 's3':
        raise ValueError(f"Invalid S3 path: {s3_path}. Path should start with 's3://'")

    bucket_name = parsed_url.netloc
    object_key = parsed_url.path.lstrip('/')

    if not bucket_name or not object_key:
        raise ValueError(f"Invalid S3 path: {s3_path}. Unable to extract bucket name or object key.")

    s3_client = boto3.client('s3')
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response['Body'].read()

        # Attempt to detect the encoding
        detection = chardet.detect(file_content)
        if detection['encoding'] is not None:
            try:
                # Attempt to decode as text
                return file_content.decode(detection['encoding'])
            except UnicodeDecodeError:
                # If decoding fails, treat as binary
                return file_content
        else:
            # If no encoding detected, treat as binary
            return file_content
    except ClientError as e:
        print(f"An error occurred: {e}")
        raise e
