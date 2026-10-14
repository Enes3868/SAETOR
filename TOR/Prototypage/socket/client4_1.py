import socket
import threading

def receive_messages(sock):
    while True:
        try:
            msg = sock.recv(1024).decode('utf-8')
            if not msg:
                break
            print(msg)
        except:
            break

server_ip = input("Adresse IP du serveur : ")
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server_ip, 1002))

thread = threading.Thread(target=receive_messages, args=(client,))
thread.start()

print("Tapez 'bye' pour quitter, 'arret' pour stopper le serveur.")
while True:
    msg = input()
    client.send(msg.encode('utf-8'))
    if msg.lower() in ['bye', 'arret']:
        break

client.close()
