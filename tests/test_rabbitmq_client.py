import json
from unittest.mock import MagicMock

from app.util import rabbitmq_client as rmq


def teardown_function():
    # Reset publisher singleton between tests
    rmq.init_rabbitmq_publisher(None)


def test_init_rabbitmq_publisher_disabled():
    rmq.init_rabbitmq_publisher(None)
    assert rmq.get_rabbitmq_publisher() is None


def test_publish_order_job(monkeypatch):
    connection_mock = MagicMock()
    channel_mock = MagicMock()
    connection_mock.channel.return_value = channel_mock

    monkeypatch.setattr(rmq.pika, "BlockingConnection", MagicMock(return_value=connection_mock))

    rmq.init_rabbitmq_publisher("amqp://user:pass@rabbitmq:5672/vhost", order_queue="test.queue")
    publisher = rmq.get_rabbitmq_publisher()
    assert publisher is not None

    payload = {"foo": "bar"}
    assert publisher.publish_order_job(payload) is True

    channel_mock.queue_declare.assert_called_once_with(queue="test.queue", durable=True, arguments=None)
    channel_mock.basic_publish.assert_called_once()
    args, kwargs = channel_mock.basic_publish.call_args
    assert kwargs["routing_key"] == "test.queue"
    assert json.loads(kwargs["body"])["foo"] == "bar"
