import json
import asyncio
import websockets
import random
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


connected = False


# manage keys start

def generate_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key

def save_keys(private_key, public_key, user_phoneNumber):
    # Ensure the local directory exists
    os.makedirs("client_db2", exist_ok=True)
    
    # Save the private key locally
    with open(f"client_db2/{user_phoneNumber}_private_key.pem", "wb") as file:
        file.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
     # Ensure the server directory exists
    os.makedirs("server_db", exist_ok=True)
    
    # Save the public key on the server
    with open(f"server_db/{user_phoneNumber}_public_key.pem", "wb") as file:
        file.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

def load_private_key(user_phoneNumber):
    with open(f"client_db2/{user_phoneNumber}_private_key.pem", "rb") as file:
        private_key = serialization.load_pem_private_key(
            file.read(),
            password=None,
        )
    return private_key

def load_public_key(user_phoneNumber):
    with open(f"server_db/{user_phoneNumber}_public_key.pem", "rb") as file:
        public_key = serialization.load_pem_public_key(
            file.read(),
        )
    return public_key

# manage keys end

#data manipulation 


def decrypt_message(private_key, encrypted_message):
    decrypted_message = private_key.decrypt(
        encrypted_message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted_message.decode()

def encrypt_message(public_key, message):
    encrypted_message = public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return encrypted_message

def add_user_info():
    
    user_name = input("enter your full name: \n")
    user_mail = input("enter your mail address:  \n")
    user_phoneNumber = input("enter your phone_number: \n")
    
    private_key, public_key = generate_keys()
    save_keys(private_key, public_key, user_phoneNumber)
    
    user_data = {"user_phoneNumber":user_phoneNumber,"user_name":user_name,"user_mail":user_mail}
    
    # Save object
    with open("client_db2/user_data2.json", "w") as file:
        json.dump(user_data, file)
    return user_data

def collect_data_from_db():
    global user_info
    # Load object
    with open("client_db2/user_data2.json", "r") as file:
        user_info = json.load(file)
    return user_info   
# enter message to user :
async def send_message(websocket, phone,):
    try:
        global to
        to = input("enter contact phone: ")
        the_message = input("Content: \n")
        sender_user_name = user_info["user_name"]
        
        message_content = f"Message From: {sender_user_name} \n {the_message}"
    
        recipient_public_key = load_public_key(to)

        # Encrypt the message
        encrypted_message = encrypt_message(recipient_public_key, message_content)
    
    except FileNotFoundError:
        print("Recipient public key not found")
    except Exception as error:
        print(f"Error encrypting message: {error}")
        return


    newMessage = {"type":"message",
                  "from":phone,
                  "to":to,
                  "send_message":encrypted_message.hex()}

    await websocket.send(json.dumps(newMessage))
    
async def want_toSendText(websocket, phone):
    send_more = input("Do you want to send a message? (y/n): ")
                        
    if send_more == 'y':
        await send_message(websocket, phone) # send message function
                        
    elif send_more == 'n':
        await asyncio.sleep(1)
        
    elif send_more == 'exit':
        print("Goodbye!")
        await websocket.close()
    return

async def ack(websocket, phone):
    ack_message = {"type":"ack","from":phone,"to":to}                
    await websocket.send(json.dumps(ack_message))
    
async def request_data(uri):
    global connected
    async with websockets.connect(uri ,ping_interval=None) as websocket:
        
        # נפריד את המידע מהאחסון למשתנים
        
        name = user_info["user_name"]
        mail = user_info["user_mail"]
        phone = user_info["user_phoneNumber"]
        
        # creating the first Register on server messege
        req_message = json.dumps({"type":"Register","name":name,"phone":phone,"mail":mail})
        
        # i want to Register
        await websocket.send(req_message)
        while True:
            try:   
                response = await websocket.recv()
                response_json = json.loads(response)
                
                if response_json["type"] == "TokenSent":
                    
                    # please enter your code !
                    print(response_json["message"])
                    
                    token = response_json["Token"]
                    print(f"your token: {token}")
                    
                    mail_code = input("Enter Vertification Code \n")

                    send_token = {"type":"ConfirmToken","Token":mail_code}
                    
                    
                    await websocket.send(json.dumps(send_token))
                        
                    
                elif response_json["type"] == "TokenFailed":    # secound chanse to hit code
                    print(response_json["message"]) 
                    
                    mail_code = input("Enter Vertification Code, again\n")
                    try_again = {"type":"ConfirmToken","Token":str(mail_code)}
                    await websocket.send(json.dumps(try_again))
                    
                    
                elif response_json["type"] == "afterVerifedToken": 
                    success = response_json["message"]
                    print(success)
                    
                    await want_toSendText(websocket, phone) # שאלה ראשונה האם לשלוח הודעה 
                        
                    
                elif response_json["type"] == "unreachable":   # manage offline user
                    unreachable_message = response_json["message"]
                    print(unreachable_message)
                    
                elif response_json["type"] == "message":    # manage user response 
                    user_message = response_json["message"]
                    
                    # Decrypt the message using the local private key
                    private_key = load_private_key(user_info["user_phoneNumber"])
                    encrypted_message = bytes.fromhex(user_message)
                    decrypted_message = decrypt_message(private_key, encrypted_message)
                    print(f"Decrypted message: {decrypted_message}")
                    
                    await want_toSendText(websocket, phone) # שאלה האם לשלוח הודעה כתגובה למשתמש
                    await ack(websocket, phone) # אישור קבלת הודעה
                    
             
                elif response_json["type"] == "ack":
                    ack_message = response_json["message"]
                    print(ack_message)
                    
                        
            
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by server")
                break
            except Exception as error:  # Catch other potential errors
                print(f"Error receiving data: {error}")
                break

async def run_main():
    uri = "ws://127.0.0.1:443"  # Server URL
    
    # check_if_new_user
    while(True):
        new_user = input("are you new user? (n/y): ")
        
        if new_user == 'y' or new_user == 'Y': 
            add_user_info()
            collect_data_from_db()
            break
        
        elif new_user == 'n' or new_user == 'N':
            collect_data_from_db() # נשתמש במידע האחרון שקיים בשרת
            user_name = user_info["user_name"]
            
            print(f"welcome {user_name}!")
            break
 
    await request_data(uri)   
    await asyncio.Future() # Run until shutdown 
    
if __name__ == "__main__":
    asyncio.run(run_main())
