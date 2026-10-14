import sys
import socket
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor, QPalette
from base_donnees import bd


class ServeurThread(QThread):
    message_received = pyqtSignal(str)
    server_started = pyqtSignal(str, int)
    server_stopped = pyqtSignal()
    
    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = True
        self.serveur_instance = None
    
    def run(self):
        """Exécute le serveur dans un thread séparé"""
        self.message_received.emit(f"[INIT] Initialisation du serveur sur le port {self.port}...")
        
        try:
            ip_local = socket.gethostbyname(socket.gethostname())

            if bd.connecter():
                self.message_received.emit(f"[SUCCES] Base de données connectée sur {bd.host}")
                if bd.verifier_tables():
                    self.message_received.emit("[SUCCES] Tables OK")
                else:
                    self.message_received.emit("[ERREUR] Tables manquantes dans la base")
            else:
                self.message_received.emit("[ERREUR] Impossible de connecter la base de données")
            
            self.serveur_instance = ServeurMaitreGUI('0.0.0.0', self.port, self.message_received)
            self.server_started.emit(ip_local, self.port)
            self.message_received.emit(f"[SUCCES] Serveur démarré sur {ip_local}:{self.port}")
            self.message_received.emit("[ATTENTE] En attente de connexions...")
            self.serveur_instance.demarrer()
        except Exception as e:
            self.message_received.emit(f"[ERREUR] ERREUR: {str(e)}")
        finally:
            self.server_stopped.emit()
    
    def stop(self):
        """Arrête le serveur"""
        self.running = False
        if self.serveur_instance:
            self.serveur_instance.stop_server()
        self.quit()
        self.wait()


