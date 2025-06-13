import json
import time
from .Script import Script

class MonkeyAdbError(Exception):
    pass

class MonkeyAdb(Script):
    """Replay a monkey.txt file using adb shell input commands."""
    def execute_script(self, device, *args, **kwargs):
        super(MonkeyAdb, self).execute_script(device, *args, **kwargs)
        with open(self.path, 'r') as f:
            prev_up = 0
            for line in f:
                if not line.strip():
                    continue
                action = json.loads(line)
                wait = max(0, (float(action.get('down', 0)) - float(prev_up))/1000)
                if wait:
                    time.sleep(wait)
                if action['type'] == 'touch':
                    device.shell('input tap %s %s' % (action['x'], action['y']))
                    duration = (float(action.get('up', 0)) - float(action.get('down',0)))/1000
                    if duration:
                        time.sleep(duration)
                elif action['type'] == 'drag':
                    p1, p2 = action['points']
                    duration = int(float(action.get('up',0)) - float(action.get('down',0)))
                    device.shell('input swipe %s %s %s %s %s' % (
                        p1['x'], p1['y'], p2['x'], p2['y'], duration))
                elif action['type'] == 'press':
                    for k in action['keys']:
                        device.shell('input keyevent %s' % k['key'])
                    duration = (float(action.get('up',0)) - float(action.get('down',0)))/1000
                    if duration:
                        time.sleep(duration)
                elif action['type'] == 'text':
                    device.shell("input text '%s'" % action['value'])
                    duration = (float(action.get('up',0)) - float(action.get('down',0)))/1000
                    if duration:
                        time.sleep(duration)
                else:
                    raise MonkeyAdbError('Unknown action type %s' % action['type'])
                prev_up = float(action.get('up', prev_up))
        return 0
