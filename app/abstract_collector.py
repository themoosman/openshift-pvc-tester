import logging
from abc import abstractmethod
from typing import List
from custom_metric import CustomMetric
from prometheus_client.core import GaugeMetricFamily


class AbstractCollector():

    def __init__(self, metric_name: str, metric_name_desc: str, namespace: str, dyn_client):
        self.metric_name = metric_name
        self.metric_name_desc = metric_name_desc
        self.namespace = namespace
        self.dyn_client = dyn_client

    def collect(self):
        commit_metric = GaugeMetricFamily(self.metric_name,
                                          self.metric_name_desc,
                                          labels=['app'])
        commit_metrics = self.generate_metrics()
        for metric in commit_metrics:
            logging.info("Collected metric{app=%s, ts=%s, value=%s}"
                         % (
                             metric.app_name,
                             str(float(metric.timestamp)),
                             str(float(metric.status))
                         )
                         )
            commit_metric.add_metric([metric.app_name], metric.status, timestamp=metric.timestamp)
            yield commit_metric

    @abstractmethod
    def generate_metrics(self) -> List[CustomMetric]:
        pass
