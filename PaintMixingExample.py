from ItmPy import *
from ItmPy.IntelligenceTransferStrategies import *
from ItmPy.IntelligenceTransferStrategies.SimpleStrategy import SimpleStrategy
from ItmPy.ItmScopes import ItmScope
import dill
from scapy.all import *
from ItmPy.ItmNetworkStack.ItmPackets import *


class PaintMixingSAScope(ItmScope):
    def __init__(self, agent, strategy):
        super().__init__(agent=agent, scope_name=f"situational_awareness", strategy=strategy)

    """
        Returns the amount of paint in the given tank name
        Returns None if the tank does not exist on the agent
    """
    def get_paint_tank_sensor_value(self, tank_name):
        try:
            if tank_name in self._agent.paint_tanks.keys():
                return self._agent.paint_tanks[tank_name]
            else:
                return None
        except AttributeError:
            raise ItmException("Agent does not have paint tank sensors")

    def get_mixing_bowl_capacity(self):
        return self._agent.mixing_bowl_capacity

class PaintMixingLIScope(ItmScope):
    def __init__(self, agent, strategy):
        super().__init__(agent=agent, scope_name=f"logical_image", strategy=strategy)

    """
    Converts a color name to (c, m, y, k) tuple
    Each tuple element is between [0, 1] and reflects the proportion of that color, with all elements adding up to 1
    """
    def calculate_primary_color_breakdown(self, color_name):
        if color_name == "cyan":
            return (1, 0, 0, 0)
        elif color_name == "magenta":
            return (0, 1, 0, 0)
        elif color_name == "yellow":
            return (0, 0, 1, 0)
        elif color_name == "black":
            return (0, 0, 0, 1)
        elif color_name == "white":
            return (0.25, 0.25, 0.25, 0.25)
        else:
            return None

    def verify_paint_can_be_mixed(self, cyan_qty, magenta_qty, yellow_qty, black_qty):
        if cyan_qty <= self._agent["situational_awareness"].get_paint_tank_sensor_value('cyan') and \
            magenta_qty <= self._agent["situational_awareness"].get_paint_tank_sensor_value('magenta') and \
            yellow_qty <= self._agent["situational_awareness"].get_paint_tank_sensor_value('yellow') and \
            black_qty <= self._agent["situational_awareness"].get_paint_tank_sensor_value('black'):
            return True
        else:
            return False


class PaintMixingAGScope(ItmScope):
    def __init__(self, agent, strategy):
        super().__init__(agent=agent, scope_name=f"agency", strategy=strategy)

    def add_cyan_paint(self, amount):
        self._agent.add_paint_to_bucket('cyan', amount)

    def add_magenta_paint(self, amount):
        self._agent.add_paint_to_bucket('magenta', amount)

    def add_yellow_paint(self, amount):
        self._agent.add_paint_to_bucket('yellow', amount)

    def add_black_paint(self, amount):
        self._agent.add_paint_to_bucket('black', amount)

    def empty_bucket(self):
        self._agent.empty_bucket()

    def add_water_to_bucket(self):
        self._agent.add_water_to_bucket(self._agent['situational_awareness'].get_mixing_bowl_capacity())

    def mix_paint(self, color_name, amount):
        cyan, magenta, yellow, black = self._agent['logical_image'].calculate_primary_color_breakdown(color_name=color_name)
        # Scale by the amount of paint the user wanted
        cyan, magenta, yellow, black = (cyan*amount, magenta*amount, yellow*amount, black*amount)

        if self._agent['logical_image'].verify_paint_can_be_mixed(cyan_qty=cyan,
                                                                  magenta_qty=magenta,
                                                                  yellow_qty=yellow,
                                                                  black_qty=black):
            self.add_cyan_paint(cyan)
            self.add_magenta_paint(magenta)
            self.add_yellow_paint(yellow)
            self.add_black_paint(black)
            self.empty_bucket()
            self.add_water_to_bucket()
            self.empty_bucket()
        else:
            raise Exception("Insufficient paint to mix.")

class PaintMixingRobotAgent(ItmAgent):
    paint_tanks = {
        'cyan': 1.0,
        'magenta': 1.0,
        'yellow': 1.0,
        'black': 1.0,
    }

    mixing_bowl_capacity = 5

    def __init__(self, name, interface=None, local_ip=None, netmask=None, itmp_port=None):
        super().__init__(name=name, interface=interface,
                         local_ip=local_ip, netmask=netmask, itmp_port=itmp_port)

        self._scopes = {
            'situational_awareness': PaintMixingSAScope(self, strategy=SimpleStrategy()),
            'logical_image': PaintMixingLIScope(self, strategy=SimpleStrategy()),
            'agency': PaintMixingAGScope(self, strategy=SimpleStrategy())
        }

    def empty_bucket(self):
        print("Bucket emptied")

    def add_water_to_bucket(self, amount):
        print(f"{amount}L of water added to bucket")

    def add_paint_to_bucket(self, tank_name, amount):
        self.paint_tanks[tank_name] = self.paint_tanks[tank_name] - amount
        print(f"{tank_name} changed by {amount}.\nTanks now hold {self.paint_tanks}")


def main():
    agent = PaintMixingRobotAgent(name="PaintMixingRobot", interface="Software Loopback Interface 1",
                                  local_ip="127.0.0.1", netmask=8, itmp_port=33108)
    agent_thread = threading.Thread(target=agent.agent_main_loop)
    agent_thread.start()

    agent["agency"].mix_paint("white", 2)
    agent["agency"].dilute_paint("white", 2, 4)

    agent_thread.join()

if __name__ == "__main__":
    main()