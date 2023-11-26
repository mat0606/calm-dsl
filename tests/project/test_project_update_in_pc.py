import json

from calm.dsl.builtins import Project
from calm.dsl.builtins import Provider, Ref, read_local_file

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))
ACCOUNTS = DSL_CONFIG["ACCOUNTS"]

NTNX_ACCOUNT = ACCOUNTS["NUTANIX_PC"][0]
NTNX_ACCOUNT_NAME = NTNX_ACCOUNT["NAME"]
NTNX_SUBNET = NTNX_ACCOUNT["SUBNETS"][0]["NAME"]
NTNX_SUBNET_CLUSTER = NTNX_ACCOUNT["SUBNETS"][0]["CLUSTER"]

AWS_ACCOUNT = ACCOUNTS["AWS"][0]
AWS_ACCOUNT_NAME = AWS_ACCOUNT["NAME"]

AZURE_ACCOUNT = ACCOUNTS["AZURE"][0]
AZURE_ACCOUNT_NAME = AZURE_ACCOUNT["NAME"]

GCP_ACCOUNT = ACCOUNTS["GCP"][0]
GCP_ACCOUNT_NAME = GCP_ACCOUNT["NAME"]

VMWARE_ACCOUNT = ACCOUNTS["VMWARE"][0]
VMWARE_ACCOUNT_NAME = VMWARE_ACCOUNT["NAME"]

K8S_ACCOUNT = ACCOUNTS["K8S"][0]
K8S_ACCOUNT_NAME = K8S_ACCOUNT["NAME"]

USER = DSL_CONFIG["USERS"][0]
USER_NAME = USER["NAME"]


class TestDslProject(Project):
    """Sample DSL Project"""

    providers = [
        Provider.Ntnx(
            account=Ref.Account(NTNX_ACCOUNT_NAME),
            subnets=[Ref.Subnet(name=NTNX_SUBNET, cluster=NTNX_SUBNET_CLUSTER)],
        ),
        Provider.Aws(account=Ref.Account(AWS_ACCOUNT_NAME)),
        Provider.Azure(account=Ref.Account(AZURE_ACCOUNT_NAME)),
        Provider.Gcp(account=Ref.Account(GCP_ACCOUNT_NAME)),
        Provider.Vmware(account=Ref.Account(VMWARE_ACCOUNT_NAME)),
        Provider.K8s(account=Ref.Account(K8S_ACCOUNT_NAME)),
    ]

    users = [Ref.User(name=USER_NAME)]

    quotas = {"vcpus": 2, "storage": 2, "memory": 1}
