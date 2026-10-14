import sys
import socket
import threading
import random
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from chiffrement import (
    chiffrer,
    chiffrer_cesar,
    dechiffrer_cesar,
    encoder_couche_routage,
    decoder_couche_routage,
    texte_vers_nombre_segmente
)


class ClientThread(QThread):
    """Thread pour exécuter le client en arrière-plan"""
    log_signal = pyqtSignal(str)
    connected_signal = pyqtSignal(bool)
    message_received_signal = pyqtSignal(str, str)  # (adresse, message)

    def __init__(self, nom_client, port_client, ip_maitre, port_maitre=9000):
        super().__init__()
        self.nom_client = nom_client.upper()
        self.port_client = port_client
        self.ip_maitre = ip_maitre
        self.port_maitre = port_maitre
        self.cle_cesar = 24
        self.running = True
        self.serveur_socket = None

    def run(self):
        """Méthode principale du thread"""
        self.log_signal.emit(f"[INIT] Initialisation du client {self.nom_client}...")

        if not self.enregistrer_aupres_maitre():
            self.connected_signal.emit(False)
            return

        self.connected_signal.emit(True)
        self.demarrer_reception()

    def enregistrer_aupres_maitre(self):
        """Enregistre le client auprès du serveur maître"""
        try:
            socket_maitre = socket.socket()
            socket_maitre.settimeout(10)
            socket_maitre.connect((self.ip_maitre, self.port_maitre))

            message = f"ENREGISTRER_CLIENT;{self.nom_client};{self.port_client}"
            self.log_signal.emit(f"[ENVOI] Envoi enregistrement: {message}")
            socket_maitre.send(message.encode())

            reponse = socket_maitre.recv(1024).decode()
            socket_maitre.close()

            if reponse == "OK":
                self.log_signal.emit(f"[SUCCES] Client {self.nom_client} enregistré")
                return True
            else:
                self.log_signal.emit(f"[ERREUR] Erreur: {reponse}")
                return False

        except Exception as e:
            self.log_signal.emit(f"[ERREUR] Erreur connexion au maître: {e}")
            return False

    def demarrer_reception(self):
        """Démarre le serveur de réception des messages"""
        try:
            self.serveur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serveur_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.serveur_socket.bind(('0.0.0.0', self.port_client))
            self.serveur_socket.listen(5)
            self.serveur_socket.settimeout(1.0)

            self.log_signal.emit(f"[ECOUTE] Client {self.nom_client} en écoute sur le port {self.port_client}")

            while self.running:
                try:
                    connexion, adresse = self.serveur_socket.accept()
                    donnees = connexion.recv(1024).decode()
                    if donnees:
                        self.log_signal.emit(f"[RECEPTION] Message reçu de {adresse[0]}:")
                        self.log_signal.emit(f"   Chiffré: '{donnees}'")

                        message_clair = dechiffrer_cesar(donnees, self.cle_cesar)
                        self.log_signal.emit(f"   Déchiffré: '{message_clair}'")
                        self.message_received_signal.emit(adresse[0], message_clair)

                    connexion.close()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.log_signal.emit(f"[ATTENTION] Erreur réception: {e}")
                    continue

        except Exception as e:
            self.log_signal.emit(f"[ERREUR] Erreur initialisation socket: {e}")
        finally:
            if self.serveur_socket:
                try:
                    self.serveur_socket.close()
                except:
                    pass

    def supprimer_du_maitre(self):
        """Informe le serveur maître de la déconnexion"""
        try:
            socket_maitre = socket.socket()
            socket_maitre.settimeout(5)
            socket_maitre.connect((self.ip_maitre, self.port_maitre))

            message = f"DECONNEXION_CLIENT;{self.nom_client}"
            self.log_signal.emit(f"[DECONNEXION] Envoi déconnexion: {message}")
            socket_maitre.send(message.encode())

            socket_maitre.close()
            self.log_signal.emit("[SUCCES] Déconnexion signalée au serveur maître")

        except Exception as e:
            self.log_signal.emit(f"[ATTENTION] Impossible de signaler la déconnexion: {e}")

    def obtenir_info_noeud(self, id_noeud):
        """Obtient les informations d'un nœud depuis le serveur maître"""
        try:
            socket_maitre = socket.socket()
            socket_maitre.settimeout(5)
            socket_maitre.connect((self.ip_maitre, self.port_maitre))
            message = f"OBTENIR_INFO_NOEUD;{id_noeud.upper()}"
            socket_maitre.send(message.encode())
            reponse = socket_maitre.recv(1024).decode()
            socket_maitre.close()

            if reponse != "NON_TROUVE" and reponse != "ERREUR_FORMAT":
                parties = reponse.split(":")
                if len(parties) >= 3:
                    return {
                        'type': parties[0],
                        'ip': parties[1],
                        'port': int(parties[2])
                    }
            return None

        except Exception as e:
            self.log_signal.emit(f"[ATTENTION] Erreur récupération info nœud: {e}")
            return None

    def obtenir_routeurs_du_maitre(self):
        """Obtient la liste des routeurs depuis le serveur maître"""
        try:
            socket_maitre = socket.socket()
            socket_maitre.connect((self.ip_maitre, self.port_maitre))
            socket_maitre.send(b"OBTENIR_ROUTEURS")
            donnees = socket_maitre.recv(4096).decode()
            socket_maitre.close()

            routeurs = {}
            for routeur_info in donnees.split("|"):
                if routeur_info:
                    parties = routeur_info.split(":")
                    if len(parties) >= 5:
                        id_routeur = parties[0]
                        ip = parties[1]
                        port = int(parties[2])
                        cle_cesar = int(parties[3])
                        routeurs[id_routeur] = {
                            'ip': ip,
                            'port': port,
                            'cle_publique': (cle_cesar, None)
                        }
            return routeurs

        except Exception as e:
            self.log_signal.emit(f"[ATTENTION] Erreur récupération routeurs: {e}")
            return {}

    def envoyer_message(self, destinataire, message, nombre_routeurs=3):
        """Envoie un message à un destinataire"""
        try:
            self.log_signal.emit("\n" + "=" * 50)
            self.log_signal.emit("[ENVOI] ENVOI DE MESSAGE")
            self.log_signal.emit("=" * 50)

            info_dest = self.obtenir_info_noeud(destinataire)
            if not info_dest or info_dest['type'] != 'client':
                self.log_signal.emit(f"[ERREUR] Destinataire {destinataire} invalide")
                return False

            routeurs = self.obtenir_routeurs_du_maitre()
            if len(routeurs) < nombre_routeurs:
                self.log_signal.emit(f"[ERREUR] Pas assez de routeurs: {len(routeurs)}/{nombre_routeurs}")
                return False

            ids_routeurs = list(routeurs.keys())
            chemin = random.sample(ids_routeurs, nombre_routeurs)
            self.log_signal.emit(f"[ROUTE] Chemin: {' → '.join(chemin)} → {destinataire}")

            message_chiffre = chiffrer_cesar(message.upper(), self.cle_cesar)
            self.log_signal.emit(f"[CHIFFREMENT] Message: '{message}' → chiffré: '{message_chiffre}'")

            donnees = message_chiffre
            
            self.log_signal.emit("[OIGNON] Construction de l'oignon:")
            for i in range(len(chemin) - 1, -1, -1):
                routeur_id = chemin[i]
                routeur_info = routeurs[routeur_id]

                est_dernier = (i == len(chemin) - 1)

                if est_dernier:
                    prochain_saut = destinataire
                else:
                    prochain_saut = chemin[i + 1]

                couche = encoder_couche_routage(prochain_saut, donnees, destinataire, est_dernier)

                if est_dernier:
                    self.log_signal.emit(f"  Couche FINALE {routeur_id}: DEST|{destinataire}|...")
                else:
                    self.log_signal.emit(f"  Couche {routeur_id}: NEXT|{prochain_saut}|...")

                donnees = chiffrer(couche, routeur_info['cle_publique'])
                self.log_signal.emit(f"    Chiffré → {donnees[:30]}...")

            premier = routeurs[chemin[0]]
            self.log_signal.emit(f"[TRANSMISSION] Envoi au routeur {chemin[0]} ({premier['ip']}:{premier['port']})")

            socket_routeur = socket.socket()
            socket_routeur.settimeout(10)
            socket_routeur.connect((premier['ip'], premier['port']))
            socket_routeur.send(donnees.encode())
            socket_routeur.close()

            self.log_signal.emit(f"[SUCCES] Message envoyé à {destinataire} via {nombre_routeurs} routeurs")
            return True

        except Exception as e:
            self.log_signal.emit(f"[ERREUR] Erreur envoi: {e}")
            return False

    def stop(self):
        """Arrête le thread"""
        self.running = False
        if self.serveur_socket:
            try:
                self.serveur_socket.close()
            except:
                pass
        self.supprimer_du_maitre()
        self.quit()
        self.wait()


