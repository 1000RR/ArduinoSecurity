GOAL:


- serverside render app served over SSL that renders given a client cert [Q: how to install client cert on Linux, Mac, iOS, android] that can be verified with an intermediate CA, just as the server's cert is made. (made by master CA)
- state is central and updated dynamically (via react). Single state store.
- cert should be issued for internal hostname, internal ip, and external hostname. 



SAFETY CRITERIA:
- password-protected if no cert found. [TODO: max attempts?]
- TODO: no exposure of any port other than custom https port, and socketio port. 
