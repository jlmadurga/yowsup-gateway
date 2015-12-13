# -*- coding: utf-8 -*-
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback, \
    EventCallback
from yowsup.layers.protocol_messages.protocolentities import \
    TextMessageProtocolEntity
import logging
from yowsup.layers.network import YowNetworkLayer
from yowsup_gateway.results import SuccessfulResult
from yowsup_gateway.exceptions import ConnectionError
from functools import wraps


logger = logging.getLogger(__name__)

def connection_required(f):
    @wraps(f)
    def decorated_function(self, *args, **kwargs):
        if not self.connected:
            raise ConnectionError("%s needs to be connected" % f.__name__)
        return f(self, *args, **kwargs)
    return decorated_function

class ExitGateway(Exception):
    """
    Raised by GatewayLayer to exit stack loop
    """
    pass


class GatewayLayer(YowInterfaceLayer):    
    """
    Layer to be on the top of the Yowsup Stack. 
    :ivar bool connected: connected or not connected to whatsapp
    :ivar list ack_pending: list with incoming ack messages to receive
    :ivar list inbox: list of received messages from whatsapp
    :ivar list outbox: list of sent messages to whatsapp
    """

    CALLBACK_EVENT = "org.openwhatsapp.yowsup.prop.callback"
    PROP_MESSAGES = "org.openwhatsapp.yowsup.prop.sendclient.queue"
    EVENT_SEND_MESSAGES = "org.openwhatsapp.yowsup.prop.queue.sendmessage"
    
    def __init__(self):

        super(GatewayLayer, self).__init__()
        self.ack_pending = []
        self.connected = False
        self.inbox = []
        self.outbox = []
        
    def _get_event_callback(self):
        return self.getProp(self.CALLBACK_EVENT, None)
      
    def _send_protocol_entity(self, protocol_entity):
        self.outbox.append(protocol_entity)
        self.toLower(protocol_entity)
        
    def _receive_protocol_entity(self, protocol_entity):
        self.inbox.append(protocol_entity)
        
    def check_pending_flow(self):
        if self.ack_pending:
            pending_acks = [pending_ack for pending_ack in self.ack_pending]
            raise ConnectionError("Pending incoming Ack messages not received \
                                    %s" % str(pending_acks))

    @ProtocolEntityCallback("success")
    def on_success(self, success_protocol_entity):
        """
        Callback when there is a successful connection to whatsapp server
        """
        logger.info("Logged in")
        self.connected = True
        callback_event = self._get_event_callback()
        if callback_event:
            self.onEvent(callback_event)
            
    @ProtocolEntityCallback("failure")
    def on_failure(self, entity):
        """
        Callback function when there is a failure in a connection to whatsapp 
        server
        """
        logger.error("Login failed, reason: %s" % entity.getReason())
        self.connected = False
       
    @ProtocolEntityCallback("ack")
    @connection_required
    def on_ack(self, entity):
        """
        Callback function when receiving an ack for a sent message from 
        whatsapp
        """
        self.inbox.append(entity)
        # if the id match ack_pending id, then pop the id of the message out
        if entity.getId() in self.ack_pending:
            self.ack_pending.pop(self.ack_pending.index(entity.getId()))
            logger.info("Message sent:" + str(entity.getId()))
             
        if not len(self.ack_pending):
            logger.info("Disconnect")
            self.disconnect()
        
    @ProtocolEntityCallback("message")
    @connection_required
    def on_message(self, message_protocol_entity):
        """
        Callback function when receiving message from whatsapp server
        """
        self._receive_protocol_entity(message_protocol_entity)
        self._send_protocol_entity(message_protocol_entity.ack())  
            
    @ProtocolEntityCallback("receipt")
    @connection_required
    def on_receipt(self, receipt_protocol_entity):
        """
        Callback function when receiving receipt message from whatsapp
        """
        self._receive_protocol_entity(receipt_protocol_entity)
        self._send_protocol_entity(receipt_protocol_entity.ack())
        
    @EventCallback(EVENT_SEND_MESSAGES)
    @connection_required
    def on_send_messages(self, yowLayerEvent):
        """
        Callback function when receiving event to send messages
        """
        for message in yowLayerEvent.getArg("messages"):
            number, content = message
            if '@' in number:
                message_protocol_entity = \
                    TextMessageProtocolEntity(content, to=number)
            elif '-' in number:
                message_protocol_entity = \
                    TextMessageProtocolEntity(content, to="%s@g.us" % number)
            else:
                message_protocol_entity = \
                    TextMessageProtocolEntity(content,
                                              to="%s@s.whatsapp.net" % number)
            # append the id of message to ack_pending list
            # which the id of message will be deleted when ack is received.
            self.ack_pending.append(message_protocol_entity.getId())
            self._send_protocol_entity(message_protocol_entity)

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    @connection_required
    def on_disconnected(self, yowLayerEvent):
        """
        Callback function when receiving a disconnection event
        """
        self.connected = False
        self.check_pending_flow()
        self.getStack().result = SuccessfulResult(self.inbox, self.outbox)
        raise ExitGateway()
