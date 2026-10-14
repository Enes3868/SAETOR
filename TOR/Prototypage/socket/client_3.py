import socket
import threading


def start_client():
    host = '10.128.5.23'
    port = 1002

    try:
        client_socket = socket.socket()
        client_socket.connect((host, port))
        print(f"Connecté au serveur {host}:{port}")
    except Exception as e:
        print(f"Impossible de se connecter au serveur: {e}")
        return

    def receive_messages():
        while True:
            try:
                reply = client_socket.recv(1024).decode()
                if not reply:
                    print("Le serveur a fermé la connexion")
                    break

                print(f"\nMessage du serveur : {reply}")
                print("Entrez un message (bye ou arret ou autre) : ", end="", flush=True)

                if reply == "Serveur arrêté" or "arrêté" in reply.lower():
                    print("Le serveur a été arrêté")
                    client_socket.close()
                    break

            except Exception as e:
                print(f"\nErreur de réception: {e}")
                break

    def send_messages():
        while True:
            try:
                message = input("Entrez un message (bye ou arret ou autre) : ")
                client_socket.send(message.encode())
                print(f"Message envoyé : {message}")

                if message == "bye":
                    print("Déconnexion")
                    client_socket.close()
                    break

                elif message == "arret":
                    print("Arrêt demandé du serveur")
                    client_socket.close()
                    break

            except Exception as e:
                print(f"Erreur d'envoi: {e}")
                break

    # Démarrer le thread de réception
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.daemon = True
    receive_thread.start()

    # Thread d'envoi dans le thread principal
    send_messages()


if __name__ == "__main__":
    start_client()
