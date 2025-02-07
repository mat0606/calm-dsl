# THIS FILE IS AUTOMATICALLY GENERATED.
# Disclaimer: Please test this file before using in production.
# Change blueprint
"""
Generated blueprint DSL (.py)
"""

import json  # no_qa
import os  # no_qa

from calm.dsl.builtins import *  # no_qa


# Secret Variables
BP_CRED_CENTOS_KEY = read_local_file("BP_CRED_CENTOS_KEY")
BP_CRED_DomainAdministrator_PASSWORD = read_local_file(
    "BP_CRED_DomainAdministrator_PASSWORD"
)
BP_CRED_Centos2_CRED_PASSWORD = read_local_file(
    "BP_CRED_Centos2_CRED_PASSWORD"
)


# Credentials
BP_CRED_CENTOS = basic_cred(
    "centos",
    BP_CRED_CENTOS_KEY,
    name="CENTOS",
    type="KEY",
    default=True,
)
BP_CRED_DomainAdministrator = basic_cred(
    "administrator@dstantnx.local",
    BP_CRED_DomainAdministrator_PASSWORD,
    name="Domain Administrator",
    type="PASSWORD",
)
BP_CRED_Centos2 = basic_cred(
    "centos",
    BP_CRED_Centos2_CRED_PASSWORD,
    name="Centos 2 Credential",
    type="PASSWORD",
)


class Centos(Service):
    @action
    def __delete__():
        """System action for deleting an application. Deletes created VMs as well"""

        CalmTask.Exec.ssh(
            name="Unjoin Domain",
            filename=os.path.join(
                "scripts", "Service_Centos_Action___delete___Task_UnjoinDomain.sh"
            ),
            cred=ref(BP_CRED_CENTOS),
            target=ref(Centos),
        )

    @action
    def InstallNginx(name="Install Nginx"):

        CalmTask.Exec.ssh(
            name="Install Nginx",
            filename=os.path.join(
                "scripts", "Service_Centos_Action_InstallNginx_Task_InstallNginx.sh"
            ),
            cred=ref(BP_CRED_CENTOS),
            target=ref(Centos),
        )
        CalmTask.Exec.ssh(
            name="Configure Nginx",
            filename=os.path.join(
                "scripts", "Service_Centos_Action_InstallNginx_Task_ConfigureNginx.sh"
            ),
            cred=ref(BP_CRED_CENTOS),
            target=ref(Centos),
        )
        CalmTask.Exec.ssh(
            name="Configure Firewall",
            filename=os.path.join(
                "scripts",
                "Service_Centos_Action_InstallNginx_Task_ConfigureFirewall.sh",
            ),
            cred=ref(BP_CRED_CENTOS),
            target=ref(Centos),
        )


class ccalm_timeResources(AhvVmResources):

    memory = 2
    vCPUs = 2
    cores_per_vCPU = 1
    disks = [AhvVmDisk.Disk.Scsi.cloneFromImageService("CENTOS_77", bootable=True)]
    nics = [AhvVmNic.NormalNic.ingress("Client Network", cluster="VPC")]

    guest_customization = AhvVmGC.CloudInit(
        filename=os.path.join("specs", "ccalm_time_cloud_init_data.yaml")
    )


class ccalm_time(AhvVm):

    name = "c@@{calm_time}@@"
    resources = ccalm_timeResources


class Centos_VM(Substrate):

    os_type = "Linux"
    provider_type = "AHV_VM"
    provider_spec = ccalm_time
    provider_spec_editables = read_spec(
        os.path.join("specs", "Centos_VM_create_spec_editables.yaml")
    )
    readiness_probe = readiness_probe(
        connection_type="SSH",
        disabled=False,
        retries="5",
        connection_port=22,
        address="@@{platform.status.resources.nic_list[0].ip_endpoint_list[0].ip}@@",
        delay_secs="60",
        credential=ref(BP_CRED_CENTOS),
    )


class Package1(Package):

    services = [ref(Centos)]

    @action
    def __install__():

        CalmTask.Exec.ssh(
            name="Installed OS Package",
            filename=os.path.join(
                "scripts",
                "Package_Package1_Action___install___Task_InstalledOSPackage.sh",
            ),
            cred=ref(BP_CRED_CENTOS),
            target=ref(Centos),
        )
        CalmTask.Exec.ssh(
            name="Join DNS",
            filename=os.path.join(
                "scripts", "Package_Package1_Action___install___Task_JoinDNS.sh"
            ),
            cred=ref(BP_CRED_CENTOS),
            target=ref(Centos),
        )
        CalmTask.Exec.ssh(
            name="Join AD Domain",
            filename=os.path.join(
                "scripts", "Package_Package1_Action___install___Task_JoinADDomain.sh"
            ),
            cred=ref(BP_CRED_CENTOS),
            target=ref(Centos),
        )
        Centos.InstallNginx(name="Install Nginx")


class b1a5673a_deployment(Deployment):

    min_replicas = "1"
    max_replicas = "1"
    default_replicas = "1"

    packages = [ref(Package1)]
    substrate = ref(Centos_VM)


class Default(Profile):

    deployments = [b1a5673a_deployment]

    domain_name = CalmVariable.Simple(
        "dstantnx.local",
        label="",
        is_mandatory=False,
        is_hidden=False,
        runtime=False,
        description="",
    )

    Domain_Server_IP = CalmVariable.Simple(
        "10.129.33.219",
        label="",
        is_mandatory=False,
        is_hidden=False,
        runtime=False,
        description="",
    )

    Domain_Server = CalmVariable.Simple(
        "SGDC01",
        label="",
        is_mandatory=False,
        is_hidden=False,
        runtime=False,
        description="",
    )

    nginx_port = CalmVariable.Simple(
        "80",
        label="",
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )


class Nginx(Blueprint):

    services = [Centos]
    packages = [Package1]
    substrates = [Centos_VM]
    profiles = [Default]
    credentials = [BP_CRED_CENTOS, BP_CRED_DomainAdministrator]
