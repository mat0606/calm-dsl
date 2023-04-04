# THIS FILE IS AUTOMATICALLY GENERATED.
"""
Sample Calm DSL for Hello blueprint

The top-level folder contains the following files:
HelloBlueprint/
├── .local
│   └── keys
│       ├── centos
│       └── centos_pub
├── blueprint.py
└── scripts
    ├── pkg_install_task.sh
    └── pkg_uninstall_task.sh

On launch, this blueprint does the following:
  1. Creates AHV VM (2 vCPUs, 4G Mem, 1 core)
  2. Installs CentOS 7 by downloading image from http://download.nutanix.com.
  3. Injects SSH public key in the VM using cloud init.
  4. Creates calm credential using the SSH private key to run tasks on the VM.

Order of execution for every deployment during blueprint launch:
  1. Substrate.__pre_create__() (Only http and escript tasks are allowed here)
  2. Substrate.__create__() (Generated from provider_spec)
  3. Package.__install__() (Scripts to install application go here)
  4. Service.__create__() (Scripts to configure and create the service go here)
  5. Service.__start__() (Scripts to start the service go here)

Useful commands (execute from top-level directory):
  1. calm compile bp --file HelloBlueprint/blueprint.py
  2. calm create bp --file HelloBlueprint/blueprint.py --name <blueprint_name>
  3. calm get bps --name <blueprint_name>
  4. calm describe bp <blueprint_name>
  5. calm launch bp <blueprint_name> --app_name <app_name> -i
  6. calm get apps --name <app_name>
  7. calm describe app <app_name>
  8. calm delete app <app_name>
  9. calm delete bp <blueprint_name>

"""

import os

from calm.dsl.builtins import Service, Package, Substrate
from calm.dsl.builtins import Deployment, Profile, Blueprint
from calm.dsl.builtins import CalmVariable as Variable
from calm.dsl.builtins import CalmTask as Task
from calm.dsl.builtins import action, parallel, ref, basic_cred
from calm.dsl.builtins import read_local_file
from calm.dsl.builtins import vm_disk_package, AhvVmDisk, AhvVmNic, AhvCluster, AhvVpc
from calm.dsl.builtins import AhvVmGC, AhvVmResources, AhvVm, Ref


# SSH Credentials
CENTOS_USER = "centos"
CENTOS_KEY = read_local_file(os.path.join("keys", "centos"))
CENTOS_PUBLIC_KEY = read_local_file(os.path.join("keys", "centos_pub"))
CentosCred = basic_cred(
    CENTOS_USER,
    CENTOS_KEY,
    name="Centos",
    type="KEY",
    default=True,
)

# OS Image details for VM
CENTOS_IMAGE_SOURCE = "http://download.nutanix.com/calm/CentOS-7-x86_64-1810.qcow2"
CentosPackage = vm_disk_package(
    name="centos_disk",
    config={"image": {"source": CENTOS_IMAGE_SOURCE}},
)


class HelloService(Service):
    """Sample Service"""

    # Service Variables
    ENV = Variable.WithOptions.Predefined.string(
        ["DEV", "PROD"], default="DEV", is_mandatory=True, runtime=True
    )

    # Service Actions
    @action
    def __create__():
        # Step 1
        Task.Exec.ssh(name="Task1", script="echo 'Service create in ENV=@@{ENV}@@'")

    @action
    def __start__():
        # Step 1
        Task.Exec.ssh(name="Task1", script="echo 'Service start in ENV=@@{ENV}@@'")

    @action
    def __stop__():
        # Step 1
        Task.Exec.ssh(name="Task1", script="echo 'Service stop in ENV=@@{ENV}@@'")

    @action
    def __delete__():
        # Step 1
        Task.Exec.ssh(name="Task1", script="echo 'Service delete in ENV=@@{ENV}@@'")

    # Custom service actions
    @action
    def custom_action_1():
        """Sample service action"""

        # Step 1
        Task.Exec.ssh(name="Task11", script='echo "Hello"')

        # Step 2
        Task.Exec.ssh(name="Task12", script='echo "Hello again"')

    @action
    def custom_action_2():

        # Step 1
        Task.Exec.ssh(name="Task21", script="date")

        # Step 2
        with parallel():  # All tasks within this context will be run in parallel
            Task.Exec.ssh(name="Task22a", script="date")
            Task.Exec.ssh(name="Task22b", script="date")

        # Step 3
        Task.Exec.ssh(name="Task23", script="date")


