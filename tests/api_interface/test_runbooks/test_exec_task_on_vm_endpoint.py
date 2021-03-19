import pytest
import uuid
from distutils.version import LooseVersion as LV

from calm.dsl.store import Version
from calm.dsl.cli.main import get_api_client
from calm.dsl.cli.constants import RUNLOG
from tests.api_interface.test_runbooks.test_files.exec_task import (
    ShellTaskOnLinuxVMAHVStaticEndpoint,
    ShellTaskOnLinuxVMAHVDynamicEndpoint1,
    ShellTaskOnLinuxVMAHVDynamicEndpoint2,
    ShellTaskOnLinuxVMAHVDynamicEndpoint3,
    ShellTaskOnLinuxVMVMWareStaticEndpoint,
    ShellTaskOnLinuxVMVMWareDynamicEndpoint1,
    ShellTaskOnLinuxVMVMWareDynamicEndpoint2,
    ShellTaskOnLinuxVMVMWareDynamicEndpoint3,
    #  ShellTaskOnLinuxVMAHVDynamicEndpoint4,
    #  ShellTaskOnLinuxVMVMWareStaticEndpoint,
    #  ShellTaskOnWindowsVMAHVStaticEndpoint,
    #  ShellTaskOnWindowsVMAHVDynamicEndpoint1,
    #  ShellTaskOnWindowsVMAHVDynamicEndpoint2
    #  ShellTaskOnLinuxVMVMWareStaticEndpoint,
)
from utils import upload_runbook, poll_runlog_status

# calm_version
CALM_VERSION = Version.get_version("Calm")


@pytest.mark.skipif(
    LV(CALM_VERSION) < LV("3.2.0"),
    reason="Tests are for env changes introduced in 3.2.0",
)
class TestExecTasksVMEndpoint:
    @pytest.mark.runbook
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "Runbook",
        [
            # Static VM IDs
            ShellTaskOnLinuxVMAHVStaticEndpoint,
            # Dynamic filter name equals
            ShellTaskOnLinuxVMAHVDynamicEndpoint1,
            # Dynamic filter name starts with
            ShellTaskOnLinuxVMAHVDynamicEndpoint2,
            # Dynamic filter power_state equals
            ShellTaskOnLinuxVMAHVDynamicEndpoint3,
            # Static VM IDs for Vmware
            # ShellTaskOnLinuxVMVMWareStaticEndpoint,
            # Dynamic filter name equals
            # ShellTaskOnLinuxVMVMWareDynamicEndpoint1,
            # Dynamic filter name starts with
            # ShellTaskOnLinuxVMVMWareDynamicEndpoint2,
            # Dynamic filter power_state equals
            # ShellTaskOnLinuxVMVMWareDynamicEndpoint3
        ],
    )
    def test_script_run(self, Runbook):
        client = get_api_client()
        rb_name = "test_exectask_vm_ep_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, Runbook)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # endpoints generated by this runbook
        endpoint_list = rb["spec"]["resources"].get("endpoint_definition_list", [])

        # running the runbook
        print("\n>>Running the runbook")

        res, err = client.runbook.run(rb_uuid, {})
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        response = res.json()
        runlog_uuid = response["status"]["runlog_uuid"]

        # polling till runbook run gets to terminal state
        state, reasons = poll_runlog_status(
            client, runlog_uuid, RUNLOG.TERMINAL_STATES, maxWait=360
        )

        print(">> Runbook Run state: {}\n{}".format(state, reasons))
        assert state == RUNLOG.STATUS.SUCCESS

        # Finding the trl id for the exec task (all runlogs for multiple IPs)
        exec_tasks = []
        res, err = client.runbook.list_runlogs(runlog_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        response = res.json()
        entities = response["entities"]
        for entity in entities:
            if (
                entity["status"]["type"] == "task_runlog"
                and entity["status"]["task_reference"]["name"] == "ExecTask"
                and runlog_uuid in entity["status"].get("machine_name", "")
            ):
                exec_tasks.append(entity["metadata"]["uuid"])

        # Now checking the output of exec task
        for exec_task in exec_tasks:
            res, err = client.runbook.runlog_output(runlog_uuid, exec_task)
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))
            runlog_output = res.json()
            output_list = runlog_output["status"]["output_list"]
            assert "Task is successful" in output_list[0]["output"]

        # delete the runbook
        _, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            print("runbook {} deleted".format(rb_name))

        # delete endpoints generated by this test
        for endpoint in endpoint_list:
            _, err = client.endpoint.delete(endpoint["uuid"])
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))
