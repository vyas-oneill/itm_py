import queue
import threading
import ipaddress
import dill
import inspect

from ItmPy import ItmMessages, ItmNetworkStack
from ItmPy.ItmMessages import AcquisitionRequestMessage, AcquisitionResponseMessage
from ItmPy.ItmNetworkStack.ItmPackets import *


class ItmAgent:
    _name = ""
    _scopes = {
        "situational_awareness": None,
        "logical_image": None,
        "agency": None
    }
    _network_stack = None
    _interface = ""
    _local_ip = None
    _netmask = None
    _itmp_port = None

    _waiting_member = None
    _wait_event = None

    def __init__(self, name="", scopes=None, interface="", local_ip=None, netmask=None, itmp_port=None, promiscuous_mode=False):
        self._name = name
        self._interface = interface
        self._local_ip = local_ip
        self._itmp_port = itmp_port
        self._netmask = netmask
        if scopes is not None:
            self._scopes = scopes

        print(f"Starting network server for agent {self._name} {local_ip}:{itmp_port}...")
        self._network_stack = ItmNetworkStack.ItmNetworkStack(interface=interface, local_ip=local_ip,
                                                              netmask=netmask, itmp_port=itmp_port,
                                                              promiscuous_mode=promiscuous_mode)
        self._network_stack.start()
        print(f"{self._name} network server up.")

    """
        Returns the scope given by scope_name
    """
    def __getitem__(self, scope_name):
        return self._scopes[scope_name]

    def _enqueue_outgoing_message(self, message):
        return self._network_stack.outgoing_message_queue.put(message)

    def _dequeue_incoming_message(self):
        return self._network_stack.incoming_message_queue.get(block=False)

    def _wait_for_resolution(self, scope_name, member_name, timeout=None):
        # Register to wait
        self._wait_event = threading.Event()
        self._waiting_member = f"{scope_name}.{member_name}"

        # Wait
        if timeout is not None:
            self._wait_event.wait(timeout)
        else:
            self._wait_event.wait()

        # Clean up
        self._wait_event = None
        self._waiting_member = None

    """
    Attempts to acquire the supplied member in the supplied scope from the destination agent (can be broadcast)
    If timeout is set to None, blocks until the request is satisfied
    Returns True if successfully able to acquire the member, otherwise False
    Must not be called from the agent main loop thread or will block indefinitely
    """
    def itm_acquire(self, destination, scope_name, member_name, timeout=None):
        outgoing_msg = IP(src=self._local_ip, dst=destination) / \
                       UDP(sport=self._itmp_port, dport=self._itmp_port) / \
                       ItmPacket(operation=int(ITM_OPERATIONS.inverse['Acquisition_Request'])) / \
                       ItmAcquisitionRequestPacket(scope=scope_name, member_name=member_name)

        self._enqueue_outgoing_message(outgoing_msg)
        self._wait_for_resolution(scope_name=scope_name, member_name=member_name, timeout=timeout)
        return self._scopes[scope_name].has_member(member_name)

    def get_local_address(self):
        return self._local_ip

    def get_port(self):
        return self._itmp_port

    def get_broadcast_address(self):
        my_network = ipaddress.ip_network(f"{self._local_ip}/{self._netmask}", strict=False) # strict=False - Mask out host bits
        return str(my_network.broadcast_address)

    def get_name(self):
        return self._name

    def handle_hardware_requirements(self):
        pass

    def process_incoming_communications(self):
        try:
            incoming_msg = self._dequeue_incoming_message()
            if IP in incoming_msg and ItmPacket in incoming_msg:
                # Need IP for addressing information and ItmPacket for Itm operations

                # Check type of message and process it accordingly
                if ItmAcquisitionRequestPacket in incoming_msg:
                    self._process_acquisition_request(incoming_msg)
                elif ItmAcquisitionResponsePacket in incoming_msg:
                    self._process_acquisition_response(incoming_msg)

                else:
                    print(f"Warning: received ItmPacket with unknown operation {incoming_msg[ItmPacket].operation}. Ignoring.")
            else:
                pass  # Ignore non-ItmPacket messages

        except queue.Empty:
            # Ignore when no messages are in the queue
            # and continue to loop until there are messages in the queue
            pass

    def situational_awareness(self):
        pass

    def logical_image(self):
        pass

    def agency(self):
        pass

    def process_outgoing_communications(self):
        pass

    def _process_acquisition_request(self, request):
        scope = request[ItmAcquisitionRequestPacket].scope.decode('utf-8')
        member_name = request[ItmAcquisitionRequestPacket].member_name.decode('utf-8')

        if scope in self._scopes.keys() and self._scopes[scope].has_member(member_name):
            # Unbind methods
            f = self._scopes[scope].__getattribute__(member_name)
            serialised = None
            if getattr(f, '__self__', None) is not None:
                serialised = dill.dumps(f.__func__)
            else:
                serialised = dill.dumps(f)

            response = self._network_stack.build_response_transport_layer(request) /\
                ItmPacket(operation=ITM_OPERATIONS.inverse["Acquisition_Response"],
                          interaction_id=request[ItmPacket].interaction_id) /\
                ItmAcquisitionResponsePacket(scope=scope,
                                             member_name=member_name,
                                             serialised=serialised
                                             )
            self._enqueue_outgoing_message(response)
        else:
            print(f"Received request for unknown member {scope}.{member_name}")

    def _process_acquisition_response(self, response):
        scope = response.scope.decode('utf-8')
        member_name = response.member_name.decode('utf-8')
        serialised = response.serialised

        self._scopes[scope].__setattr__(member_name, dill.loads(serialised).__get__(self._scopes[scope]))
        if self._waiting_member == f"{scope}.{member_name}":
            self._wait_event.set()

    def agent_main_loop(self):
        print(f"{self._name} is starting the agent main loop...")
        while True:
            self.handle_hardware_requirements()
            self.process_incoming_communications()
            self.situational_awareness()
            self.logical_image()
            self.agency()
            self.process_outgoing_communications()

        self._network_stack.stop()
