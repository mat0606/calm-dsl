"""
Calm Runbook Sample for running http tasks
"""
import json

from calm.dsl.runbooks import read_local_file
from calm.dsl.runbooks import runbook
from calm.dsl.runbooks import RunbookTask as Task, RunbookVariable as Variable
from calm.dsl.runbooks import CalmEndpoint as Endpoint
from calm.dsl.config import get_context
from utils import (
    read_test_config,
    change_uuids,
    update_tunnel_and_project,
)
from tests.utils import get_vpc_project, get_vpc_tunnel_using_account

AUTH_USERNAME = read_local_file(".tests/runbook_tests/auth_username")
AUTH_PASSWORD = read_local_file(".tests/runbook_tests/auth_password")
URL = read_local_file(".tests/runbook_tests/url")

ContextObj = get_context()
server_config = ContextObj.get_server_config()
pc_ip = server_config["pc_ip"]
TEST_URL = "https://{}:9440/".format(pc_ip)

endpoint = Endpoint.HTTP(
    URL, verify=False, auth=Endpoint.Auth(AUTH_USERNAME, AUTH_PASSWORD)
)
endpoint_with_tls_verify = Endpoint.HTTP(
    URL, verify=True, auth=Endpoint.Auth(AUTH_USERNAME, AUTH_PASSWORD)
)
endpoint_with_incorrect_auth = Endpoint.HTTP(URL, verify=False)
endpoint_without_auth = Endpoint.HTTP(TEST_URL)
endpoint_with_multiple_urls = Endpoint.HTTP(
    ["@@{base}@@/endpoints", "@@{base}@@/blueprints", "@@{base}@@/runbooks"],
    auth=Endpoint.Auth(AUTH_USERNAME, AUTH_PASSWORD),
)

endpoint_with_invalid_url = Endpoint.HTTP(
    TEST_URL + "api/nutanix/v3/random",
    verify=False,
    auth=Endpoint.Auth(AUTH_USERNAME, AUTH_PASSWORD),
)


def get_http_task_runbook(endpoint_file="http_endpoint_payload.json", config_file=None):
    """returns the runbook for http task"""

    global endpoint_payload
    endpoint_payload = change_uuids(read_test_config(file_name=endpoint_file), {})

    if endpoint_file == "http_tunnel_endpoint.json" and config_file:
        vpc_project_obj = get_vpc_project(config_file)
        vpc_tunnel_obj = get_vpc_tunnel_using_account(config_file)
        update_tunnel_and_project(vpc_tunnel_obj, vpc_project_obj, endpoint_payload)

    @runbook
    def HTTPTask(endpoints=[endpoint]):

        # Creating an endpoint with POST call
        Task.HTTP.post(
            body=json.dumps(endpoint_payload),
            headers={"Content-Type": "application/json"},
            content_type="application/json",
            response_paths={"ep_uuid": "$.metadata.uuid"},
            status_mapping={200: True},
            target=endpoints[0],
        )

        # Check the type of the created endpoint
        Task.HTTP.get(
            relative_url="/" + endpoint_payload["metadata"]["uuid"],
            headers={"Content-Type": "application/json"},
            content_type="application/json",
            response_paths={"ep_type": "$.spec.resources.type"},
            status_mapping={200: True},
            target=endpoints[0],
        )

        # Delete the created endpoint
        Task.HTTP.delete(
            relative_url="/" + endpoint_payload["metadata"]["uuid"],
            headers={"Content-Type": "application/json"},
            content_type="application/json",
            status_mapping={200: True},
            target=endpoints[0],
        )

        Task.Exec.escript(name="ExecTask", script='''print "@@{ep_type}@@"''')

    return HTTPTask


@runbook
def HTTPTaskWithValidations():

    # Creating an endpoint with POST call
    Task.HTTP.post(
        relative_url="/list",
        body=json.dumps({}),
        headers={"Content-Type": "application/json"},
        content_type="application/json",
        response_paths={"ep_uuid": "$.metdata.uuid"},
    )


@runbook
def HTTPTaskWithoutAuth(endpoints=[endpoint_without_auth]):

    # Creating an endpoint with POST call
    Task.HTTP.get(content_type="text/html", status_mapping={200: True})


@runbook
def HTTPTaskWithIncorrectCode(endpoints=[endpoint_without_auth]):

    # Creating an endpoint with POST call
    Task.HTTP.get(name="HTTPTask", content_type="text/html", status_mapping={300: True})


@runbook
def HTTPTaskWithFailureState(endpoints=[endpoint_without_auth]):

    # Creating an endpoint with POST call
    Task.HTTP.get(
        name="HTTPTask", content_type="text/html", status_mapping={200: False}
    )


@runbook
def HTTPTaskWithUnsupportedURL(endpoints=[endpoint_with_invalid_url]):

    # Creating an endpoint with POST call
    Task.HTTP.get(
        name="HTTPTask",
        relative_url="unsupported url",
        headers={"Content-Type": "application/json"},
        content_type="application/json",
        status_mapping={200: True},
    )


@runbook
def HTTPTaskWithUnsupportedPayload(endpoints=[endpoint]):

    # Creating an endpoint with POST call
    Task.HTTP.post(
        name="HTTPTask",
        relative_url="/list",
        body=json.dumps({"payload": "unsupported"}),
        headers={"Content-Type": "application/json"},
        content_type="application/json",
        status_mapping={200: True},
        target=endpoints[0],
    )


@runbook
def HTTPTaskWithIncorrectAuth(endpoints=[endpoint_with_incorrect_auth]):

    # Creating an endpoint with POST call
    Task.HTTP.post(
        name="HTTPTask",
        relative_url="/list",
        body=json.dumps({}),
        headers={"Content-Type": "application/json"},
        content_type="application/json",
        status_mapping={200: True},
        target=endpoints[0],
    )


@runbook
def HTTPTaskWithTLSVerify(endpoints=[endpoint_with_tls_verify]):

    # Creating an endpoint with POST call
    Task.HTTP.post(
        name="HTTPTask",
        relative_url="/list",
        body=json.dumps({}),
        headers={"Content-Type": "application/json"},
        content_type="application/json",
        status_mapping={200: True},
        target=endpoints[0],
    )


@runbook
def HTTPHeadersWithMacro(endpoints=[endpoint_with_incorrect_auth]):

    # Creating an endpoint with POST call
    Task.HTTP.post(
        name="HTTPTask",
        relative_url="/list",
        body=json.dumps({}),
        headers={"Authorization": "Bearer @@{calm_jwt}@@"},
        content_type="application/json",
        status_mapping={200: True},
        target=endpoints[0],
    )


@runbook
def HTTPRelativeURLWithMacro(endpoints=[endpoint]):

    relative_url_var = Variable.Simple("/list")  # noqa
    # Creating an endpoint with POST call
    Task.HTTP.post(
        name="HTTPTask",
        relative_url="@@{relative_url_var}@@",
        body=json.dumps({}),
        content_type="application/json",
        status_mapping={200: True},
        target=endpoints[0],
    )


@runbook
def HTTPEndpointWithMultipleURLs(endpoints=[endpoint_with_multiple_urls]):

    base = Variable.Simple(  # noqa
        "https://{}:9440/api/nutanix/v3".format(server_config["pc_ip"])
    )
    # Creating an endpoint with POST call
    Task.HTTP.post(
        name="HTTPTask",
        relative_url="/list",
        body=json.dumps({}),
        content_type="application/json",
        status_mapping={200: True},
    )
