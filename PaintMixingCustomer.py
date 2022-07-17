import threading

from ItmPy import ItmAgent
from ItmPy.ItmScopes import ItmScope


class PaintMixingCustomerAGScope(ItmScope):
    def __init__(self, agent, strategy):
        super().__init__(agent=agent, scope_name="agency", strategy=strategy)

    def dilute_paint(self, color_name, paint_amount, dilute_amount):
        cyan, magenta, yellow, black = self._agent['logical_image'].calculate_primary_color_breakdown(color_name=color_name)
        # Scale by the amount of paint the user wanted
        cyan, magenta, yellow, black = (cyan * paint_amount, magenta * paint_amount, yellow * paint_amount, black * paint_amount)

        if self._agent['logical_image'].verify_paint_can_be_mixed(cyan_qty=cyan,
                                                                  magenta_qty=magenta,
                                                                  yellow_qty=yellow,
                                                                  black_qty=black):
            self.add_cyan_paint(cyan)
            self.add_magenta_paint(magenta)
            self.add_yellow_paint(yellow)
            self.add_black_paint(black)
            self._agent.add_water_to_bucket(amount=dilute_amount)
            self.empty_bucket()
            self.add_water_to_bucket()
            self.empty_bucket()
        else:
            raise Exception("Insufficient paint to mix.")

class PaintMixingCustomer(ItmAgent):
    def __init__(self, name, interface=None, local_ip=None, netmask=None, itmp_port=None):
        super().__init__(name=name, interface=interface,
                         local_ip=local_ip, netmask=netmask, itmp_port=itmp_port)

        self._scopes = {
            'agency': PaintMixingCustomerAGScope(self, strategy=None)
        }


def main():
    customer = PaintMixingCustomer(name="PaintMixingCustomer", interface="Software Loopback Interface 1",
                                   local_ip="127.0.0.2", netmask=8, itmp_port=33108)
    customer_thread = threading.Thread(target=customer.agent_main_loop)
    customer_thread.start()

    customer_thread.join()

if __name__=="__main__":
    main()