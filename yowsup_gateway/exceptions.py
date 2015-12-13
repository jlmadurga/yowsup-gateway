# -*- coding: utf-8 -*-
class YowsupGatewayError(Exception):
    pass


class UnexpectedError(YowsupGatewayError):
    """ Raised for unknown or unexpected errors. """
    pass


class ConfigurationError(YowsupGatewayError):
    """
    Raised when gateway detects and error in configurations
    """
    pass


class ConnectionError(YowsupGatewayError):
    """
    Raised when gateway tries to perform an action which requires to be
    connected to WhatsApp
    """
    pass


class AuthenticationError(YowsupGatewayError):
    """
    Raised when gateway cannot authenticate with the whatsapp.  This means the
    password for number is incorrect. Check if registration was correct
    """
    pass
