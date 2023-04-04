import json
import time
import pytest

from click.testing import CliRunner
from calm.dsl.cli import main as cli

from calm.dsl.cli.constants import APPLICATION, ERGON_TASK
from calm.dsl.log import get_logging_handle
from calm.dsl.api import get_client_handle_obj
from calm.dsl.api.connection import REQUEST


VPC_TUNNEL_NAME = "vpc_name_1"
LOG = get_logging_handle(__name__)


class Application:
    NON_BUSY_APP_STATES = [
        APPLICATION.STATES.STOPPED,
        APPLICATION.STATES.RUNNING,
        APPLICATION.STATES.ERROR,
    ]

    def _wait_for_non_busy_state(self, name, timeout=300):
        return self._wait_for_states(name, self.NON_BUSY_APP_STATES, timeout)

    def _wait_for_states(self, name, states, timeout=100):
        LOG.info("Waiting for states: {}".format(states))
        runner = CliRunner()
        result = runner.invoke(cli, ["describe", "app", name, "--out=json"])
        if result.exit_code:
            cli_res_dict = {"Output": result.output, "Exception": str(result.exception)}
            LOG.debug(
                "Cli Response: {}".format(
                    json.dumps(cli_res_dict, indent=4, separators=(",", ": "))
                )
            )
            LOG.debug(
                "Traceback: \n{}".format(
                    "".join(traceback.format_tb(result.exc_info[2]))
                )
            )
        app_data = json.loads(result.output)
        LOG.info("App State: {}".format(app_data["status"]["state"]))
        LOG.debug("App Terminal states: {}".format(states))

        is_terminal = True
        poll_interval = 15

        state = app_data["status"]["state"]
        while state not in states:
            time.sleep(poll_interval)
            result = runner.invoke(cli, ["describe", "app", name, "--out=json"])
            app_data = json.loads(result.output)
            state = app_data["status"]["state"]
            LOG.debug("App State: {}".format(state))
            if timeout <= 0:
                LOG.error("Timed out before reaching desired state")
                is_terminal = False
                break
            timeout -= poll_interval
        LOG.debug("App data: {}".format(app_data))

        return is_terminal

    def get_substrates_platform_data(
        self, name, substrate_name=None, with_metadata=False
    ):
        """
        This routine returns platform data of a vm
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["-vvvvv", "describe", "app", name, "--out=json"])
        app_data = {}
        try:
            app_data = json.loads(result.output)
        except Exception as exp:
            LOG.error("App data: {}".format(result.output))

        platform_data_str = ""
        for substrate in app_data["status"]["resources"]["deployment_list"]:

            if not substrate_name:
                platform_data_str = substrate["substrate_configuration"][
                    "element_list"
                ][0]["platform_data"]

            elif substrate["substrate_configuration"]["name"] == substrate_name:
                platform_data_str = substrate["substrate_configuration"][
                    "element_list"
                ][0]["platform_data"]

            if platform_data_str:
                platform_data_dict = json.loads(platform_data_str)
                if with_metadata:
                    return platform_data_dict
                return platform_data_dict["status"]

        return None


class Task:
    def poll_task_to_state(
        self,
        client,
        task_uuid,
        expected_state=ERGON_TASK.STATUS.SUCCEEDED,
        duration=900,
    ):
        """routine will poll for task to come in specific state"""

        def get_task(client, task_uuid):
            res, err = client.nutanix_task.read(task_uuid)
            if err:
                LOG.error(err)
                pytest.fail(res)
            return res.json()

        task_payload = get_task(client, task_uuid)
        poll_interval = 15
        while task_payload["status"] not in ERGON_TASK.TERMINAL_STATES:
            time.sleep(poll_interval)
            if duration <= 0:
                break

            task_payload = get_task(client, task_uuid)
            duration -= poll_interval

        if task_payload["status"] != expected_state:
            LOG.debug(task_payload)
            pytest.fail("Task went to {} state".format(task_payload["status"]))

        return task_payload


class ReportPortal(object):
    def __init__(self, token):

        self.headers = {"Authorization": str(token)}
        self.host = "rp.calm.nutanix.com/api/v1/calm"
        self.client = get_client_handle_obj(
            host=self.host, port=None, scheme=REQUEST.SCHEME.HTTP
        )
        self.client.connection.session.headers = self.headers

    def get_launch_id(self, run_name, run_number):
        """
        This routine gets the launch id for the given runname and number
        Args:
            run_name(str): Report portal run name
            run_number(int): Report portal run number
        Returns:
            (str) launch id
        """
        endpoint = "launch?page.size=50&page=1"
        response, _ = self.client.connection._call(method="get", endpoint=endpoint)
        response = response.json()

        total_pages = int(response["page"]["totalPages"]) + 1

        for page in range(1, total_pages):
            endpoint = "launch?page.size=50&page.page={}&page.sort=start_time,number%2CDESC".format(
                page
            )
            launches, _ = self.client.connection._call(method="get", endpoint=endpoint)
            launches = json.loads(launches.content)

            for launch in launches["content"]:
                if launch["name"] == run_name and launch["number"] == run_number:
                    LOG.info(
                        "Launch id of run name: {}, number: {} is {}".format(
                            run_name, run_number, launch["id"]
                        )
                    )
                    return launch["id"]

        LOG.warning(
            "Launch id of run name: {}, number: {} is not found".format(
                run_name, run_number
            )
        )

    def get_tests(self, launch_id, query_parm, only_test_names=True):
        """
        This routine gets the tests for the given launch id and query_param
        Args:
            launch_id(str): Launch id
            query_parm(str): query_parm supported by report portal
            only_test_names(bool): Return only test name
        Returns:
            (list) list of test names
        """
        endpoint = "item?page.size=50&filter.eq.launch={}".format(launch_id)
        query_parm = endpoint + query_parm if query_parm else endpoint

        response, _ = self.client.connection._call(method="get", endpoint=endpoint)
        response = json.loads(response.content)

        total_pages = int(response["page"]["totalPages"]) + 1
        all_tests = list()
        for page in range(1, total_pages):
            endpoint = "item?page.page={}&page.size=50&filter.eq.launch={}&filter.in.issue$issue_type=TI001".format(
                page, launch_id
            )
            tests, _ = self.client.connection._call(method="get", endpoint=endpoint)
            tests = json.loads(tests.content)
            all_tests.extend(tests["content"])

        if not only_test_names:
            return all_tests
        all_test_name_list = list()
        for test in all_tests:
            test_full_name_split = test["name"].split("::")
            test_name = test_full_name_split[len(test_full_name_split) - 1]
            all_test_name_list.append(test_name)
        return all_test_name_list


def get_vpc_project(config):
    project_name = "default"
    vpc_enabled = config.get("IS_VPC_ENABLED", False)
    if not vpc_enabled:
        return {"name": project_name, "uuid": ""}

    return {
        "name": config.get("VPC_PROJECTS", {})
        .get("PROJECT1", {})
        .get("NAME", project_name),
        "uuid": config.get("VPC_PROJECTS", {}).get("PROJECT1", {}).get("UUID", ""),
    }


def get_vpc_tunnel_using_account(config):
    vpc = ""  # set default, if found set that value
    accounts = config.get("ACCOUNTS", {}).get("NUTANIX_PC", [])
    for acc in accounts:
        if acc.get("NAME") == "NTNX_LOCAL_AZ":
            for subnet in acc.get("OVERLAY_SUBNETS", []):
                if subnet.get("VPC", "") == VPC_TUNNEL_NAME:
                    vpc = VPC_TUNNEL_NAME
                    break

    vpc_tunnel = config.get("VPC_TUNNELS", {}).get("NTNX_LOCAL_AZ", {}).get(vpc, {})
    return {"name": vpc_tunnel.get("name", ""), "uuid": vpc_tunnel.get("uuid", "")}
