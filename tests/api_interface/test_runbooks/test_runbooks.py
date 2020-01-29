import pytest
import uuid

from calm.dsl.cli.main import get_api_client
from calm.dsl.cli.constants import RUNLOG
from calm.dsl.builtins import create_endpoint_payload
from tests.sample_runbooks import DslPausePlayRunbook
from utils import upload_runbook, update_runbook, poll_runlog_status, read_test_config, change_uuids
from test_files.exec_task import linux_endpoint

RunbookPayload = read_test_config(file_name="runbook_payload.json")
RunbookUpdatePayload = read_test_config(file_name="runbook_payload2.json")


class TestRunbooks:
    @pytest.mark.slow
    @pytest.mark.runbook
    def test_runbooks_list(self):

        client = get_api_client()

        params = {"length": 20, "offset": 0}
        res, err = client.runbook.list(params=params)

        if not err:
            print("\n>> Runbook list call successful>>")
            assert res.ok is True
        else:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

    @pytest.mark.slow
    @pytest.mark.runbook
    def test_rb_crud(self):

        client = get_api_client()
        runbook = change_uuids(RunbookPayload, {})

        # Runbook Create
        res, err = client.runbook.create(runbook)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        rb = res.json()
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        rb_name = rb["spec"]["name"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"

        # reading the runbook using get call
        print("\n>>Reading Runbook")
        res, err = client.runbook.read(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            assert res.ok is True
            res = res.json()
            assert rb_name == res["spec"]["name"]
            assert rb_name == res["metadata"]["name"]
            assert rb_name == res["metadata"]["name"]
            print(">> Get call to runbook is successful >>")

        # creating an endpoint
        EndpointPayload, _ = create_endpoint_payload(linux_endpoint)
        ep_payload = EndpointPayload.get_dict()
        res, err = client.endpoint.upload_with_secrets("endpoint_" + str(uuid.uuid4())[-10:], "", ep_payload["spec"]["resources"])
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        endpoint = res.json()
        endpoint_state = endpoint["status"]["state"]
        endpoint_name = endpoint["status"]["name"]
        endpoint_uuid = endpoint["metadata"]["uuid"]
        assert endpoint_state == "ACTIVE"

        # updating the runbook
        del rb["status"]
        resources = change_uuids(RunbookUpdatePayload["spec"]["resources"], {})
        rb["spec"]["resources"]["credential_definition_list"] = resources["credential_definition_list"]
        rb["spec"]["resources"]["runbook"]["task_definition_list"][1] = resources["runbook"]["task_definition_list"][1]
        rb["spec"]["resources"]["runbook"]["task_definition_list"][0]["child_tasks_local_reference_list"][0]["uuid"] = resources["runbook"]["task_definition_list"][1]["uuid"]
        rb["spec"]["resources"]["runbook"]["variable_list"].append(resources["runbook"]["variable_list"][0])
        rb["spec"]["resources"]["default_target_reference"] = {
            "uuid": endpoint_uuid,
            "name": endpoint_name,
            "kind": "app_endpoint"
        }
        res, err = client.runbook.update(rb_uuid, rb)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        rb = res.json()
        assert rb["status"]["state"] == "ACTIVE"
        assert len(rb["spec"]["resources"]["credential_definition_list"]) == 1

        # run the runbook
        print("\n>>Running the runbook")
        res, err = client.runbook.run(rb_uuid, {})
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        response = res.json()
        runlog_uuid = response["status"]["runlog_uuid"]

        # polling till runbook run gets to terminal state
        state, reasons = poll_runlog_status(client, runlog_uuid, RUNLOG.TERMINAL_STATES)

        print(">> Runbook Run state: {}\n{}".format(state, reasons))
        assert state == RUNLOG.STATUS.SUCCESS

        # deleting runbook
        print("\n>>Deleting runbook")
        res, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            assert res.ok is True
            res = res.json()
            print("API Response: {}".format(res["description"]))
            print(">> Delete call to runbook is successful >>")

        # deleting endpoint
        _, err = client.endpoint.delete(endpoint_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

    @pytest.mark.skip(reason="runbook update through DSL is not supported on feat branch")
    @pytest.mark.slow
    @pytest.mark.runbook
    @pytest.mark.parametrize("Runbook", [DslPausePlayRunbook])
    def test_rb_update(self, Runbook):

        client = get_api_client()
        rb_name = "test_ask_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, Runbook)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # reading the runbook using get call
        print("\n>>Reading Runbook")
        res, err = client.runbook.read(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            assert res.ok is True
            res = res.json()
            task_list = res["spec"]["resources"]["runbook"]["task_definition_list"]
            assert len(task_list) == 6
            assert rb_name == res["spec"]["name"]
            assert rb_name == res["metadata"]["name"]
            assert rb_name == res["metadata"]["name"]
            print(">> Get call to runbook is successful >>")

        # updating the runbook
        # TODO have to update this with updated runbook
        rb = update_runbook(client, rb_name, DslPausePlayRunbook)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # reading the runbook using get call
        print("\n>>Reading Runbook")
        res, err = client.runbook.read(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            assert res.ok is True
            res = res.json()
            task_list = res["spec"]["resources"]["runbook"]["task_definition_list"]
            assert len(task_list) == 5
            assert rb_name == res["spec"]["name"]
            assert rb_name == res["metadata"]["name"]
            assert rb_name == res["metadata"]["name"]
            print(">> Get call to runbook is successful >>")

        # deleting runbook
        print("\n>>Deleting runbook")
        res, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            assert res.ok is True
            res = res.json()
            print("API Response: {}".format(res["description"]))
            print(">> Delete call to runbook is successful >>")
