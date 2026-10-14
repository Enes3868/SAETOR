import socket
import threading

clients = []

def handle_client(client_socket, address):
    print(f"[+] Nouveau client connecté: {address}")
    while True:
        try:
            msg = client_socket.recv(1024).decode('utf-8')
            if not msg:
                break

            print(f"[{address}] {msg}")

            if msg.lower() == "bye":
                print(f"[-] {address} quitte le chat.")
                clients.remove(client_socket)
                client_socket.close()
                break

            elif msg.lower() == "arret":
                print("[!] Arrêt demandé, fermeture du serveur...")
                for c in clients:
                    c.close()
                server.close()
                return

            # Relayer le message à tous les autres clients
            for c in clients:
                if c != client_socket:
                    c.send(f"[{address}] {msg}".encode('utf-8'))

        except:
            break

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 1002))
server.listen(5)
print("[*] Serveur en écoute sur le port 5000")

while True:
    client_socket, addr = server.accept()
    clients.append(client_socket)
    thread = threading.Thread(target=handle_client, args=(client_socket, addr))
    thread.start()
