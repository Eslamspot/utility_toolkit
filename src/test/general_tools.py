import pytest
from unittest.mock import patch, MagicMock
from utility_toolkit import aws_tools

def test_get_s3_file_content():
  with patch('boto3.client') as mock_client:
      mock_s3 = MagicMock()
      mock_client.return_value = mock_s3
      mock_s3.get_object.return_value = {
          'Body': MagicMock(read=lambda: b'test content')
      }
      
      content = aws_tools.get_s3_file_content('s3://test-bucket/test-file.txt')
      assert content == 'test content'

def test_get_s3_file_content_binary():
  with patch('boto3.client') as mock_client:
      mock_s3 = MagicMock()
      mock_client.return_value = mock_s3
      mock_s3.get_object.return_value = {
          'Body': MagicMock(read=lambda: b'\x00\x01\x02')
      }
      
      content = aws_tools.get_s3_file_content('s3://test-bucket/test-file.bin')
      assert isinstance(content, bytes)
      assert content == b'\x00\x01\x02'

def test_get_s3_file_content_invalid_path():
  with pytest.raises(ValueError):
      aws_tools.get_s3_file_content('invalid-path')

# Add more tests for other AWS functions...