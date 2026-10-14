import socket

def start_client():
    host = '127.0.0.1'
    port = 1002
    client_socket = socket.socket()
    client_socket.connect((host, port))
    print(f"Connecté au serveur {host}:{port}")

    while True:
        try:
            message = input("Entrez un message (bye ou arret ou autre) : ")
            client_socket.send(message.encode())
            print(f"Message envoyé : {message}")

            reply = client_socket.recv(1024).decode()
            print(f"Message du serveur : {reply}")

            if message == "bye":
                print("Déconnexion")
                client_socket.close()
                break

            elif message == "arret":
                print("Le serveur a été arrêté")
                client_socket.close()
                break

        except Exception as e:
            print(f"Erreur : {e}")
            break
start_client()
