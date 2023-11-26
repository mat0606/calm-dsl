import pytest
import json
import uuid
import click
import traceback
from distutils.version import LooseVersion as LV
from click.testing import CliRunner
from calm.dsl.api import get_api_client
from calm.dsl.cli.quotas import _get_quota
from calm.dsl.builtins.models.helper.common import get_project
from calm.dsl.cli import main as cli
from calm.dsl.builtins.models.metadata_payload import reset_metadata_obj
from calm.dsl.builtins import read_local_file
from calm.dsl.config import get_context
from calm.dsl.store import Version
from calm.dsl.log import get_logging_handle

LOG = get_logging_handle(__name__)
DSL_PROJECT_PATH = "tests/project/test_project_in_pc.py"
DSL_UPDATE_PROJECT_PATH = "tests/project/test_project_update_in_pc.py"
DSL_PROJECT_WITH_ENV_PATH = "tests/project/test_project_with_env.py"
DSL_PROJECT_WITH_VPC_PATH = "tests/project/test_project_with_overlay_subnets.py"

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))
USER = DSL_CONFIG["USERS"][0]
USER_NAME = USER["NAME"]

ACCOUNTS = DSL_CONFIG["ACCOUNTS"]
AWS_ACCOUNT = ACCOUNTS["AWS"][0]
AWS_ACCOUNT_NAME = AWS_ACCOUNT["NAME"]

# calm_version
CALM_VERSION = Version.get_version("Calm")


