# Note: In given example, we not added environment reference anywhere.
# Project create command will pick one Environment module from file and attaches to project

import uuid
import json

from calm.dsl.builtins import Project, read_local_file, readiness_probe
from calm.dsl.builtins import Provider, Ref
from calm.dsl.builtins import Substrate, Environment
from calm.dsl.builtins import AhvVmDisk, AhvVmNic, AhvVmGC
from calm.dsl.builtins import basic_cred, AhvVmResources, AhvVm


CENTOS_KEY = read_local_file(".tests/keys/centos")
CENTOS_PUBLIC_KEY = read_local_file(".tests/keys/centos_pub")

Centos = basic_cred("centos", CENTOS_KEY, name="Centos", type="KEY", default=True)

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))
ACCOUNTS = DSL_CONFIG["ACCOUNTS"]

NTNX_ACCOUNT_NAME = "NTNX_LOCAL_AZ"
VLAN_NETWORK = DSL_CONFIG["AHV"]["NETWORK"]["VLAN1211"]

CENTOS_CI = DSL_CONFIG["AHV"]["IMAGES"]["DISK"]["CENTOS_7_CLOUD_INIT"]
SQL_SERVER_IMAGE = DSL_CONFIG["AHV"]["IMAGES"]["CD_ROM"]["SQL_SERVER_2014_x64"]

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

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))


def get_local_az_overlay_details_from_dsl_config(config):
    networks = config["ACCOUNTS"]["NUTANIX_PC"]
    local_az_account = None
    for account in networks:
        if account.get("NAME") == NTNX_ACCOUNT_NAME:
            local_az_account = account
            break
    overlay_subnets_list = local_az_account.get("OVERLAY_SUBNETS", [])
    vlan_subnets_list = local_az_account.get("SUBNETS", [])

    cluster = ""
    vpc = ""
    overlay_subnet = ""

    for subnet in overlay_subnets_list:
        if subnet["NAME"] == "vpc_subnet_1" and subnet["VPC"] == "vpc_name_1":
            overlay_subnet = subnet["NAME"]
            vpc = subnet["VPC"]
            break

    for subnet in vlan_subnets_list:
        if subnet["NAME"] == config["AHV"]["NETWORK"]["VLAN1211"]:
            cluster = subnet["CLUSTER"]
            break
    return overlay_subnet, vpc, cluster


VLAN_NETWORK = DSL_CONFIG["AHV"]["NETWORK"]["VLAN1211"]
NETWORK1, VPC1, CLUSTER1 = get_local_az_overlay_details_from_dsl_config(DSL_CONFIG)


class MyAhvLinuxVmResources(AhvVmResources):

    memory = 4
    vCPUs = 2
    cores_per_vCPU = 1
    disks = [
        AhvVmDisk.Disk.Scsi.cloneFromImageService(CENTOS_CI, bootable=True),
    ]
    nics = [AhvVmNic(NETWORK1, vpc=VPC1)]

    guest_customization = AhvVmGC.CloudInit(
        config={
            "users": [
                {
                    "name": "centos",
                    "ssh-authorized-keys": [CENTOS_PUBLIC_KEY],
                    "sudo": ["ALL=(ALL) NOPASSWD:ALL"],
                }
            ]
        }
    )

    serial_ports = {0: False, 1: False, 2: True, 3: True}


class MyAhvLinuxVm(AhvVm):

    resources = MyAhvLinuxVmResources
    categories = {"AppFamily": "Backup", "AppType": "Default"}
    cluster = Ref.Cluster(CLUSTER1)


class AhvVmSubstrate(Substrate):
    """AHV VM config given by reading a spec file"""

    provider_spec = MyAhvLinuxVm
    readiness_probe = readiness_probe(disabled=True)


class MyAhvWindowsVmResources(AhvVmResources):

    memory = 4
    vCPUs = 2
    cores_per_vCPU = 1
    disks = [
        AhvVmDisk.Disk.Scsi.cloneFromImageService(CENTOS_CI, bootable=True),
    ]
    nics = [AhvVmNic(NETWORK1, vpc=VPC1)]

    guest_customization = AhvVmGC.Sysprep.FreshScript(
        filename="scripts/sysprep_script.xml"
    )

    serial_ports = {0: False, 1: False, 2: True, 3: True}


class MyAhvWindowsVm(AhvVm):

    resources = MyAhvWindowsVmResources
    categories = {"AppFamily": "Backup", "AppType": "Default"}
    cluster = Ref.Cluster(CLUSTER1)


class AhvWindowsVmSubstrate(Substrate):
    """AHV VM config given by reading a spec file"""

    provider_spec = MyAhvWindowsVm
    os_type = "Windows"
    readiness_probe = readiness_probe(disabled=True)


class ProjEnvironment(Environment):

    substrates = [AhvVmSubstrate, AhvWindowsVmSubstrate]
    credentials = [Centos]
    providers = [
        Provider.Ntnx(
            account=Ref.Account(NTNX_ACCOUNT_NAME),
            subnets=[
                Ref.Subnet(name=VLAN_NETWORK, cluster=CLUSTER1),
                Ref.Subnet(name=NETWORK1, vpc=VPC1),
            ],
            clusters=[Ref.Cluster(CLUSTER1)],
            vpcs=[Ref.Vpc(VPC1)],
        )
    ]


class TestDslProjectOverlayWithEnv5(Project):
    """Sample DSL Project with environments"""

    providers = [
        Provider.Ntnx(
            account=Ref.Account(NTNX_ACCOUNT_NAME),
            subnets=[
                Ref.Subnet(name=VLAN_NETWORK, cluster=CLUSTER1),
                Ref.Subnet(name=NETWORK1, vpc=VPC1),
            ],
            vpcs=[Ref.Vpc(name=VPC1, account_name=NTNX_ACCOUNT_NAME)],
            clusters=[Ref.Cluster(name=CLUSTER1, account_name=NTNX_ACCOUNT_NAME)],
        ),
        Provider.Aws(account=Ref.Account(AWS_ACCOUNT_NAME)),
        Provider.Azure(account=Ref.Account(AZURE_ACCOUNT_NAME)),
        Provider.Gcp(account=Ref.Account(GCP_ACCOUNT_NAME)),
        Provider.Vmware(account=Ref.Account(VMWARE_ACCOUNT_NAME)),
        Provider.K8s(account=Ref.Account(K8S_ACCOUNT_NAME)),
    ]

    users = [Ref.User(name=USER_NAME)]

    envs = [ProjEnvironment]

    quotas = {
        "vcpus": 1,
        "storage": 2,
        "memory": 1,
    }


# NOTE this is used for tests. Environment name is changed to prevent same name for multiple environments
ProjEnvironment.__name__ = "{}_{}".format(
    ProjEnvironment.__name__, str(uuid.uuid4())[:10]
)
