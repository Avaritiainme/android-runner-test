import collections
import os.path as op

import pytest
from mock import Mock, call, patch
import time
import paths
import subprocess
from AndroidRunner.MonkeyReplay import MonkeyReplay, MonkeyReplayError
from AndroidRunner.MonkeyRunner import MonkeyRunner, MonkeyRunnerError
from AndroidRunner.MonkeyAdb import MonkeyAdb
from AndroidRunner.Python3 import Python3
from AndroidRunner.Script import Script, ScriptError
from AndroidRunner.Scripts import Scripts
from AndroidRunner.util import ConfigError, FileNotFoundError


class TestScripts(object):
    @pytest.fixture()
    def paths_dict(self, tmpdir):
        paths.CONFIG_DIR = str(tmpdir)

    @pytest.fixture()
    def scripts(self, paths_dict):
        with patch('AndroidRunner.Python3.Python3.__init__', return_value=None):
            test_path = 'test/path/to/script.py'
            test_config = collections.OrderedDict()
            test_config['testscript'] = test_path
            return Scripts(test_config)

    @patch('AndroidRunner.Python3.Python3.__init__')
    def test_experiment_script_init(self, mock, paths_dict):
        mock.return_value = None
        test_path = 'test/path/to/script.py'
        test_config = collections.OrderedDict()
        test_config['testscript'] = test_path

        scripts = Scripts(test_config)
        mock.assert_called_once_with(op.join(paths.CONFIG_DIR, test_path))
        for script in scripts.scripts['testscript']:
            assert type(script) == Python3

    @patch('AndroidRunner.Python3.Python3.__init__')
    def test_python3_interaction_script_init(self, mock, paths_dict):
        mock.return_value = None
        test_path = 'test/path/to/script.py'
        test_config = collections.OrderedDict()
        test_config['type'] = 'python3'
        test_config['path'] = test_path
        test_config_list = list()
        test_config_list.append(test_config)
        interaction_test_config = collections.OrderedDict()
        interaction_test_config['interaction'] = test_config_list
        scripts = Scripts(interaction_test_config)

        mock.assert_called_once_with(op.join(paths.CONFIG_DIR, test_path), 0, None)
        for script in scripts.scripts['interaction']:
            assert type(script) == Python3

    @patch('AndroidRunner.MonkeyReplay.MonkeyReplay.__init__')
    def test_monkeyreplay_interaction_script_init(self, mock, paths_dict):
        mock.return_value = None
        test_path = 'test/path/to/script.py'
        test_config = collections.OrderedDict()
        test_config['type'] = 'monkeyreplay'
        test_config['path'] = test_path
        test_config_list = list()
        test_config_list.append(test_config)
        interaction_test_config = collections.OrderedDict()
        interaction_test_config['interaction'] = test_config_list
        scripts = Scripts(interaction_test_config)

        mock.assert_called_once_with(op.join(paths.CONFIG_DIR, test_path), 0, None, 'monkeyrunner')
        for script in scripts.scripts['interaction']:
            assert type(script) == MonkeyReplay

    @patch('AndroidRunner.MonkeyRunner.MonkeyRunner.__init__')
    def test_monkeyrunner_interaction_script_init(self, mock, paths_dict):
        mock.return_value = None
        test_path = 'test/path/to/script.monkeyrunner'
        test_config = collections.OrderedDict()
        test_config['type'] = 'monkeyrunner'
        test_config['path'] = test_path
        test_config['timeout'] = 100
        test_config['logcat_regex'] = 'teststring'
        test_config_list = list()
        test_config_list.append(test_config)
        interaction_test_config = collections.OrderedDict()
        interaction_test_config['interaction'] = test_config_list
        scripts = Scripts(interaction_test_config)

        mock.assert_called_once_with(op.join(paths.CONFIG_DIR, test_path), 100, 'teststring', 'monkeyrunner', 'monkey_playback.py')
        for script in scripts.scripts['interaction']:
            assert type(script) == MonkeyRunner

    def test_unknown_interaction_script_init(self, paths_dict):
        test_path = 'test/path/to/script.py'
        test_config = collections.OrderedDict()
        test_config['type'] = 'unknownScript'
        test_config['path'] = test_path
        test_config_list = list()
        test_config_list.append(test_config)
        interaction_test_config = collections.OrderedDict()
        interaction_test_config['interaction'] = test_config_list
        with pytest.raises(ConfigError) as _:
            Scripts(interaction_test_config)

    @patch('AndroidRunner.Script.Script.run')
    def test_run(self, mock, scripts):
        fake_device = Mock()
        scripts.run('testscript', fake_device)
        mock.assert_called_once_with(fake_device)

    @patch('AndroidRunner.Script.Script.run')
    def test_run_empty_script_set(self, mock, scripts):
        fake_device = Mock()
        scripts.run('testscript1', fake_device)
        assert mock.call_count == 0


