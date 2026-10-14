import socket

message = "bonjour serv"
host = "127.0.0.1"
port = 1002

client_socket = socket.socket()
client_socket.connect((host, port))
print(f"Connecté au serveur {host}:{port}")
client_socket.send(message.encode())
print(f"Message envoyé au serveur : {message}")
reply = client_socket.recv(1024).decode()
print(f"Réponse reçue du serveur : {reply}")

if reply == "bye" or "arret":
    client_socket.close()
