import socket
import threading

def serv(conn, address):
    print(f"Connexion acceptée de {address}")

    def receive_messages():
        while True:
            try:
                message = conn.recv(1024).decode()
                if not message:
                    print(f"Le client {address} a fermé la connexion")
                    break

                print(f"Message reçu du client {address}: {message}")

                if message == "bye":
                    print(f"Le client {address} a demandé à se déconnecter")
                    conn.send("Vous avez été déconnecté".encode())
                    break

                elif message == "arret":
                    print("Le serveur s'arrête")
                    conn.send("Serveur arrêté".encode())
                    break

            except Exception as e:
                print(f"Erreur de communication avec {address}: {e}")
                break
        conn.close()

    def send_messages():
        while True:
            try:
                message = input("Serveur - Entrez un message: ")
                conn.send(message.encode())
                print(f"Message envoyé au client: {message}")

                if message == "arret":
                    break

                if message == "bye":
                    break

            except Exception as e:
                print(f"Erreur d'envoi: {e}")
                break
        conn.close()
    # Démarrer le thread de réception
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.daemon = True
    receive_thread.start()

    # Thread d'envoi dans le thread principal
    send_messages()

    print(f"Connexion avec {address} fermée")


def start_server():
    server_socket = socket.socket()
    server_socket.bind(('0.0.0.0', 1002))
    server_socket.listen(1)
    print("Le serveur attend une connexion sur le port 1002")

    while True:
        conn, address = server_socket.accept()

        # Créer un thread pour gérer le client
        client_thread = threading.Thread(target=serv, args=(conn, address))
        client_thread.daemon = True
        client_thread.start()


if __name__ == "__main__":
    start_server()
