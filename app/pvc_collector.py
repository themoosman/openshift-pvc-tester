import datetime
import yaml
import logging
from typing import List
from openshift.dynamic import exceptions
from abstract_collector import AbstractCollector
from custom_metric import CustomMetric


class PvcCollector(AbstractCollector):

    def __init__(self, metric_name: str, metric_name_desc: str, namespace: str, dyn_client):
        super().__init__(metric_name, metric_name_desc, namespace, dyn_client)

    def generate_metrics(self) -> List[CustomMetric]:
        logging.info("Calling generate_metrics")
        metrics = []
        status = 0.0
        pvc_name = "pvc-test"
        pvc = """
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
            name: pvc-test
        spec:
            storageClassName: thin
            accessModes:
                - ReadWriteOnce
            resources:
                requests:
                    storage: 1Gi
        """
        pvc_data = yaml.load(pvc, Loader=yaml.FullLoader)
        v1_pvc_list = self.dyn_client.resources.get(api_version='v1', kind='PersistentVolumeClaim')
        logging.info("Looking for PVs in %s" % self.namespace)
        try:
            v1_pvc_list.get(name=pvc_name, namespace=self.namespace)
            logging.info("Found PVC %s in namespace: %s" % (pvc_name, self.namespace))
            status = 1.0
            logging.info("Deleting old test PVC, will test creation on next scrape.")
            self.__delete_pvc(v1_pvc_list, pvc_name)
        except exceptions.NotFoundError:
            logging.info("No PVC found in namespace: %s", self.namespace)
            status = self.__create_pvc(v1_pvc_list, pvc_name, pvc_data)

        metric = CustomMetric()
        metric.app_name = self.metric_name
        metric.namespace = self.namespace
        metric.timestamp = datetime.datetime.now().timestamp()
        metric.status = status
        metrics.append(metric)
        return metrics

    def __create_pvc(self, v1_pvc_list, pvc_name, pvc_data) -> float:
        status = 0.0
        logging.info("Creating PVC: %s in namespace: %s" % (pvc_name, self.namespace))
        try:
            resp = v1_pvc_list.create(body=pvc_data, namespace=self.namespace)
            logging.info("PVC status: %s" % resp["status"]["phase"])
            endTime = datetime.datetime.now() + datetime.timedelta(seconds=90)
            while True:
                if datetime.datetime.now() >= endTime:
                    logging.error("Timeout while waiting for PVC %s" % pvc_name)
                    break
                else:
                    pvc = v1_pvc_list.get(namespace=self.namespace, name=pvc_name)
                    status = pvc["status"]["phase"]
                    if status == 'Bound':
                        logging.info("PVC status: Bound")
                        status = 1.0
                        logging.info("Cleanup test PVC")
                        self.__delete_pvc(v1_pvc_list, pvc_name)
                        break
        except exceptions.InternalServerError as e1:
            logging.error("InternalServerError occured while creating PVC")
            error = yaml.load(e1.body)
            logging.error(error)
        except Exception as e2:
            logging.error(str(e2))

        return status

    def __delete_pvc(self, v1_pvc_list, pvc_name):
        logging.info("Deleting PVC: %s" % pvc_name)
        try:
            v1_pvc_list.delete(name=pvc_name, namespace=self.namespace)
        except exceptions.NotFoundError as e1:
            logging.error("NotFoundError occured while deleting PVC")
            logging.error(str(e1))
        except Exception as e2:
            logging.error(str(e2))