class TestPython3(object):
    @pytest.fixture()
    def script_path(self, tmpdir):
        temp_file = tmpdir.join("script.py")
        temp_file.write('\n'.join(['from time import sleep',
                                   'def main(device_id):\n',
                                   '    sleep(0.5)\n'
                                   '    return "succes"']))
        return str(temp_file)

    @pytest.fixture()
    def init_error_script_path(self, tmpdir):
        temp_file = tmpdir.join("script.py")
        temp_file.write('\n'.join(['from time import sleep\n',
                                   'import nonexisting\n',
                                   'def main(device_id):\n',
                                   '    raise NotImplementedError\n']))
        return str(temp_file)

    def test_python3_error_init(self, init_error_script_path):
        with pytest.raises(ImportError):
            Python3(init_error_script_path)

    def test_python3_execute_script(self, script_path):
        fake_device = Mock()
        assert Python3(script_path).execute_script(fake_device) == 'succes'


class TestMonkeyReplay(object):
    @pytest.fixture()
    def script_path(self, tmpdir):
        temp_file = tmpdir.join("script")
        temp_file.write('\n'.join(['{"type": "hello"}',
                                   '{"type": "dont"}']))
        return str(temp_file)

    def test_replay_init(self, script_path):
        replay = MonkeyReplay(script_path, monkeyrunner_path="test/monkey")
        assert replay.path == script_path
        assert replay.monkeyrunner == 'test/monkey'

    @patch('subprocess.Popen')
    def test_monkeyreplay_execute_script_succes(self, mock, script_path):
        subprocess_mock = Mock()
        subprocess_mock.communicate.return_value = [b'output', b'error']
        subprocess_mock.wait.return_value = 0
        mock.return_value = subprocess_mock
        monkey_path = '/usr/lib/android-sdk/tools/monkeyrunner'
        monkey_command = "{} -plugin jyson-1.0.2.jar MonkeyPlayer/replayLogic.py {}".format(monkey_path,
                                                                                            script_path).split(" ")
        assert MonkeyReplay(script_path, monkeyrunner_path=monkey_path).execute_script(Mock()) == 0
        mock.assert_called_once_with(monkey_command, cwd=paths.ROOT_DIR, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    @patch('subprocess.Popen')
    def test_monkeyreplay_execute_script_error(self, mock, script_path):
        subprocess_mock = Mock()
        subprocess_mock.communicate.return_value = [b'error_output', b'fake_error']
        subprocess_mock.wait.return_value = 1
        mock.return_value = subprocess_mock
        monkey_path = '/usr/lib/android-sdk/tools/monkeyrunner'
        with pytest.raises(Exception) as expect_ex:
            MonkeyReplay(script_path, monkeyrunner_path=monkey_path).execute_script(Mock())
        assert expect_ex.type == MonkeyReplayError
        assert str(expect_ex.value) == 'error_output'


class TestMonkeyrunner(object):
    @pytest.fixture()
    def script_path(self, tmpdir):
        temp_file = tmpdir.join("script")
        temp_file.write('\n'.join(['{"type": "hello"}',
                                   '{"type": "dont"}']))
        return str(temp_file)

    def test_init_runner(self, script_path):
        monkey_path = '/usr/lib/android-sdk/tools/monkeyrunner'
        runner = MonkeyRunner(script_path, monkeyrunner_path=monkey_path)
        assert type(runner) == MonkeyRunner
        assert runner.monkeyrunner_path == monkey_path

    @patch('subprocess.run')
    def test_execute_script_succes(self, mock_subprocess, script_path):
        monkey_path = '/usr/lib/android-sdk/tools/monkeyrunner'
        monkey_playback_path = '/usr/lib/android-sdk/tools/swt/monkeyrunner/scripts/monkey_playback.py'
        mock_subprocess.return_value = Mock()
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = b'success'
        runner_return = MonkeyRunner(script_path, monkeyrunner_path=monkey_path, monkey_playback_path=monkey_playback_path).execute_script(Mock())
        mock_subprocess.assert_called_once_with([monkey_path, monkey_playback_path, script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert runner_return == 0

    @patch('subprocess.run')
    def test_execute_script_error(self, mock_subprocess, script_path):
        monkey_path = '/usr/lib/android-sdk/tools/monkeyrunner'
        monkey_playback_path = '/usr/lib/android-sdk/tools/swt/monkeyrunner/scripts/monkey_playback.py'
        mock_subprocess.return_value = Mock()
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = b'SocketException'
        with pytest.raises(Exception) as expect_ex:
            MonkeyRunner(script_path, monkeyrunner_path=monkey_path, monkey_playback_path=monkey_playback_path).execute_script(Mock())
        assert expect_ex.type == MonkeyRunnerError
        assert str(expect_ex.value) == 'SocketException'


class TestMonkeyAdb(object):
    @pytest.fixture()
    def script_path(self, tmpdir):
        temp_file = tmpdir.join("script")
        temp_file.write('{"type": "touch", "x": 10, "y": 20, "down": 0, "up": 10}')
        return str(temp_file)

    def test_init(self, script_path):
        runner = MonkeyAdb(script_path)
        assert runner.path == script_path

    @patch('AndroidRunner.MonkeyAdb.time.sleep')
    def test_execute_script(self, mock_sleep, script_path):
        device = Mock()
        MonkeyAdb(script_path).execute_script(device)
        device.shell.assert_called_once_with('input tap 10 20')


class TestScript(object):
    @pytest.fixture()
    def script_path(self, tmpdir):
        temp_file = tmpdir.join("script.py")
        temp_file.write('\n'.join(['from time import sleep',
                                   'def main(device_id):\n',
                                   '    sleep(0.5)\n'
                                   '    return "succes"']))
        return str(temp_file)

    @pytest.fixture()
    def error_script_path(self, tmpdir):
        temp_file = tmpdir.join("script.py")
        temp_file.write('\n'.join(['from time import sleep',
                                   'def main(device_id):\n',
                                   '    raise NotImplementedError\n']))
        return str(temp_file)

    @pytest.fixture()
    def script(self, script_path):
        return Script(script_path)

    def test_logcat_regex(self, script):
        fake_device = Mock()
        test_queue = Mock()
        manager = Mock()

        manager.fake_device_mock = fake_device
        manager.test_queu_mock = test_queue

        script.mp_logcat_regex(test_queue, fake_device, 'test_regex')

        expected_calls = [call.fake_device_mock.logcat_regex('test_regex'), call.test_queu_mock.put('logcat')]

        assert manager.mock_calls == expected_calls

    def test_script_not_found_init(self):
        with pytest.raises(FileNotFoundError):
            Script('fake/file/path')

    def test_script_run_normal(self, script_path):
        fake_device = Mock()
        assert Python3(script_path).run(fake_device) == 'script'

    def test_script_run_timeout(self, script_path):
        fake_device = Mock()
        assert Python3(script_path, timeout=10).run(fake_device) == 'timeout'

    def test_script_run_logcat(self, script_path):
        fake_device = Mock()
        assert Python3(script_path, logcat_regex='').run(fake_device) == 'logcat'

    def test_script_error(self, error_script_path):
        fake_device = Mock()
        with pytest.raises(ScriptError) as expect_ex:
            Python3(error_script_path).run(fake_device)
        assert 'NotImplementedError' in str(expect_ex.value)

    def test_script_mp_run(self, script_path):
        fake_device = Mock()
        test_queue = Mock()
        test_script = Python3(script_path)
        test_script.mp_run(test_queue, fake_device)

        test_queue.put.assert_called_once_with('script')

    def test_script_mp_run_error(self, error_script_path):
        fake_device = Mock()
        test_queue = Mock()
        test_script = Python3(error_script_path)
        test_script.mp_run(test_queue, fake_device)
        assert test_queue.put.call_count == 2
        assert 'NotImplementedError' in str(test_queue.put.call_args_list)
        assert 'script' in str(test_queue.put.call_args_list[1][0])

    @patch("time.sleep")
    def test_mp_logcat_regex_one_iteration(self, sleep, script_path):
        fake_device = Mock()
        fake_device.logcat_regex.side_effect = [False, True]
        test_queue = Mock()
        test_script = Python3(script_path)
        test_script.mp_logcat_regex(test_queue, fake_device, "Test")

        sleep.assert_called_once_with(1)
        test_queue.put.assert_called_once_with("logcat")