class ConsoleWidget(QTextEdit):
    """Widget personnalisé pour la console"""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 10))
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        self.setPalette(palette)

    def append_message(self, message):
        """Ajoute un message avec coloration syntaxique"""
        if "[SUCCES]" in message:
            color = "#4CAF50"
        elif "[ERREUR]" in message:
            color = "#F44336"
        elif "[ATTENTION]" in message or "[ATTENTE]" in message:
            color = "#FF9800"
        elif "[INIT]" in message:
            color = "#2196F3"
        elif "[ENVOI]" in message or "[RECEPTION]" in message:
            color = "#9C27B0"
        elif "[CHIFFREMENT]" in message or "[OIGNON]" in message:
            color = "#FFC107"
        elif "[ROUTE]" in message or "[TRANSMISSION]" in message:
            color = "#00BCD4"
        elif "[DECONNEXION]" in message or "[ECOUTE]" in message:
            color = "#E91E63"
        elif "[ENREGISTREMENT]" in message:
            color = "#3F51B5"
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


class ClientGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Client Sécurisé")
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # ========== SECTION 1: CONNEXION ==========
        connexion_group = QGroupBox("CONNEXION AU SERVEUR")
        connexion_layout = QGridLayout()

        connexion_layout.addWidget(QLabel("Nom Client:"), 0, 0)
        self.nom_input = QLineEdit()
        self.nom_input.setPlaceholderText("Ex: ALICE")
        self.nom_input.setMaximumWidth(200)
        connexion_layout.addWidget(self.nom_input, 0, 1)

        connexion_layout.addWidget(QLabel("Port Client:"), 1, 0)
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Ex: 7100")
        self.port_input.setMaximumWidth(200)
        connexion_layout.addWidget(self.port_input, 1, 1)

        connexion_layout.addWidget(QLabel("IP Serveur:"), 2, 0)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Ex: 10.128.200.14")
        self.ip_input.setMaximumWidth(200)
        connexion_layout.addWidget(self.ip_input, 2, 1)

        connexion_layout.addWidget(QLabel("Port Serveur:"), 3, 0)
        self.port_serveur_input = QLineEdit()
        self.port_serveur_input.setText("9000")
        self.port_serveur_input.setMaximumWidth(200)
        connexion_layout.addWidget(self.port_serveur_input, 3, 1)

        self.connect_btn = QPushButton("Se Connecter")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.connect_btn.clicked.connect(self.connecter_client)
        connexion_layout.addWidget(self.connect_btn, 4, 0)

        self.deconnect_btn = QPushButton("Se Déconnecter")
        self.deconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.deconnect_btn.clicked.connect(self.deconnecter_client)
        self.deconnect_btn.setEnabled(False)
        connexion_layout.addWidget(self.deconnect_btn, 4, 1)

        self.status_label = QLabel("Non connecté")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold; font-size: 12px;")
        connexion_layout.addWidget(self.status_label, 5, 0, 1, 2)

        connexion_group.setLayout(connexion_layout)
        main_layout.addWidget(connexion_group)

        # ========== SECTION 2: ENVOI DE MESSAGE ==========
        message_group = QGroupBox("ENVOYER UN MESSAGE")
        message_layout = QGridLayout()

        message_layout.addWidget(QLabel("Destinataire:"), 0, 0)
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Ex: BOB")
        self.dest_input.setMaximumWidth(200)
        message_layout.addWidget(self.dest_input, 0, 1)

        message_layout.addWidget(QLabel("Nombre de Routeurs:"), 0, 2)
        self.nb_routeurs_input = QSpinBox()
        self.nb_routeurs_input.setRange(1, 10)
        self.nb_routeurs_input.setValue(3)
        self.nb_routeurs_input.setMaximumWidth(100)
        message_layout.addWidget(self.nb_routeurs_input, 0, 3)

        message_layout.addWidget(QLabel("Message:"), 1, 0)
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(80)
        self.message_input.setPlaceholderText("Tapez votre message ici...")
        message_layout.addWidget(self.message_input, 1, 1, 1, 3)

        self.send_btn = QPushButton("Envoyer")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.send_btn.clicked.connect(self.envoyer_message)
        self.send_btn.setEnabled(False)
        message_layout.addWidget(self.send_btn, 2, 0, 1, 4)

        message_group.setLayout(message_layout)
        main_layout.addWidget(message_group)

        # ========== SECTION 3: AFFICHAGE DES LOGS ==========
        logs_group = QGroupBox("JOURNAL D'ACTIVITÉ")
        logs_layout = QVBoxLayout()

        self.console = ConsoleWidget()
        logs_layout.addWidget(self.console)

        logs_group.setLayout(logs_layout)
        main_layout.addWidget(logs_group)

    def connecter_client(self):
        """Connecte le client au serveur maître"""
        nom = self.nom_input.text().strip()
        port = self.port_input.text().strip()
        ip = self.ip_input.text().strip()
        port_serveur = self.port_serveur_input.text().strip()

        if not nom or not port or not ip:
            self.console.append_message("[ERREUR] Tous les champs sont requis")
            return

        try:
            port = int(port)
            port_serveur = int(port_serveur) if port_serveur else 9000

            self.nom_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.ip_input.setEnabled(False)
            self.port_serveur_input.setEnabled(False)
            self.connect_btn.setEnabled(False)
            
            self.client_thread = ClientThread(nom, port, ip, port_serveur)
            self.client_thread.log_signal.connect(self.console.append_message)
            self.client_thread.connected_signal.connect(self.on_connexion_resultat)
            self.client_thread.message_received_signal.connect(self.on_message_received)
            self.client_thread.finished.connect(self.on_client_finished)
            self.client_thread.start()

        except ValueError:
            self.console.append_message("[ERREUR] Port invalide")
            self.reactiver_connexion()
        except Exception as e:
            self.console.append_message(f"[ERREUR] {str(e)[:100]}")
            self.reactiver_connexion()

    def on_connexion_resultat(self, success):
        """Gère le résultat de la tentative de connexion"""
        if success:
            self.status_label.setText("Connecté")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")
            self.deconnect_btn.setEnabled(True)
            self.send_btn.setEnabled(True)
        else:
            self.console.append_message("[ERREUR] Échec de la connexion")
            self.reactiver_connexion()

    def reactiver_connexion(self):
        """Réactive les champs de connexion"""
        self.nom_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.ip_input.setEnabled(True)
        self.port_serveur_input.setEnabled(True)
        self.connect_btn.setEnabled(True)
        self.deconnect_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.status_label.setText("Non connecté")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold; font-size: 12px;")

    def deconnecter_client(self):
        """Déconnecte le client"""
        if self.client_thread:
            self.client_thread.stop()
            self.client_thread = None

        self.console.append_message("[DECONNEXION] Client déconnecté")
        self.reactiver_connexion()

    def on_message_received(self, adresse, message):
        """Gère la réception d'un message"""
        # Cette méthode est appelée quand un message est reçu
        # Vous pouvez ajouter du traitement spécifique ici si besoin
        pass

    def on_client_finished(self):
        """Appelé quand le thread client se termine"""
        self.console.append_message("[INFO] Thread client terminé")

    def envoyer_message(self):
        """Envoie un message"""
        if not self.client_thread or not self.client_thread.isRunning():
            self.console.append_message("[ERREUR] Non connecté")
            return

        destinataire = self.dest_input.text().strip().upper()
        message = self.message_input.toPlainText().strip()
        nb_routeurs = self.nb_routeurs_input.value()

        if not destinataire:
            self.console.append_message("[ERREUR] Destinataire requis")
            return

        if not message:
            self.console.append_message("[ERREUR] Message vide")
            return

        self.send_btn.setEnabled(False)
        self.send_btn.setText("Envoi en cours...")

        QTimer.singleShot(100, lambda: self._envoyer_message(destinataire, message, nb_routeurs))

    def _envoyer_message(self, destinataire, message, nb_routeurs):
        """Méthode pour envoyer le message (appelée après un délai)"""
        try:
            success = self.client_thread.envoyer_message(destinataire, message, nb_routeurs)
            if success:
                self.message_input.clear()
        except Exception as e:
            self.console.append_message(f"[ERREUR] Erreur d'envoi: {str(e)[:100]}")
        finally:
            self.send_btn.setEnabled(True)
            self.send_btn.setText("Envoyer")

    def closeEvent(self, event):
        """Gestion de la fermeture de la fenêtre"""
        if self.client_thread and self.client_thread.isRunning():
            self.client_thread.stop()
            self.client_thread.wait(2000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ClientGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
