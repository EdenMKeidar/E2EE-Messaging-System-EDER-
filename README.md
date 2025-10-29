# E2EE Messaging System

A minimal end-to-end encrypted (E2EE) messaging demo built in Python.  
It includes a WebSocket server and two clients that generate RSA key pairs per user,
perform a simple token-based registration,and exchange encrypted messages in real time.
If a recipient is offline, messages are cached and delivered when they reconnect.

*This project is for learning/demo purposes only.

---

## How to Run

### 1) Prerequisites
- Python 3.10+
- Install dependencies:
bash
pip install websockets cryptography

next steps-
stat the server -
Run in one terminal:
python e2ee_server.py
run two clients- Open two other terminals:
client A- python e2ee_client.py
client B- python e2ee_client2.py
Register and Exchange Messages- Register and then you can send and receive encrypted messages between the two clients!
