from ItmPy import *
from scapy.all import *
from ItmPy.ItmNetworkStack.ItmPackets import *


class ItmNetworkObserver(ItmAgent):
    _verbose = False

    def __init__(self, name, interface=None, local_ip=None, itmp_port=None, verbose=False):
        if verbose is not None:
            self._verbose = verbose

        super().__init__(name=name, interface=interface, local_ip=local_ip, itmp_port=itmp_port, promiscuous_mode=True)

    def process_incoming_communications(self):
        try:
            log_str = ""
            incoming_msg = self._dequeue_incoming_message()
            if IP in incoming_msg and ItmPacket in incoming_msg:
                # Need IP for addressing information and ItmPacket for Itm operations

                log_str = f"{incoming_msg[IP].src} > {incoming_msg[IP].dst}: "
                # Check type of message and process it accordingly
                if ItmAcquisitionRequestPacket in incoming_msg:
                    log_str = log_str + f"ACQUIRE {incoming_msg[ItmAcquisitionRequestPacket].scope.decode('utf-8')}.{incoming_msg[ItmAcquisitionRequestPacket].member_name.decode('utf-8')}"
                elif ItmAcquisitionResponsePacket in incoming_msg:
                    log_str = log_str + f"RESPONSE [ACQUIRE {incoming_msg[ItmAcquisitionResponsePacket].scope.decode('utf-8')}.{incoming_msg[ItmAcquisitionResponsePacket].member_name.decode('utf-8')}]"
                else:
                    log_str = log_str + f"ItmPacket with unknown operation {incoming_msg[ItmPacket].operation}."
            elif self._verbose:
                log_str = log_str + incoming_msg.show(dump=True)

            print(log_str)
        except queue.Empty:
            # Ignore when no messages are in the queue
            # and continue to loop until there are messages in the queue
            pass

def main():
    agent = ItmNetworkObserver("MAS Observer", interface="Software Loopback Interface 1", local_ip="127.0.0.99", itmp_port=33108)

    agent_thread = threading.Thread(target=agent.agent_main_loop)
    agent_thread.start()

    agent_thread.join()

if __name__ == "__main__":
    main()