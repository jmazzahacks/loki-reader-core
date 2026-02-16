"""
MetricSeries model representing a series of metric datapoints with common labels.
"""

from dataclasses import dataclass

from .metric_sample import MetricSample


@dataclass
class MetricSeries:
    """
    A series of metric datapoints sharing common labels.

    Returned by Loki for metric queries like count_over_time, rate, etc.

    Attributes:
        labels: Dictionary of label key-value pairs identifying this series.
        samples: List of MetricSample objects with timestamp/value pairs.
    """

    labels: dict[str, str]
    samples: list[MetricSample]

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with labels and samples.
        """
        return {
            "labels": self.labels,
            "samples": [sample.to_dict() for sample in self.samples]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricSeries":
        """
        Create MetricSeries from dictionary.

        Args:
            data: Dictionary with labels and samples keys.

        Returns:
            MetricSeries instance.
        """
        samples = [MetricSample.from_dict(s) for s in data.get("samples", [])]
        return cls(
            labels=data["labels"],
            samples=samples
        )

    @classmethod
    def from_loki_matrix(cls, data: dict) -> "MetricSeries":
        """
        Create MetricSeries from Loki matrix result format.

        Matrix results have multiple timestamp/value pairs per series.
        Format: {"metric": {labels}, "values": [[ts, val], ...]}

        Args:
            data: Dictionary with 'metric' (labels) and 'values' (datapoints).

        Returns:
            MetricSeries instance.
        """
        labels = data.get("metric", {})
        values = data.get("values", [])
        samples = [MetricSample.from_loki_value(v) for v in values]
        return cls(labels=labels, samples=samples)

    @classmethod
    def from_loki_vector(cls, data: dict) -> "MetricSeries":
        """
        Create MetricSeries from Loki vector result format.

        Vector results have a single timestamp/value pair per series.
        Format: {"metric": {labels}, "value": [ts, val]}

        Args:
            data: Dictionary with 'metric' (labels) and 'value' (single datapoint).

        Returns:
            MetricSeries instance with one sample.
        """
        labels = data.get("metric", {})
        value = data.get("value", [])
        samples = [MetricSample.from_loki_value(value)] if value else []
        return cls(labels=labels, samples=samples)
