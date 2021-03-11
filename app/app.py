import os
import logging
import time
from pvc_collector import PvcCollector
from kubernetes import client, config
from openshift.dynamic import DynamicClient
from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)-15s %(levelname)-8s %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%m-%d-%Y %H:%M:%S"


loglevel = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
numeric_level = getattr(logging, loglevel.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError("Invalid log level: %s" % loglevel)
logging.basicConfig(format=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_LOG_DATE_FORMAT, level=numeric_level)
print("Initializing Logger with LogLevel: %s" % loglevel.upper())


def load_kube_config():
    namespace = None
    if "OPENSHIFT_BUILD_NAME" in os.environ:
        config.load_incluster_config()
        file_namespace = open(
            "/run/secrets/kubernetes.io/serviceaccount/namespace", "r"
        )
        if file_namespace.mode == "r":
            namespace = file_namespace.read()
            logging.info("namespace: %s" % (namespace))
    else:
        config.load_kube_config()
    return namespace


if __name__ == "__main__":
    namespace = load_kube_config()
    k8s_config = client.Configuration().get_default_copy()
    k8s_config.verify_ssl = False
    # k8s_client = client.api_client.ApiClient(configuration=k8s_config)
    k8s_client = client.ApiClient(configuration=k8s_config)
    dyn_client = DynamicClient(k8s_client)

    start_http_server(8080)
    # namespace = "test-mon"
    logging.info("Using namespace: %s" % (namespace))
    collector = PvcCollector("pvc_status", "Status of Provisioner", namespace, dyn_client)
    REGISTRY.register(collector)

    while True:
        time.sleep(1)
