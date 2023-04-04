import json
import pytest
from app_edit_overlay_blueprint import TestVPCRuntime
from calm.dsl.log import get_logging_handle
import os
from calm.dsl.builtins import read_local_file
from calm.dsl.config import get_context
from calm.dsl.builtins.models.metadata_payload import (
    reset_metadata_obj,
    get_metadata_payload,
)
from calm.dsl.store import Version
from distutils.version import LooseVersion as LV

CRED_USERNAME = read_local_file(".tests/username")
CRED_PASSWORD = read_local_file(".tests/password")
DNS_SERVER = read_local_file(".tests/dns_server_two_vm_example")
MYSQL_PORT = read_local_file(".tests/mysql_port")

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))
NTNX_LOCAL_ACCOUNT = DSL_CONFIG["ACCOUNTS"]["NTNX_LOCAL_AZ"]


# calm_version
CALM_VERSION = Version.get_version("Calm")

LOG = get_logging_handle(__name__)


def get_local_az_overlay_details_from_dsl_config(config):
    networks = config["ACCOUNTS"]["NUTANIX_PC"]
    local_az_account = None
    for account in networks:
        if account.get("NAME") == "NTNX_LOCAL_AZ":
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

    for subnet in vlan_subnets_list:
        if subnet["NAME"] == config["AHV"]["NETWORK"]["VLAN1211"]:
            cluster = subnet["CLUSTER"]
            break
    return overlay_subnet, vpc, cluster


NETWORK1, VPC1, CLUSTER1 = get_local_az_overlay_details_from_dsl_config(DSL_CONFIG)


@pytest.mark.skipif(
    LV(CALM_VERSION) < LV("3.5.0") or not DSL_CONFIG.get("IS_VPC_ENABLED", False),
    reason="Overlay Subnets can be used in Calm v3.5.0+ blueprints or VPC is disabled on the setup",
)
class TestAppEditOverlaySubnetBlueprint:
    def setup_method(self):
        """Method to instantiate to created_bp_list"""

        # Resetting context
        ContextObj = get_context()
        ContextObj.reset_configuration()

        # Resetting metadata object
        reset_metadata_obj()

        self.created_bp_list = []

    def teardown_method(self):
        """Method to delete creates bps and apps during tests"""

        # Resetting context
        ContextObj = get_context()
        ContextObj.reset_configuration()

        # Resetting metadata object
        reset_metadata_obj()

    def test_json(self):
        get_metadata_payload(
            "tests/cli/runtime_helpers/ahv/app_edit_overlay_blueprint.py"
        )
        generated_json = json.loads(TestVPCRuntime.json_dumps(pprint=True))
        LOG.info(generated_json)

        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "app_edit_overlay_blueprint.json")
        known_json = json.loads(open(file_path).read())

        for _nic in known_json["app_profile_list"][0]["patch_list"][0]["attrs_list"][0][
            "data"
        ]["pre_defined_nic_list"]:
            _nic["subnet_reference"]["name"] = NETWORK1
            _nic["subnet_reference"].pop("uuid", None)
            _nic["vpc_reference"]["name"] = VPC1
            _nic.get("vpc_reference", {}).pop("uuid", None)

        for _nic in generated_json["app_profile_list"][0]["patch_list"][0][
            "attrs_list"
        ][0]["data"]["pre_defined_nic_list"]:
            _nic["subnet_reference"].pop("uuid", None)
            _nic.get("vpc_reference", {}).pop("uuid", None)

        known_json["substrate_definition_list"][0]["create_spec"][
            "cluster_reference"
        ] = {"kind": "cluster", "name": CLUSTER1}
        generated_json["substrate_definition_list"][0]["create_spec"][
            "cluster_reference"
        ].pop("uuid", None)

        for _nic in known_json["substrate_definition_list"][0]["create_spec"][
            "resources"
        ]["nic_list"]:
            _nic["subnet_reference"].pop("uuid", None)
            _nic["subnet_reference"]["name"] = NETWORK1
            _nic["vpc_reference"]["name"] = VPC1
            _nic.get("vpc_reference", {}).pop("uuid", None)

        for _nic in generated_json["substrate_definition_list"][0]["create_spec"][
            "resources"
        ]["nic_list"]:
            _nic["subnet_reference"].pop("uuid", None)
            _nic.get("vpc_reference", {}).pop("uuid", None)

        known_json["substrate_definition_list"][0]["create_spec"]["resources"][
            "account_uuid"
        ] = None
        generated_json["substrate_definition_list"][0]["create_spec"]["resources"][
            "account_uuid"
        ] = None
        known_json["substrate_definition_list"][0]["create_spec"]["resources"][
            "disk_list"
        ][0]["data_source_reference"]["uuid"] = None
        generated_json["substrate_definition_list"][0]["create_spec"]["resources"][
            "disk_list"
        ][0]["data_source_reference"]["uuid"] = None
        known_json["app_profile_list"][0]["patch_list"][0]["attrs_list"][0][
            "uuid"
        ] = None
        generated_json["app_profile_list"][0]["patch_list"][0]["attrs_list"][0][
            "uuid"
        ] = None
        print("known_json")
        print(known_json)
        print("generated_json")
        print(generated_json)

        if LV(CALM_VERSION) >= LV("3.4.0"):
            for cred in known_json["credential_definition_list"]:
                cred["cred_class"] = "static"

        assert sorted(known_json.items()) == sorted(
            generated_json.items()
        ), "Known Json: {}\nGen Json: {}".format(
            known_json.items(), generated_json.items()
        )