class ServeurMaitreGUI:
    """Serveur TCP pour l'interface graphique"""
    
    def __init__(self, hote='0.0.0.0', port=9000, signal_callback=None):
        self.hote = hote
        self.port = port
        self.signal_callback = signal_callback
        self.running = True
        self.server_socket = None
        self._print("[INIT] Initialisation du serveur maître...")

    def _print(self, message):
        if self.signal_callback:
            self.signal_callback.emit(message)
        else:
            print(message)

    def traiter_enregistrement_routeur(self, connexion, adresse, donnees):
        parties = donnees.split(";")
        if len(parties) >= 5:
            id_routeur = parties[1]
            port = int(parties[2])
            e = int(parties[3])
            n = int(parties[4])

            ip_reelle = adresse[0]

            if bd.est_connecte() and bd.enregistrer_noeud(id_routeur, "routeur", ip_reelle, port, e, n):
                self._print(f"[SUCCES] Routeur {id_routeur} enregistré avec IP {ip_reelle}:{port}")
                connexion.send(b"OK")
                self.ajouter_regles_routage_automatiques(id_routeur, ip_reelle, port)
            else:
                self._print(f"[ERREUR] Échec de l'enregistrement du routeur {id_routeur}")
                connexion.send(b"ERREUR_BD")
        else:
            self._print("[ERREUR] Format de message incorrect")
            connexion.send(b"ERREUR_FORMAT")

    def traiter_deconnexion_routeur(self, connexion, adresse, donnees):
        """Traite la déconnexion d'un routeur"""
        parties = donnees.split(";")
        if len(parties) >= 2:
            id_routeur = parties[1]
            
            self._print(f"[DECONNEXION] Déconnexion du routeur {id_routeur}...")
            
            if bd.est_connecte():
                try:
                    curseur = bd.connexion.cursor()
                    curseur.execute(
                        "UPDATE noeuds SET statut='inactif' WHERE id_noeud=%s",
                        (id_routeur,)
                    )
                    
                    curseur.execute(
                        "DELETE FROM table_routage WHERE id_routeur=%s OR destination=%s",
                        (id_routeur, id_routeur)
                    )
                    
                    bd.connexion.commit()
                    curseur.close()
                    
                    self._print(f"[SUCCES] Routeur {id_routeur} déconnecté et supprimé")
                    connexion.send(b"OK")
                    
                except Exception as e:
                    self._print(f"[ERREUR] Déconnexion routeur: {e}")
                    connexion.send(b"ERREUR_BD")
            else:
                connexion.send(b"ERREUR_BD")
        else:
            connexion.send(b"ERREUR_FORMAT")

    def traiter_deconnexion_client(self, connexion, adresse, donnees):
        """Traite la déconnexion d'un client"""
        parties = donnees.split(";")
        if len(parties) >= 2:
            id_client = parties[1].upper()
            
            self._print(f"[DECONNEXION] Déconnexion du client {id_client}...")
            
            if bd.est_connecte():
                try:
                    curseur = bd.connexion.cursor()
                    curseur.execute(
                        "UPDATE noeuds SET statut='inactif' WHERE id_noeud=%s",
                        (id_client,)
                    )
                    curseur.execute(
                        "DELETE FROM table_routage WHERE destination=%s",
                        (id_client,)
                    )
                    
                    bd.connexion.commit()
                    curseur.close()
                    
                    self._print(f"[SUCCES] Client {id_client} déconnecté")
                    connexion.send(b"OK")
                    
                except Exception as e:
                    self._print(f"[ERREUR] Déconnexion client: {e}")
                    connexion.send(b"ERREUR_BD")
            else:
                connexion.send(b"ERREUR_BD")
        else:
            connexion.send(b"ERREUR_FORMAT")

    def ajouter_regles_routage_automatiques(self, nouveau_routeur, ip_routeur, port_routeur):
        if not bd.est_connecte():
            self._print("[ERREUR] Base non connectée, impossible d'ajouter les règles de routage")
            return

        self._print(f"[CONFIG] Ajout des règles de routage pour {nouveau_routeur}...")

        tous_les_routeurs = bd.obtenir_tous_routeurs()
        self._print(f"[LISTE] Routeurs existants: {[r['id'] for r in tous_les_routeurs]}")

        for routeur in tous_les_routeurs:
            if routeur['id'] != nouveau_routeur:
                bd.ajouter_regle_routage(
                    routeur['id'],
                    nouveau_routeur,
                    nouveau_routeur, 
                    ip_routeur,
                    port_routeur
                )

                bd.ajouter_regle_routage(
                    nouveau_routeur,
                    routeur['id'],
                    routeur['id'],
                    routeur['ip'],
                    routeur['port']
                )

                self._print(f"[SUCCES] Règle routage ajoutée: {routeur['id']} <-> {nouveau_routeur}")

        tous_les_clients = bd.obtenir_tous_clients()
        self._print(f"[LISTE] Clients existants: {[c['id'] for c in tous_les_clients]}")

        for client in tous_les_clients:
            bd.ajouter_regle_routage(
                nouveau_routeur,
                client['id'],
                "0",  # "0" signifie livraison finale au client
                client['ip'],
                client['port']
            )
            self._print(f"[SUCCES] Règle routage ajoutée: {nouveau_routeur} -> {client['id']} (livraison directe)")

    def traiter_enregistrement_client(self, connexion, adresse, donnees):
        parties = donnees.split(";")
        if len(parties) >= 3:
            id_client = parties[1].upper()  # Normaliser en majuscules
            port = int(parties[2])
            ip_reelle = adresse[0]

            if bd.est_connecte() and bd.enregistrer_noeud(id_client, "client", ip_reelle, port):
                self._print(f"[SUCCES] Client {id_client} enregistré avec IP {ip_reelle}:{port}")
                connexion.send(b"OK")
                self.ajouter_regles_client_automatiques(id_client, ip_reelle, port)
            else:
                self._print(f"[ERREUR] Échec de l'enregistrement du client {id_client}")
                connexion.send(b"ERREUR")
        else:
            connexion.send(b"ERREUR_FORMAT")

    def ajouter_regles_client_automatiques(self, nouveau_client, ip_client, port_client):
        """Ajoute automatiquement les règles de routage pour un nouveau client vers tous les routeurs existants"""
        if not bd.est_connecte():
            return

        self._print(f"[CONFIG] Ajout des règles de routage pour le nouveau client {nouveau_client}...")

        tous_les_routeurs = bd.obtenir_tous_routeurs()
        self._print(f"[LISTE] Routeurs disponibles: {[r['id'] for r in tous_les_routeurs]}")

        for routeur in tous_les_routeurs:
            bd.ajouter_regle_routage(
                routeur['id'],
                nouveau_client,
                "0",  # Livraison finale au client
                ip_client,
                port_client
            )
            self._print(f"[SUCCES] Règle routage ajoutée: {routeur['id']} -> {nouveau_client} (livraison directe)")

    def traiter_obtenir_routeurs(self, connexion):
        if not bd.est_connecte():
            connexion.send(b"ERREUR_BD")
            return

        routeurs = bd.obtenir_tous_routeurs()
        if routeurs:
            message = ""
            for routeur in routeurs:
                message += f"{routeur['id']}:{routeur['ip']}:{routeur['port']}:{routeur['cle_publique'][0]}:{routeur['cle_publique'][1]}|"
            connexion.send(message.encode())
            self._print(f"[SUCCES] Liste de {len(routeurs)} routeurs envoyée à un client")
        else:
            connexion.send(b"AUCUN_ROUTEUR")

    def traiter_obtenir_info_noeud(self, connexion, donnees):
        if not bd.est_connecte():
            connexion.send(b"ERREUR_BD")
            return

        parties = donnees.split(";")
        if len(parties) >= 2:
            id_noeud = parties[1].upper()
            self._print(f"[RECHERCHE] Recherche d'information pour le nœud: {id_noeud}")

            info_noeud = bd.obtenir_info_noeud(id_noeud)
            if info_noeud:
                message = f"{info_noeud['type']}:{info_noeud['ip']}:{info_noeud['port']}"
                if info_noeud['cle_publique']:
                    message += f":{info_noeud['cle_publique'][0]}:{info_noeud['cle_publique'][1]}"
                connexion.send(message.encode())
                self._print(f"[SUCCES] Info nœud {id_noeud} envoyée: {message}")
            else:
                self._print(f"[ERREUR] Nœud {id_noeud} non trouvé dans la base")
                connexion.send(b"NON_TROUVE")
        else:
            connexion.send(b"ERREUR_FORMAT")

    def traiter_connexion(self, connexion, adresse):
        try:
            donnees = connexion.recv(1024).decode().strip()
            self._print(f"[REÇU] Requête reçue de {adresse[0]}: {donnees[:50]}...")

            if donnees.startswith("ENREGISTRER_ROUTEUR"):
                self.traiter_enregistrement_routeur(connexion, adresse, donnees)
            elif donnees.startswith("ENREGISTRER_CLIENT"):
                self.traiter_enregistrement_client(connexion, adresse, donnees)
            elif donnees == "OBTENIR_ROUTEURS":
                self.traiter_obtenir_routeurs(connexion)
            elif donnees.startswith("OBTENIR_INFO_NOEUD"):
                self.traiter_obtenir_info_noeud(connexion, donnees)
            elif donnees.startswith("DECONNEXION_ROUTEUR"):
                self.traiter_deconnexion_routeur(connexion, adresse, donnees)
            elif donnees.startswith("DECONNEXION_CLIENT"):
                self.traiter_deconnexion_client(connexion, adresse, donnees)
            else:
                self._print(f"[ERREUR] Commande inconnue: {donnees}")
                connexion.send(b"COMMANDE_INCONNUE")
        except Exception as e:
            self._print(f"[ERREUR] Erreur traitement: {e}")
            connexion.send(b"ERREUR")
        finally:
            connexion.close()

    def demarrer(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.hote, self.port))
        self.server_socket.listen(20)

        self._print(f"[SUCCES] Serveur maître démarré sur {self.hote}:{self.port}")
        self._print("[ATTENTE] En attente de connexions...")

        while self.running:
            try:
                connexion, adresse = self.server_socket.accept()
                threading.Thread(target=self.traiter_connexion, args=(connexion, adresse)).start()
            except OSError:
                break
    
    def stop_server(self):
        """Arrête le serveur"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()


class ConsoleWidget(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 10))
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        self.setPalette(palette)
        
    def append_message(self, message):
        if "[SUCCES]" in message:
            color = "#4CAF50"
        elif "[ERREUR]" in message:
            color = "#F44336"
        elif "[ATTENTION]" in message:
            color = "#FF9800"
        elif "[INIT]" in message:
            color = "#2196F3"
        elif "[REÇU]" in message or "[LISTE]" in message:
            color = "#9C27B0"
        elif "[RECHERCHE]" in message or "[DECONNEXION]" in message:
            color = "#FFC107"
        elif "[ATTENTE]" in message or "[CONFIG]" in message:
            color = "#00BCD4"
        else:
            color = "#E0E0E0"
        html = f'<span style="color: {color};">{message}</span>'
        self.append(html)
        self.moveCursor(QTextCursor.MoveOperation.End)
        if self.document().blockCount() > 1000:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()


class ServerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serveur_thread = None
        self.init_ui()
        self.get_local_ip()
        
    def init_ui(self):
        self.setWindowTitle("Serveur Maître - Interface de Contrôle")
        self.setGeometry(100, 100, 900, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        info_group = QGroupBox("Informations du Serveur")
        info_layout = QVBoxLayout()
        ip_layout = QHBoxLayout()
        ip_label = QLabel("Adresse IP locale:")
        ip_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.ip_value = QLabel("Chargement...")
        self.ip_value.setFont(QFont("Arial", 10))
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_value)
        ip_layout.addStretch()
        port_layout = QHBoxLayout()
        port_label = QLabel("Port du serveur:")
        port_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Ex: 9000")
        self.port_input.setText("9000")
        self.port_input.setMaximumWidth(100)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        info_layout.addLayout(ip_layout)
        info_layout.addLayout(port_layout)
        info_group.setLayout(info_layout)
        
        controls_group = QGroupBox("Contrôles du Serveur")
        controls_layout = QHBoxLayout()
        self.start_button = QPushButton("Démarrer le Serveur")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_button.clicked.connect(self.start_server)
        controls_layout.addWidget(self.start_button)
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        
        console_group = QGroupBox("Console du Serveur")
        console_layout = QVBoxLayout()
        self.console = ConsoleWidget()
        console_layout.addWidget(self.console)
        console_group.setLayout(console_layout)
        
        main_layout.addWidget(info_group)
        main_layout.addWidget(controls_group)
        main_layout.addWidget(console_group)
        
        self.ip_timer = QTimer()
        self.ip_timer.timeout.connect(self.get_local_ip)
        self.ip_timer.start(30000)
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self.ip_value.setText(f"{ip}")
        except Exception as e:
            self.ip_value.setText("Non disponible")
            self.console.append_message(f"[ATTENTION] Impossible de récupérer l'IP: {str(e)}")
    
    def start_server(self):
        try:
            port = int(self.port_input.text())
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            self.console.append_message("[ERREUR] Port invalide. Veuillez entrer un port entre 1 et 65535")
            return
        
        self.start_button.setEnabled(False)
        self.port_input.setEnabled(False)
        self.serveur_thread = ServeurThread(port)
        self.serveur_thread.message_received.connect(self.console.append_message)
        self.serveur_thread.server_started.connect(self.on_server_started)
        self.serveur_thread.server_stopped.connect(self.on_server_stopped)
        self.serveur_thread.start()
        self.console.append_message(f"[INIT] Lancement du serveur sur le port {port}...")
    
    def on_server_started(self, ip, port):
        self.console.append_message(f"[SUCCES] Serveur démarré avec succès sur {ip}:{port}")
    
    def on_server_stopped(self):
        self.start_button.setEnabled(True)
        self.port_input.setEnabled(True)
        self.console.append_message("[ARRET] Serveur arrêté")
    
    def closeEvent(self, event):
        if self.serveur_thread and self.serveur_thread.isRunning():
            self.serveur_thread.stop()
            self.serveur_thread.wait(2000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ServerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
