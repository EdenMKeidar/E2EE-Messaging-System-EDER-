import asyncio
import websockets
import os
import random
import json

CATCH_FILE_PATH = "server_db/catch_messages.json"

user_list = {
    "0524987132":{"user_data":["test@gmail.com","test"]}
}

catch_message = {
    # to 
    "phone":{"from":"user1_phone","message": "are you online ?"}
    
}
# adding websocket live connection with user phone.
# נשמר רק כאשר השרת רץ

online = {
    "phone":{"link":"websocket"}
}

# Load catch messages from file if it exists
def load_catch_messages():
    if os.path.exists(CATCH_FILE_PATH):
        with open(CATCH_FILE_PATH, "r") as file:
            return json.load(file)
    return {}

# Save catch messages to file
def save_catch_messages():
    with open(CATCH_FILE_PATH, "w") as file:
        json.dump(catch_message, file)

def send_to_catch(to, sender, message):
    if to not in catch_message:
        catch_message[to] = {}
        
        
    message_id = len(catch_message[to]) + 1
    
    # כדי לאפשר לשמור כמה הודעות שמיועדות למשתמש הזה 
    catch_message[to][message_id] = {"from": sender, "message": message}
    save_catch_messages()  # Save catch messages to file
    
def appendToOnline(phone, websocket):
    
        if phone not in online:
        
            online[phone] = {"link": websocket}   # create live online dict 
            print(f"Added new online user: {phone}")
            
            # Check and deliver any stored messages
            if phone in catch_message:
                for msg_id, msg in catch_message[phone].items():
                    asyncio.create_task(websocket.send(json.dumps({
                        "type": "message",
                        "catch": True,
                        "from": msg["from"],
                        "message": msg["message"]
                    })))
                    
                del catch_message[phone]  # Clear stored messages after delivery
                save_catch_messages()  # Save catch messages to file
        else:
            print(f"User is already online.")
    
def load_data_from_db():
    """
    Loads user_list dictionary from the server_db/user_list.json file.
    
    Returns:
    - user_list dictionary.
    """
    with open("server_db/user_list.json", "r") as file:
        user_list = json.load(file)
    return user_list

def append_to_user_list(user_list, phone, email, name):
    """
    Appends a new user to the user_list dictionary.
    
    Parameters:
    - user_list: dict - The dictionary to append to.
    - phone: str - User's phone number (key).
    - email: str - User's email address.
    - name: str - User's name.
    
    Returns:
    - dict - Updated user_list dictionary.
    """
    if phone not in user_list:
        user_list[phone] = {
        "user_data": [email, name]
        }
        print(f"Added new user: {phone}")
    else:
        print(f"User with phone {phone} already exists.")

    # update the server after code change.
    with open("server_db/user_list.json", "w") as file:
        json.dump(user_list,file)
    return user_list

def create_token():
       # נשמור את הזמן העכשווי ונוסיף יום עד לפקיעת התוקף
       
    token = random.randint(100000,999999)
    return token
    
async def sendBySecureChannel(user_name,user_mail,token,connection):
     
    try:
        print(f"sending the code to {user_name}: {token}")

        await connection.send(json.dumps({"type": "TokenSent","Token":token,
                                                          "message": "A token has been sent to your sms. Please confirm."}))
                        
                
                            
        
            
            
    except Exception as e:
        print(f"Failed to send sms: {e}")
    
async def websocket(connection): 
    
    try:
       async for client_request in connection:
                
                incoming_message = json.loads(client_request)
                  
                if incoming_message["type"] == "Register":

                    register_mail = incoming_message["mail"]
                    register_name = incoming_message["name"]
                    register_phone = incoming_message["phone"]
                    
                    token = str(create_token())
                    # new client want to register lets create new token and send to his mail box
                    
                    await sendBySecureChannel(register_name,register_mail,token,connection)
                
                # בדיקת התוקן        
                        
                elif incoming_message["type"] == "ConfirmToken":
                    
                    # נבדוק האם התוקן שווה למקור לבדיקת זהות
                   
                    if token == incoming_message["Token"]:
                        # if the user is autenticated 
                        
                        print(f"New user: {register_phone}, added to verified user_list.")
                        append_to_user_list(user_list, register_phone,register_mail, register_name)
                        
                        #adding users to online list
                        appendToOnline(register_phone,connection)
                        
                        response = {"type":"afterVerifedToken","message":"Connected to edar\n you can send messages."}
                    else:
                        response = {"type":"TokenFailed","message":"Bad token Please try again."} 

                    await connection.send(json.dumps(response))
                     
                elif incoming_message["type"] == "message":
                    
                    the_reciever = incoming_message["to"]
                    the_sender = incoming_message["from"]
                    the_message = incoming_message["send_message"]
                    
                    if the_reciever in online:  # Check if the recipient is online
                        the_reciever_link = online[the_reciever]["link"]  # Access the recipient's connection
                        await the_reciever_link.send(json.dumps({
                            "type": "message",
                            "from": the_sender,
                            "message": the_message
                            }))
                    else:
                        send_to_catch(the_reciever, the_sender, the_message)
                        
                        
                        unreachable_user = {
                            "type": "unreachable",
                            "message": f"User {the_reciever} is not Online,\n saving the message in case he turn Online again."
                        }
                        await connection.send(json.dumps(unreachable_user))  # Notify the sender that the recipient is offline  

                elif incoming_message["type"] == "ack":
    
                    to = incoming_message["to"]
                    sender = incoming_message["from"]
                    the_reciever_link = online[to]["link"]
                    
                    send_ack = {"type": "ack", "message": f"{sender} got the Message."}
                    await the_reciever_link.send(json.dumps(send_ack))
                    
    except Exception as error:
        print(f"Error in session: {error}")
        await connection.wait_closed()
        
                # ניהול ניתוקי משתמשים
    finally:
        # Clean up the user's connection upon disconnection
        disconnected_phone = None
        for phone, details in online.items():
            if details["link"] == connection:
                disconnected_phone = phone
                break

        if disconnected_phone:
            del online[disconnected_phone]
            print(f"User {disconnected_phone} has been disconnected and removed from online list.")


async def run_server():   # Server settings
    global catch_message
    
    async with websockets.serve(websocket, "localhost", 443,ping_interval=None):
        print("Server is listening on port: 443")
        await asyncio.Future()  # Run server until shotdown.
        load_data_from_db() # load the user_list from the db
        catch_message = load_catch_messages() # Initialize catch_message from file
        
if __name__ == "__main__":
    asyncio.run(run_server())
    #run the code