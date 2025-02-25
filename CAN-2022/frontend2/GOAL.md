GOAL:

[nginx will handle 2-way certificate verification, could go for React SPA instead of SSR]
[if need password access, then need SSR]
- serverside render app served over SSL that renders given a client cert [Q: how to install client cert on Linux, Mac, iOS, android] that can be verified with an intermediate CA, just as the server's cert is made. (made by master CA)
- state is central and updated dynamically (react, duh). Single store out of pieces.
- cert should be for internal hostname, internal ip, and external hostname. Q: how can i map <host.domain.com> to map to a local machine?



SAFETY CRITERIA:
- Nothing should render if the cert is unverified
- no exposure of any port other than custom https port, and socketio port. 
