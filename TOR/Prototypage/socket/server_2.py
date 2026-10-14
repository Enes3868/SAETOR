import socket
import time


def start_server():
    server_socket = socket.socket()

    server_socket.bind(('0.0.0.0', 1002))
    server_socket.listen(1)
    print("Le serveur attend une connexion")

    conn, address = server_socket.accept()
    print(f"Connexion acceptée de {address}")

    while True:
        try:
            message = conn.recv(1024).decode()
            if not message:
                print("Le client a fermé la connexion")
                break

            print(f"Message reçu du client : {message}")

            if message == "bye":
                print("Le client a demandé à se déconnecter")
                conn.send("Vous avez été déconnecté".encode())
                break

            elif message == "arret":
                print("Le serveur s'arrête")
                conn.send("Serveur arrêté".encode())
                break

            else:
                reply = f"Message reçu: {message}"
                conn.send(reply.encode())

        except Exception as e:
            print(f"Erreur de communication : {e}")
            break
    conn.close()
    server_socket.close()
start_server()
