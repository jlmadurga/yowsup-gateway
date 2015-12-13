========
Usage
========

The idea of Yowsup-Gateway is simplify the use of Yowsup library.To use Yowsup Gateway in a project::

    from yowsup_gateway import YowsupGateway
    
    gateway = YowsupGateway(credentials=("phone_number", "password"))
    
    # Send text messages
    result = gateway.send_messages([("to_phone_number", "text message")])
    if result.is_success:
       print result.inbox, result.outbox
       
    # Receive messages
    result = gateway.receive_messages()
    if result.is_sucess:
       print result.inbox, result.outbox
       
If you want to use encryotion or add layers between core layers and Yowsup-Gateway layer::

	gateway = YowsupGateway(credentials, True, OtherLayers)
       

To get whatsapp password you should register first your number with yowsup-cli 
https://github.com/tgalal/yowsup/wiki/yowsup-cli-2.0#yowsup-cli-registration
       