class HelloPackage(Package):
    """Sample Package"""

    # Services created by installing this Package
    services = [ref(HelloService)]

    # Package Variables
    sample_pkg_var = Variable.Simple("Sample package installation")

    # Package Actions
    @action
    def __install__():

        # Step 1
        Task.Exec.ssh(
            name="Task1", filename=os.path.join("scripts", "pkg_install_task.sh")
        )

    @action
    def __uninstall__():

        # Step 1
        Task.Exec.ssh(
            name="Task1", filename=os.path.join("scripts", "pkg_uninstall_task.sh")
        )


class HelloVmResources(AhvVmResources):

    memory = 4
    vCPUs = 2
    cores_per_vCPU = 1
    disks = [
        AhvVmDisk.Disk.Scsi.cloneFromVMDiskPackage(CentosPackage, bootable=True),
    ]
    nics = [
        AhvVmNic(vpc="Sk_VPC", subnet="SkSubnet"),
        AhvVmNic(subnet="demo vpc subnet", vpc="demo vpc"),
    ]
    # nics = [AhvVmNic(subnet="vlan.800", cluster="auto_cluster_prod_1a619308826b")]
    # nics = [AhvVmNic.OverlayNic(vpc="Sk_VPC", subnet="SkSubnet"), AhvVmNic(subnet="vlan.800", cluster="auto_cluster_prod_1a619308826b")]

    guest_customization = AhvVmGC.CloudInit(
        config={
            "users": [
                {
                    "name": CENTOS_USER,
                    "ssh-authorized-keys": [CENTOS_PUBLIC_KEY],
                    "sudo": ["ALL=(ALL) NOPASSWD:ALL"],
                }
            ]
        }
    )


class HelloVm(AhvVm):

    resources = HelloVmResources
    cluster = Ref.Cluster(name="auto_cluster_prod_1a619308826b")
    # vpc_reference = AhvVpc("Sk_VPC")
    categories = {"AppFamily": "Demo", "AppType": "Default"}


class HelloSubstrate(Substrate):
    """AHV VM Substrate"""

    provider_type = "AHV_VM"
    provider_spec = HelloVm

    # Substrate Actions
    @action
    def __pre_create__():

        # Step 1
        Task.Exec.escript(
            name="Task1", script="print 'Pre Create task runs before VM is created'"
        )

    @action
    def __post_delete__():

        # Step 1
        Task.Exec.escript(
            name="Task1", script="print 'Post delete task runs after VM is deleted'"
        )


class HelloDeployment(Deployment):
    """Sample Deployment"""

    packages = [ref(HelloPackage)]
    substrate = ref(HelloSubstrate)


class HelloProfile(Profile):

    # Deployments under this profile
    deployments = [HelloDeployment]

    # Profile Variables
    var1 = Variable.Simple("sample_val1", runtime=True)
    var2 = Variable.Simple("sample_val2", runtime=True)
    var3 = Variable.Simple.int("2", validate_regex=True, regex=r"^[\d]*$")

    # Profile Actions
    @action
    def custom_profile_action_1():
        """Sample description for a profile action"""

        # Step 1: Run a task on a service in the profile
        Task.Exec.ssh(
            name="Task1",
            script='echo "Profile level action using @@{var1}@@ and @@{var2}@@ and @@{var3}@@"',
            target=ref(HelloService),
        )

        # Step 2: Call service action as a task.
        # It will execute all tasks under the given action.
        HelloService.custom_action_1(name="Task6")


class Hello(Blueprint):
    """Sample blueprint for Hello app using AHV VM"""

    credentials = [CentosCred]
    services = [HelloService]
    packages = [HelloPackage, CentosPackage]
    substrates = [HelloSubstrate]
    profiles = [HelloProfile]
