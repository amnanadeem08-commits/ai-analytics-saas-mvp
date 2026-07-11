from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from backend.storage.s3_provider import S3StorageProvider


@pytest.fixture
def s3_provider():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="databot-test")
        yield S3StorageProvider(bucket="databot-test", region="us-east-1", client=client)


def test_s3_write_read_exists_delete(s3_provider):
    s3_provider.write("folder/file.bin", b"hello-s3")
    assert s3_provider.exists("folder/file.bin")
    assert s3_provider.read("folder/file.bin") == b"hello-s3"
    assert s3_provider.delete("folder/file.bin") is True
    assert not s3_provider.exists("folder/file.bin")


def test_s3_read_missing_raises(s3_provider):
    with pytest.raises(FileNotFoundError):
        s3_provider.read("missing.bin")


def test_s3_list_keys(s3_provider):
    s3_provider.write("reports/a.pdf", b"a")
    s3_provider.write("reports/b.pdf", b"b")
    s3_provider.write("other/c.pdf", b"c")
    keys = s3_provider.list_keys("reports/")
    assert keys == ["reports/a.pdf", "reports/b.pdf"]


def test_s3_delete_missing_returns_false(s3_provider):
    assert s3_provider.delete("nope.bin") is False
