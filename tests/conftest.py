import os
import uuid

import pytest
from influxdb_client import InfluxDBClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

from oomi_influx.config import InfluxSettings

_ORG = "testorg"
_TOKEN = "testtoken"
_ADMIN_PASSWORD = "password12"


@pytest.fixture(scope="session")
def influx_settings():
    bucket = f"test-{uuid.uuid4().hex[:8]}"
    test_url = os.environ.get("INFLUX_TEST_URL")

    if test_url:
        token = os.environ["INFLUX_TEST_TOKEN"]
        org = os.environ["INFLUX_TEST_ORG"]
        settings = _create_bucket_and_yield(test_url, token, org, bucket)
        yield settings
        _delete_bucket(test_url, token, org, bucket)
        return

    container = (
        DockerContainer("influxdb:2")
        .with_env("DOCKER_INFLUXDB_INIT_MODE", "setup")
        .with_env("DOCKER_INFLUXDB_INIT_USERNAME", "admin")
        .with_env("DOCKER_INFLUXDB_INIT_PASSWORD", _ADMIN_PASSWORD)
        .with_env("DOCKER_INFLUXDB_INIT_ORG", _ORG)
        .with_env("DOCKER_INFLUXDB_INIT_BUCKET", "init")
        .with_env("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN", _TOKEN)
        .with_exposed_ports(8086)
        .waiting_for(HttpWaitStrategy(8086, "/health").for_status_code(200))
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8086)
        url = f"http://{host}:{port}"
        settings = _create_bucket_and_yield(url, _TOKEN, _ORG, bucket)
        yield settings


def _create_bucket_and_yield(url: str, token: str, org: str, bucket: str) -> InfluxSettings:
    client = InfluxDBClient(url=url, token=token, org=org)
    try:
        client.buckets_api().create_bucket(bucket_name=bucket, org=org)
    finally:
        client.close()
    return InfluxSettings(url=url, token=token, org=org, bucket=bucket)


def _delete_bucket(url: str, token: str, org: str, bucket_name: str) -> None:
    client = InfluxDBClient(url=url, token=token, org=org)
    try:
        bucket = client.buckets_api().find_bucket_by_name(bucket_name)
        if bucket:
            client.buckets_api().delete_bucket(bucket)
    finally:
        client.close()
