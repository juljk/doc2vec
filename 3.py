import os
import sys
import signal
from datetime import datetime

sys.path.append('ThriftAutoGenApi')

from TVKeyAutomaticTestFramework.TestConfig import Args
from TVKeyAutomaticTestFramework.test_runner import TestRunner
from TVKeyAutomaticTestFramework.tv_communicator import TVCommunicator
from TVKeyAutomaticTestFramework.channel_list_config import ChannelListConfig
from TVKeyAutomaticTestFramework.configs_parser import ConfigParser
import TVKeyAutomaticTestFramework.Logging as Logging
from utils.utils import restart_tv
from utils.framework_info import FrameworkInfo
from utils.profile_installation_utils import delete_operator_profile
from managers.framework_log.logs_manager import FrameworkLogsManager
from managers.key_control.key_control_manager import KeyControlManager
from constants import TV_MOCK_IP_ADDRESS


main_logger = Logging.getLogger('main')

is_signal = False


def signal_handler(signum, _frame):
    """ Function handles exit signals """
    import pdb
    global is_signal
    is_signal = True
    pdb.set_trace()


def main():
    """ Function - entry point to our framework """
    framework_info = FrameworkInfo()
    framework_info.update_framework_info(status='Preparation', iteration=0, test_name=None)

    is_exception = False
    is_system_exit = False
    config = ConfigParser()
    test_run_configs = config.get_configs()
    Logging.AddHandler(stream=sys.stdout, level=config.logging_level)
    is_repeated = test_run_configs.pop('is_repeated')
    test_runner = TestRunner(**test_run_configs)
    tv_communicator = TVCommunicator()
    tv_communicator.start_server_in_thread()
    framework_info.update_framework_info(status='Server started')

    if not tv_communicator.wait_until_framework_is_ready(60):
        framework_info.update_framework_info(status='Failed to connect')
        raise Exception("Cannot connect to the TV")

    tv_ip = tv_communicator.get_tv_info().ip

    if tv_ip == TV_MOCK_IP_ADDRESS:
        config.is_tv = False

    framework_info.update_framework_info(status='Client started')
    framework_info.save_tv_info(ip=tv_ip)
    tv_communicator.check_connectivity()
    framework_info.update_framework_info(status='Successfully tested connection')

    #  Getting all channels from the TV and match them with channel list config
    channel_list = tv_communicator.get_control_api().GetChannelList()
    ChannelListConfig().set_channels_lcn(channel_list)

    if config.is_tv:
        current_time = tv_communicator.get_control_api().GetTime().unixSeconds
        date_time_str = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S")
        main_logger.info("TV date and time: {}".format(date_time_str))
        os.system("sudo timedatectl set-ntp false && sudo date --set=\"{}\"".format(date_time_str))
        tv_communicator.tv_mounted_drive = tv_communicator.shell_command_with_stdout(
            'ls /opt/media/')[1].split('\n')[0]

    log_manager = FrameworkLogsManager()
    framework_info.init_test_run()

    _iteration = 0
    while is_repeated(_iteration) and is_signal is not True:
        _iteration += 1
        log_manager.init_test_run_logs()
        Args.Set('iteration', _iteration)
        if Args.GetBool('pdb'):
            signal.signal(signal.SIGQUIT, signal_handler)

        framework_info.update_framework_info(status='Running', iteration=_iteration)

        if config.reset_option == 'test_run':
            main_logger.info("Restarting the TV")
            restart_tv()

        main_logger.info("Iteration --- {}".format(_iteration))
        try:
            test_runner.run_tests()
            framework_info.update_framework_info(status='Finished', test_name=None)

            if config.perform_profile_installation:
                delete_operator_profile(KeyControlManager())

        except (KeyboardInterrupt, SystemExit):
            framework_info.update_framework_info(status='SystemExit', test_name=None)
            log_manager.save_test_logs()
            is_system_exit = True
            is_exception = True
        except Exception:
            framework_info.update_framework_info(status='Interrupted', test_name=None)
            log_manager.save_test_logs()
            is_exception = True
        finally:
            tests_info = framework_info.get_last_tests_info()
            report = test_runner.get_tests_report(tests_info)

            main_logger.info(report)
            log_manager.save_test_run_result(report, _iteration)

            if (is_exception and is_system_exit) or test_runner.tests_result.shouldStop:
                log_manager.add_time_to_test_run_folder()
                raise SystemExit

    log_manager.add_time_to_test_run_folder()


if __name__ == '__main__':
    main()
