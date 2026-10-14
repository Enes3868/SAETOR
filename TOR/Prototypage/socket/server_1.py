import socket

reply = "coucou"

server_socket = socket.socket()
server_socket.bind(('0.0.0.0', 1002))
server_socket.listen(1)
print("Le serveur attend une connexion...")
conn, address = server_socket.accept()
print(f"Connexion acceptée de {address}")
message = conn.recv(1024).decode()
print(f"Message reçu du client : {message}")
conn.send(reply.encode())
print(f"Réponse envoyée au client : {reply}")

if message == "arret":
    conn.close()
    server_socket.close()
