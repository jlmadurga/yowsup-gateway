#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_gateway_layer
----------------------------------

Tests for `yowsup_gateway` layer.
"""

import unittest
import time
from yowsup.layers import YowProtocolLayerTest
from yowsup_gateway.layer import GatewayLayer
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import IncomingReceiptProtocolEntity
from yowsup.layers import YowLayerEvent
from yowsup.layers.protocol_acks.protocolentities.test_ack_incoming import entity as incomingAckEntity
from yowsup.layers.network import YowNetworkLayer
from yowsup_gateway.exceptions import ConnectionError
from yowsup_gateway.layer import ExitGateway
from yowsup_gateway import YowsupGateway
from . import success_protocol_entity
try:
    import Queue
except ImportError:
    import queue as Queue

class DummyStack(YowsupGateway):
    def __init__(self):
        self.detached_queue = Queue.Queue()
        self.result = None
        self._props = {}
        

class GatewayLayerTest(YowProtocolLayerTest, GatewayLayer):
    
    def setUp(self):
        GatewayLayer.__init__(self)
        self.connected = True
        self.setStack(DummyStack())
    
    def tearDown(self):
        pass
    
    def send_message(self):
        content = "Hello world"
        number = "341111111"
        message = (number, content)
        self.onEvent(YowLayerEvent(GatewayLayer.EVENT_SEND_MESSAGES, messages=[message]))
        return message
    
    def receive_ack(self):
        incoming_ack_entity = incomingAckEntity
        self.ack_pending.append(incoming_ack_entity.getId())
        self.receive(incoming_ack_entity)
        return incoming_ack_entity
    
    def receive_message(self):
        content = "Received message"
        jid = "bbb@s.whatsapp.net"
        msg = TextMessageProtocolEntity(content, _from=jid)
        self.receive(msg)
        return msg
    
    def receive_receipt(self):
        receipt = IncomingReceiptProtocolEntity("123", "sender", int(time.time()))
        self.receive(receipt)
        return receipt    
    
    def test_connection_successful(self):
        self.connected = False
        self.on_success(success_protocol_entity())
        self.assertTrue(self.connected)

    def test_connection_failure(self):
        self.connected = False
        self.assertFalse(self.connected)
    
    def test_send_message_ok(self):
        message = self.send_message()
        msg_sent = self.lowerSink.pop()
        self.assertEqual(msg_sent.getBody(), message[1])
        self.assertEqual(msg_sent.getTo(), message[0] + "@s.whatsapp.net")
        self.assertEqual(msg_sent.getId(), self.ack_pending.pop())
        self.assertEqual(self.outbox, [msg_sent])
        
    def test_send_message_not_connected(self):
        self.connected = False
        with self.assertRaises(ConnectionError):
            self.send_message()
    
    def test_receive_ack_message_ok(self):
        ack = self.receive_ack()
        self.assertEqual(self.ack_pending, [])
        self.assertEqual(self.inbox, [ack])
        self.assert_broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
    
    def test_receive_message(self):
        msg = self.receive_message()
        self.assertEqual(self.inbox, [msg])
        ack = self.lowerSink.pop()
        self.assertEqual(ack.getId(), msg.getId())
        self.assertEqual(self.outbox, [ack])

    def test_receive_receipt(self):
        receipt = self.receive_receipt()
        self.assertEqual(self.inbox, [receipt])
        ack = self.lowerSink.pop()
        self.assertEqual(ack.getId(), receipt.getId())
        self.assertEqual(self.outbox, [ack])
        
    def test_disconnect(self):
        with self.assertRaises(ExitGateway):
            self.onEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECTED))
        self.assertFalse(self.connected)

if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