class TestProjectCommands:
    def setup_method(self):
        """ "Reset the context changes"""

        # Resetting context
        ContextObj = get_context()
        ContextObj.reset_configuration()

        # Resetting metadata object
        reset_metadata_obj()

    def teardown_method(self):
        """ "Reset the context changes"""

        # Resetting context
        ContextObj = get_context()
        ContextObj.reset_configuration()

        # Resetting metadata object
        reset_metadata_obj()

    def test_projects_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["get", "projects"])
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
            pytest.fail("Project Get failed")
        LOG.info("Success")

    def test_compile_project(self):
        runner = CliRunner()
        LOG.info("Compiling Project file at {}".format(DSL_PROJECT_PATH))
        result = runner.invoke(
            cli, ["compile", "project", "--file={}".format(DSL_PROJECT_PATH)]
        )

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
            pytest.fail("Project compile command failed")
        LOG.info("Success")

    @pytest.mark.parametrize(
        "PROJECT_PATH",
        [
            pytest.param(DSL_PROJECT_PATH),
            pytest.param(
                DSL_PROJECT_WITH_VPC_PATH,
                marks=pytest.mark.skipif(
                    LV(CALM_VERSION) < LV("3.5.0")
                    or not DSL_CONFIG.get("IS_VPC_ENABLED", False),
                    reason="VPC Tunnels can be used in Calm v3.5.0+ or VPC is disabled on the setup",
                ),
            ),
        ],
    )
    def test_project_crud(self, PROJECT_PATH):
        """
        It will cover create/describe/update/delete/get commands on project
        This test assumes users/groups mentioned in project file are already created
        """

        context_obj = get_context()
        policy_config = context_obj.get_policy_config()

        # Create operation
        self._test_project_create_using_dsl(PROJECT_PATH)
        if policy_config.get("policy_status", "False") == "True":
            self._test_quotas_set_and_enabled_on_project_create(PROJECT_PATH)
        if self.VPC_FLAG:
            self._test_overlay_subnets()
        # Read operations
        click.echo("")
        self._test_project_describe_out_json()
        click.echo("")
        self._test_project_describe_out_text()
        click.echo("")
        self._test_project_list_name_filter()

        # Update operations
        click.echo("")
        self._test_update_project_using_cli_switches()
        click.echo("")
        self._test_update_project_using_dsl_file()

        # Delete operations
        click.echo("")
        self._test_project_delete()

    def _test_project_create_using_dsl(self, PROJECT_PATH=DSL_PROJECT_PATH):

        runner = CliRunner()
        if PROJECT_PATH == DSL_PROJECT_WITH_VPC_PATH:
            self.VPC_FLAG = True
        else:
            self.VPC_FLAG = False

        self.dsl_project_name = "Test_DSL_Project_{}".format(str(uuid.uuid4()))
        LOG.info("Testing 'calm create project' command")
        result = runner.invoke(
            cli,
            [
                "create",
                "project",
                "--file={}".format(PROJECT_PATH),
                "--name={}".format(self.dsl_project_name),
                "--description='Test DSL Project to delete'",
            ],
        )
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
            pytest.fail("Project creation from python file failed")
        LOG.info("Success")

    def _test_quotas_set_and_enabled_on_project_create(
        self, PROJECT_PATH=DSL_PROJECT_PATH
    ):
        """
        Test if quotas are set and enabled on crating project
        """

        client = get_api_client()
        runner = CliRunner()
        if PROJECT_PATH == DSL_PROJECT_WITH_VPC_PATH:
            self.VPC_FLAG = True
        else:
            self.VPC_FLAG = False

        self.dsl_project_name = "Test_DSL_Project_{}".format(str(uuid.uuid4()))
        LOG.info("Testing 'calm create project' command")
        result = runner.invoke(
            cli,
            [
                "create",
                "project",
                "--file={}".format(PROJECT_PATH),
                "--name={}".format(self.dsl_project_name),
                "--description='Test DSL Project to delete'",
            ],
        )
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
            pytest.fail("Project creation from python file failed")

        project_uuid = json.loads(result.output).get("uuid", "")
        quota_entities = {"project": project_uuid}
        quota_spec = _get_quota(client=client, quota_entities=quota_entities)
        quota = quota_spec[0].get("entities", None)

        if not (
            (quota)
            and (
                quota[0].get("status", {}).get("resources", {}).get("state", "")
                == "enabled"
            )
            and (
                quota[0]
                .get("status", {})
                .get("resources", {})
                .get("data", {})
                .get("vcpu", -1)
            )
            and (
                quota[0]
                .get("status", {})
                .get("resources", {})
                .get("data", {})
                .get("disk", -1)
            )
            and (
                quota[0]
                .get("status", {})
                .get("resources", {})
                .get("data", {})
                .get("memory", -1)
            )
        ):
            pytest.fail("Quota enable/set failed")

        self._test_disable_quotas_using_cli_switches(project_uuid=project_uuid)
        self._test_enable_quotas_using_cli_switches(project_uuid=project_uuid)
        self._test_quotas_updated_on_project_update(
            UPDATE_PROJECT_PATH=DSL_UPDATE_PROJECT_PATH
        )

        LOG.info("Success")

    def _test_quotas_updated_on_project_update(
        self, UPDATE_PROJECT_PATH=DSL_UPDATE_PROJECT_PATH
    ):
        """
        Test if projects are updated on using project update command
        """

        client = get_api_client()
        runner = CliRunner()
        LOG.info("Testing 'calm update project' command for updating quotas")
        result = runner.invoke(
            cli,
            [
                "update",
                "project",
                self.dsl_project_name,
                "--file={}".format(UPDATE_PROJECT_PATH),
            ],
        )
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
            pytest.fail("Project update from python file failed")

        project_uuid = json.loads(result.output).get("uuid", "")
        quota_entities = {"project": project_uuid}
        quota_spec = _get_quota(client=client, quota_entities=quota_entities)
        quota = quota_spec[0].get("entities", None)

        if not (
            (quota)
            and (
                quota[0].get("status", {}).get("resources", {}).get("state", "")
                == "enabled"
            )
            and (
                quota[0]
                .get("status", {})
                .get("resources", {})
                .get("data", {})
                .get("vcpu", -1)
                == 2
            )
            and (
                quota[0]
                .get("status", {})
                .get("resources", {})
                .get("data", {})
                .get("disk", -1)
                == 2147483648
            )
            and (
                quota[0]
                .get("status", {})
                .get("resources", {})
                .get("data", {})
                .get("memory", -1)
                == 1073741824
            )
        ):
            pytest.fail("Quota updation failed")

    LOG.info("Success")

    def _test_disable_quotas_using_cli_switches(self, project_uuid):
        """
        Test if cli switch disables quotas at project level to given project.
        """

        client = get_api_client()
        runner = CliRunner()
        LOG.info(
            "Testing 'calm update project' command using --disable-quotas cli switch"
        )
        result = runner.invoke(
            cli,
            ["update", "project", self.dsl_project_name, "--disable-quotas"],
        )

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
            pytest.fail("Project update call failed")

        quota_entities = {"project": project_uuid}
        quota_spec = _get_quota(client=client, quota_entities=quota_entities)
        quota_state = (
            quota_spec[0]
            .get("entities", [])[0]
            .get("status", {})
            .get("resources", {})
            .get("state", None)
        )

        if quota_state != "disabled":
            pytest.fail("Failed disabling quotas using cli switch")

        LOG.info("Success")

    def _test_enable_quotas_using_cli_switches(self, project_uuid):
        """
        Test if cli switch enables quotas at project level to given project.
        """

        client = get_api_client()
        runner = CliRunner()
        LOG.info(
            "Testing 'calm update project' command using --enable-quotas cli switch"
        )
        result = runner.invoke(
            cli,
            ["update", "project", self.dsl_project_name, "--enable-quotas"],
        )
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
            pytest.fail("Project update call failed")

        quota_entities = {"project": project_uuid}
        quota_spec = _get_quota(client=client, quota_entities=quota_entities)
        quota_state = (
            quota_spec[0]
            .get("entities", [])[0]
            .get("status", {})
            .get("resources", {})
            .get("state", None)
        )

        if quota_state != "enabled":
            pytest.fail("Failed enabling quotas using cli switch")

        LOG.info("Success")

    def _test_project_describe_out_text(self):

        runner = CliRunner()
        LOG.info("Testing 'calm describe project --out text' command")
        result = runner.invoke(cli, ["describe", "project", self.dsl_project_name])
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
            pytest.fail("Project Get call failed")

        project_name_str = "Name: {}".format(self.dsl_project_name)
        assert project_name_str in result.output
        LOG.info("Success")

    def _test_project_describe_out_json(self):

        runner = CliRunner()
        LOG.info("Testing 'calm describe project --out json' command")
        result = runner.invoke(
            cli, ["describe", "project", self.dsl_project_name, "--out", "json"]
        )
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
            pytest.fail("Project Get call failed")

        project_name_str = '"name": "{}"'.format(self.dsl_project_name)
        assert project_name_str in result.output
        LOG.info("Success")

    def _test_project_list_name_filter(self):

        runner = CliRunner()
        LOG.info("Testing 'calm get projects --name <project_name>' command")
        result = runner.invoke(
            cli, ["get", "projects", "--name", self.dsl_project_name]
        )
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
            pytest.fail("Project list call failed")

        assert self.dsl_project_name in result.output
        LOG.info("Success")

    def _test_update_project_using_cli_switches(self):
        """
        Adds user to given project.
        (User must be prsent in db)
        """

        runner = CliRunner()
        LOG.info("Testing 'calm update project' command using cli switches")
        result = runner.invoke(
            cli,
            [
                "update",
                "project",
                self.dsl_project_name,
                "--add_user",
                USER_NAME,
            ],
        )
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
            pytest.fail("Project update call failed")
        LOG.info("Success")

    def _test_account_updation_using_cli_switches(self):
        """Removes and adds account to the project"""

        runner = CliRunner()
        LOG.info(
            "Testing 'calm update project' command using cli switches for account deletion"
        )
        result = runner.invoke(
            cli,
            [
                "update",
                "project",
                self.dsl_project_name,
                "--remove_account",
                AWS_ACCOUNT_NAME,
            ],
        )
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
            pytest.fail("Project update call failed")

        LOG.info(
            "Testing 'calm update project' command using cli switches for account addition"
        )
        result = runner.invoke(
            cli,
            [
                "update",
                "project",
                self.dsl_project_name,
                "--add_account",
                AWS_ACCOUNT_NAME,
            ],
        )
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
            pytest.fail("Project update call failed")

        LOG.info("Success")

    def _test_update_project_using_dsl_file(self):
        """
        Removes user from given project.
        (User must be prsent in db)
        """

        runner = CliRunner()
        LOG.info("Testing 'calm update project' command using dsl file")
        result = runner.invoke(
            cli,
            [
                "update",
                "project",
                self.dsl_project_name,
                "--file={}".format(DSL_PROJECT_PATH),
            ],
        )
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
            pytest.fail("Project update call failed")
        LOG.info("Success")

    def _test_project_delete(self):

        runner = CliRunner()
        LOG.info("Testing 'calm delete project' command")
        result = runner.invoke(cli, ["delete", "project", self.dsl_project_name])
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
            pytest.fail("Project delete call failed")
        LOG.info("Success")

    @pytest.mark.skipif(
        LV(CALM_VERSION) >= LV("3.2.0"), reason="Env creation changed in 3.2.0"
    )
    def test_project_with_env_create_and_delete(self):
        """
        Describe and update flow are already checked in `test_project_crud`
        It will test only create and delete flow on projects with environment
        """

        runner = CliRunner()
        self.dsl_project_name = "Test_DSL_Project_Env{}".format(str(uuid.uuid4()))
        LOG.info("Testing 'calm create project' command")
        result = runner.invoke(
            cli,
            [
                "create",
                "project",
                "--file={}".format(DSL_PROJECT_WITH_ENV_PATH),
                "--name={}".format(self.dsl_project_name),
                "--description='Test DSL Project with Env to delete'",
            ],
        )
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
            pytest.fail("Project creation from python file failed")
        LOG.info("Success")

        # self._test_project_delete()

    @pytest.mark.skipif(
        LV(CALM_VERSION) < LV("3.5.0") or not DSL_CONFIG.get("IS_VPC_ENABLED", False),
        reason="Overlay Subnets can be used in Calm v3.5.0+ blueprints or VPC is disabled on the setup",
    )
    def test_compile_project_with_vpc_and_overlay_subnets(self):
        """This test will check Project compilation having VPC and
        Overlay subnets"""

        runner = CliRunner()
        LOG.info("Testing 'calm compile project' command")
        result = runner.invoke(
            cli,
            [
                "compile",
                "project",
                "--file={}".format(DSL_PROJECT_WITH_VPC_PATH),
            ],
        )
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
            pytest.fail("Project compilation from python file failed")
        LOG.info("Success")

    def _test_overlay_subnets(self):
        """This is a test to check if the project created consists of overlay subnets"""
        NTNX_ACCOUNT_1 = ACCOUNTS["NUTANIX_PC"][1]
        OVERLAY_SUBNETS = NTNX_ACCOUNT_1["OVERLAY_SUBNETS"][0]["NAME"]

        project_data = get_project(self.dsl_project_name)
        assert OVERLAY_SUBNETS in str(project_data)
