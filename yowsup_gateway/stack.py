# -*- coding: utf-8 -*-
from yowsup.stacks import YowStack
from yowsup_gateway.layer import GatewayLayer, ExitGateway
from yowsup.layers import YowLayerEvent
from yowsup import stacks
from yowsup.layers.auth import AuthError
from yowsup.layers.network import YowNetworkLayer
import asyncore
import time
import logging
from yowsup_gateway.exceptions import AuthenticationError, ConnectionError, ConfigurationError, UnexpectedError
import sys
try:
    import Queue
except ImportError:
    import queue as Queue
    
    
logger = logging.getLogger(__name__)

class YowsupGateway(YowStack):
    """
    Gateway for Yowsup in a client API way
    
    :ivar SuccessfulResult result: List of inbox and outbox messages
    :ivar Queue detached_queue: Queue with callbacks to execute after 
    disconnection
    """
    
    def __init__(self, credentials=("34658463741", "eq5rapFxTSyAceSYHZ7btgb0ono="), encryption=False, top_layers=None):
        """
        :param credentials: number and registed password
        :param bool encryptionEnabled:  E2E encryption enabled/ disabled
        :params top_layers: tuple of layer between :class:`yowsup_gateway.layer.GatewayLayer` 
        and Yowsup Core Layers  
        """
        top_layers = (GatewayLayer,) + top_layers if top_layers else (GatewayLayer,)
        if encryption:
            from yowsup.layers.axolotl import YowAxolotlLayer
            layers = (
                top_layers +
                (stacks.YOWSUP_PROTOCOL_LAYERS_FULL,) +
                (YowAxolotlLayer,) + 
                stacks.YOWSUP_CORE_LAYERS
            )
        else:
            layers = (
                top_layers +
                stacks.YOWSUP_FULL_STACK 
            )
        try:
            super(YowsupGateway, self).__init__(layers)
        except ValueError as e:
            raise ConfigurationError(e.args[0])
        self.setCredentials(credentials)
        self.detached_queue = Queue.Queue()
        self.result = None
        
    def execDetached(self, fn):
        return self.detached_queue.put(fn)
        
    def loop(self, *args, **kwargs):
        discreteVal = kwargs["discrete"]
        del kwargs["discrete"]
        start = int(time.time())
        while True:
            asyncore.loop(*args, **kwargs)
            time.sleep(discreteVal)
            try:
                # Execute from detached queue callback
                callback = self.detached_queue.get(False)
                callback()
            except Queue.Empty:
                pass
            logger.debug("LOOP : %d enqueued, waiting to finish" % len(asyncore.socket_map))
            if len(asyncore.socket_map) == 0:
                self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
            if int(time.time()) - start > 1:
                logger.debug("LOOP : Timeout")
                self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        
    def execute(self):        
        try:
            self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
            self.loop(timeout=0.1, discrete=0.2, count=4)
        except AuthError as e:
            raise AuthenticationError("Authentication Error: {0}".format(e))
        except ConnectionError as e:
            raise ConnectionError("{0}".format(e))
        except ExitGateway:
            return self.result
        except:
            raise UnexpectedError(str(sys.exc_info()[0]))
                        
    def send_messages(self, messages):
        """
        Send text messages
        
        :param messages: list of (jid, message) tuples
        :return: list of inbox and outbox messages
        :rtype: SuccessfulResult
        """
        self.result = None
        # With this option do not receive messages
        # self.setProp(YowAuthenticationProtocolLayer.PROP_PASSIVE, True)
        self.setProp(GatewayLayer.CALLBACK_EVENT, YowLayerEvent(GatewayLayer.EVENT_SEND_MESSAGES, messages=messages))
        return self.execute()
        
    def receive_messages(self):
        """
        Returns messages received from Whatsapp
        
        :return: list of inbox and outbox messages
        :rtype: SuccessfulResult
        
        It contains exchanged messages with whatsapp.::
        
            received_messages = result.inbox
            sent_messages = result.outbox
         
        """
        self.result = None
        self.setProp(GatewayLayer.CALLBACK_EVENT, None)
        return self.execute()
