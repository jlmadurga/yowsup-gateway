# -*- coding: utf-8 -*-
class SuccessfulResult(object):
    """
    An instance of this class is returned from most operations when the request 
    is successful. Get messages exchanged::
    if result.is_success:
        print [in_message for in_message in result.inbox]
        print [out_message for out_message in result.outbox]
        
    :ivar list inbox: received messages from whatsapp
    :ivar list outbox: sent message to whatsapp
    """
    def __init__(self, inbox=None, outbox=None):
        self.inbox = inbox
        self.outbox = outbox
            
    def __repr__(self):        
        return "<inbox: %s, outbox: %s at %d>" % \
            (self.inbox.__repr__(), self.outbox.__repr__(), id(self))

    @property
    def is_success(self):
        """ Returns whether the result from the gateway is a successful response
        """
        return True
