#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_yowsup_gateway
----------------------------------

Tests for `yowsup_gateway` module.
"""
import unittest
import inspect
import threading
from yowsup.layers.interface import YowInterfaceLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers import YowLayerEvent, EventCallback
from tests import success_protocol_entity, failure_protocol_entity, text_message_protocol_entity, \
    ack_incoming_protocol_entity, receipt_incoming_protocol_entity
from yowsup_gateway import YowsupGateway
from yowsup_gateway.layer import GatewayLayer
from yowsup_gateway.exceptions import AuthenticationError, ConfigurationError, ConnectionError
from yowsup.layers.auth.autherror import AuthError
    
class SendProtocolEntityCallback(object):
    """
    Decorate callback for handling send protoocol entities
    """
    def __init__(self, entityType):
        self.entityType = entityType

    def __call__(self, fn):
        fn.send_entity_callback = self.entityType
        return fn

class CoreLayerMock(YowInterfaceLayer):
    """
    Mock layer to simulate core layers
    """
    
    def __init__(self, error_auth=False, error_ack=False):
        super(CoreLayerMock, self).__init__()
        self.send_entity_callbacks = {}
        self.error_auth = error_auth
        self.error_ack = error_ack
        self.connected = False
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        for m in members:
            if hasattr(m[1], "send_entity_callback"):
                fname = m[0]
                fn = m[1]
                self.send_entity_callbacks[fn.send_entity_callback] = getattr(self, fname)
                
    def send(self, entity):
        if not self.processIqRegistry(entity):
            entityType = entity.getTag()
            if entityType in self.send_entity_callbacks:
                self.send_entity_callbacks[entityType](entity)
            else:
                self.toLower(entity)

    @EventCallback(YowNetworkLayer.EVENT_STATE_CONNECT)
    def on_connect(self, event):
        if self.error_auth:
            self.connected = False
            protocol_entity = failure_protocol_entity()
        else:
            self.connected = True
            protocol_entity = success_protocol_entity()
        self.toUpper(protocol_entity)
        if not self.connected:
            raise AuthError()

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECT)
    def on_disconnect(self, event):
        self.connected = False
        self.emitEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECTED, 
                                     reason="Connection closed", 
                                     detached=True))
        return True
    
    @SendProtocolEntityCallback("message")
    def on_message(self, message_protocol_entity):
        if not self.error_ack:
            self.toUpper(ack_incoming_protocol_entity(message_protocol_entity))
    
    @SendProtocolEntityCallback("ack")
    def on_ack(self, ack_protocol_entity):
        pass
    
    @SendProtocolEntityCallback("entity")
    def on_receipt(self, receipt_protocol_entity):
        pass
    
    def receive_message(self):
        self.toUpper(text_message_protocol_entity())
        
    def receive_ack(self):
        self.toUpper(ack_incoming_protocol_entity())
        
    def receive_receipt(self):
        self.toUpper(receipt_incoming_protocol_entity())
        
class FunctionalTests(unittest.TestCase):
    
    def setUp(self):
        self.stack = YowsupGateway(("341111111", "password"))
        stackClassesArr = (GatewayLayer, CoreLayerMock)   
        self.stack._YowStack__stack = stackClassesArr[::-1]
        self.stack._YowStack__stackInstances = []
        self.stack._YowStack__props = {}
        self.stack._construct()
        self.mock_layer = self.stack._YowStack__stackInstances[0]
        self.gateway_layer = self.stack._YowStack__stackInstances[1]
        self.number = "341234567"
        self.content = "message test"
        self.message = (self.number, self.content)
        
    def test_configuration_layer_error(self):
        class IncorrectLayer(object):
            pass
        with self.assertRaises(ConfigurationError):
            YowsupGateway(("341111111", "password"), False, (IncorrectLayer,))

    def test_auth_error(self):
        self.mock_layer.error_auth = True
        with self.assertRaises(AuthenticationError):
            self.stack.send_messages([self.message])
        self.assertFalse(self.gateway_layer.connected)
        
    def test_send_text_message(self):
        result = self.stack.send_messages([self.message])
        self.assertTrue(result.is_success)
        self.assertEqual(1, len(result.inbox))
        self.assertEqual(1, len(result.outbox))
        out_message = result.outbox[0]
        in_ack = result.inbox[0]
        self.assertEqual(out_message.getBody(), self.content)
        self.assertEqual(out_message.getTo(), self.number + "@s.whatsapp.net")
        self.assertEqual(out_message.getType(), "text")
        self.assertEqual(out_message.getId(), in_ack.getId())
        self.assertEqual(out_message.getTo(), in_ack._from)
        self.assertEqual(out_message.getType(), in_ack.getClass())
        
    def test_send_text_message_not_ok(self):
        self.mock_layer.error_ack = True
        with self.assertRaises(ConnectionError):
            self.stack.send_messages([self.message])
        
    def _queue_thread(self, fn, *args, **kwargs):
        while not self.gateway_layer.connected:
            pass
        fn(*args, **kwargs)
        
    def _test_receive(self, receive_action):
        self.input_thread = threading.Thread(target=self._queue_thread, args=(receive_action,))
        self.input_thread.daemon = True
        self.input_thread.start()
        result = self.stack.receive_messages()
        self.assertTrue(result.is_success)
        return result
    
    def test_receive_text_message(self):
        result = self._test_receive(self.mock_layer.receive_message)
        self.assertEqual(1, len(result.inbox))
        self.assertEqual(1, len(result.outbox))
        in_message = result.inbox[0]
        out_receipt = result.outbox[0]
        message = text_message_protocol_entity()
        self.assertEqual(in_message.getBody(), message.getBody())
        self.assertEqual(in_message.getFrom(), message.getFrom())
        self.assertEqual(in_message.getId(), out_receipt.getId())
        
    def test_receive_receipt(self):
        result = self._test_receive(self.mock_layer.receive_receipt)
        self.assertEqual(1, len(result.inbox))
        self.assertEqual(1, len(result.outbox))
        in_receipt = result.inbox[0]
        out_ack = result.outbox[0]
        receipt = receipt_incoming_protocol_entity()
        self.assertEqual(receipt.getId(), in_receipt.getId())
        self.assertEqual(receipt.getFrom(), in_receipt.getFrom())
        self.assertEqual(in_receipt.getId(), out_ack.getId())
        self.assertEqual(in_receipt.getFrom(), out_ack._to)
        self.assertEqual(out_ack.getClass(), "receipt")

if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
