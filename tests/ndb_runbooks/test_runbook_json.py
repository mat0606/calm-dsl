"""
Test for testing runbook generated json against known json
"""
import os
import pytest
import json

from calm.dsl.runbooks import runbook_json
from calm.dsl.builtins.models.utils import read_local_file
from calm.dsl.constants import STRATOS
from calm.dsl.config import get_context

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))
ACCOUNTS = DSL_CONFIG["ACCOUNTS"]
STRATOS_ENABLED = DSL_CONFIG.get("IS_STRATOS_ENABLED", False)


def _test_postgres_create_compile_result(known_attrs, generated_attrs):
    known_inargs = known_attrs["inarg_list"]
    generated_inargs = generated_attrs["inarg_list"]

    for var in known_inargs:
        if var["name"] in [
            "create_nutanix_ndb_database__softwareprofileid",
            "create_nutanix_ndb_database__softwareprofileversionid",
            "create_nutanix_ndb_database__computeprofileid",
            "create_nutanix_ndb_database__networkprofileid",
            "create_nutanix_ndb_database__nxclusterid",
            "create_nutanix_ndb_database__nodes__0__networkprofileid",
            "create_nutanix_ndb_database__dbparameterprofileid",
            "create_nutanix_ndb_database__timemachineinfo__0__slaid",
        ]:
            for generated_var in generated_inargs:
                if generated_var["name"] == var["name"]:
                    var["value"] = generated_var["value"]


def _test_postgres_clone_compile_result(known_attrs, generated_attrs):
    known_inargs = known_attrs["inarg_list"]
    generated_inargs = generated_attrs["inarg_list"]

    for var in known_inargs:
        if var["name"] in [
            "clone_from_time_machine_nutanix_ndb_database__compute_profile_id",
            "clone_from_time_machine_nutanix_ndb_database__network_profile_id",
            "clone_from_time_machine_nutanix_ndb_database__nx_cluster_id",
            "clone_from_time_machine_nutanix_ndb_database__nodes__0__nx_cluster_id",
            "clone_from_time_machine_nutanix_ndb_database__nodes__0__network_profile_id",
            "clone_from_time_machine_nutanix_ndb_database__nodes__0__compute_profile_id",
            "clone_from_time_machine_nutanix_ndb_database__database_parameter_profile_id",
        ]:
            for generated_var in generated_inargs:
                if generated_var["name"] == var["name"]:
                    var["value"] = generated_var["value"]


ACTION_NAME_JSON_TEST_MAPPING = {
    "postgres_create": _test_postgres_create_compile_result,
    "postgres_clone": _test_postgres_clone_compile_result,
}

RUNBOOK_ACTION_MAP = {}


def get_policy_status():
    context_obj = get_context()
    policy_config = context_obj.get_policy_config()
    if policy_config.get("policy_status", "False") == "False":
        return False
    return True


def set_runbook_action_map():
    from .create_postgres_task import nutanixdb_postgres_create
    from .restore_postgres_task import nutanixdb_postgres_restore
    from .snapshot_postgres_task import nutanixdb_postgres_snapshot
    from .delete_postgres_task import nutanixdb_postgres_delete
    from .clone_postgres_task import nutanixdb_postgres_clone

    RUNBOOK_ACTION_MAP["postgres_create"] = nutanixdb_postgres_create
    RUNBOOK_ACTION_MAP["postgres_restore"] = nutanixdb_postgres_restore
    RUNBOOK_ACTION_MAP["postgres_snapshot"] = nutanixdb_postgres_snapshot
    RUNBOOK_ACTION_MAP["postgres_delete"] = nutanixdb_postgres_delete
    RUNBOOK_ACTION_MAP["postgres_clone"] = nutanixdb_postgres_clone


def get_runbook_action_map():
    if not RUNBOOK_ACTION_MAP:
        set_runbook_action_map()
    return RUNBOOK_ACTION_MAP


@pytest.mark.skipif(
    not STRATOS_ENABLED or not get_policy_status(),
    reason="Stratos is not enabled on CALM",
)
@pytest.mark.parametrize(
    "json_file,action_name",
    [
        (
            "nutanixdb_postgres_create.json",
            "postgres_create",
        ),
        (
            "nutanixdb_postgres_restore.json",
            "postgres_restore",
        ),
        (
            "nutanixdb_postgres_snapshot.json",
            "postgres_snapshot",
        ),
        (
            "nutanixdb_postgres_delete.json",
            "postgres_delete",
        ),
        ("nutanixdb_postgres_clone.json", "postgres_clone"),
    ],
)
def test_runbook_json(json_file, action_name):
    """
    Test the generated json for a runbook agains known output
    """
    assert ACCOUNTS.get(STRATOS.PROVIDER.NDB, []), "No NDB account found in CALM"
    rb_action_map = get_runbook_action_map()
    _test_compare_compile_result(rb_action_map[action_name], json_file, action_name)


def _test_compare_compile_result(Runbook, json_file, action_name):
    """compares the runbook compilation and known output"""

    print("JSON compilation test for {}".format(action_name))
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, json_file)

    generated_json = json.loads(runbook_json(Runbook))
    known_json = json.loads(open(file_path).read())

    known_attrs = known_json["runbook"]["task_definition_list"][1]["attrs"]
    generated_attrs = generated_json["runbook"]["task_definition_list"][1]["attrs"]

    known_inargs = known_json["runbook"]["task_definition_list"][1]["attrs"][
        "inarg_list"
    ]
    generated_inargs = generated_json["runbook"]["task_definition_list"][1]["attrs"][
        "inarg_list"
    ]

    known_json["runbook"]["task_definition_list"][1]["attrs"]["inarg_list"] = sorted(
        known_inargs, key=lambda x: x["name"]
    )
    generated_json["runbook"]["task_definition_list"][1]["attrs"][
        "inarg_list"
    ] = sorted(generated_inargs, key=lambda x: x["name"])

    # Update account name
    known_attrs["account_reference"]["name"] = ACCOUNTS[STRATOS.PROVIDER.NDB][0]["NAME"]

    for field in known_attrs:
        if field.endswith("_reference"):
            if field not in generated_attrs:
                assert False, "{} is not present in generated_json".format(field)
            known_attrs[field]["uuid"] = generated_attrs[field]["uuid"]
    if action_name in ACTION_NAME_JSON_TEST_MAPPING:
        ACTION_NAME_JSON_TEST_MAPPING[action_name](known_attrs, generated_attrs)
    assert sorted(known_json.items()) == sorted(generated_json.items())
    print("JSON compilation successful for {}".format(Runbook.action_name))
