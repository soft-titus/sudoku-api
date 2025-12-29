"""
Kafka service module
"""

import logging
from typing import Union
from confluent_kafka import Producer, KafkaError

import config

logger = logging.getLogger(__name__)


class KafkaClient:
    """
    Singleton wrapper for Kafka producer.

    Provides a single instance of a Kafka producer and a simple health check method.
    """

    _instance: Producer | None = None

    @classmethod
    def get_producer(cls) -> Producer:
        """
        Get the Kafka producer instance.
        Initializes the producer if it hasn't been created yet.

        Returns:
            Producer: The confluent_kafka Producer instance.
        """
        if cls._instance is None:
            cls._instance = Producer(
                {"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS}
            )
            logger.info("Kafka producer initialized")
        return cls._instance

    @classmethod
    def check_health(cls) -> None:
        """
        Perform a simple health check on Kafka by requesting metadata.

        Raises:
            KafkaError: If Kafka is not reachable.
        """
        producer = cls.get_producer()
        try:
            producer.list_topics(timeout=5)
            logger.info("Kafka connection OK")
        except KafkaError as exc:
            logger.error("Kafka health check failed: %s", exc)
            raise

    @classmethod
    def produce_message(cls, topic: str, key: str, value: Union[str, bytes]) -> None:
        """
        Produce a message to the specified Kafka topic.

        Args:
            topic: Kafka topic name.
            key: Message key.
            value: Message payload (str or bytes).

        Raises:
            KafkaError: If message cannot be delivered.
        """
        producer = cls.get_producer()
        try:
            producer.produce(
                topic=topic, key=key, value=value, on_delivery=cls.delivery_report
            )
            producer.flush()
        except KafkaError as exc:
            logger.error("Failed to produce message to Kafka: %s", exc)
            raise

    @staticmethod
    def delivery_report(err, msg) -> None:
        """
        Callback called once message is delivered or delivery fails.
        """
        if err is not None:
            logger.error("Message delivery failed: %s", err)
        else:
            logger.info("Message delivered to %s [%s]", msg.topic(), msg.partition())
