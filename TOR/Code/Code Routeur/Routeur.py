import socket
import threading
import sys
from base_donnees import bd
from chiffrement import (
    generer_cles,
    dechiffrer,
    chiffrer,
    encoder_couche_routage,
    decoder_couche_routage
)


class Routeur:
    def __init__(self, id_routeur, port_routeur, ip_maitre, port_maitre=9000):
        self.id_routeur = id_routeur
        self.port_routeur = port_routeur
        self.ip_maitre = ip_maitre
        self.port_maitre = port_maitre
        self.serveur_running = True

        self.cle_publique, self.cle_privee = generer_cles()

        print(f"Routeur {id_routeur}: Clé César générée: {self.cle_publique[0]}")

    def cleanup(self):
        """Nettoie les ressources et supprime de la DB"""
        print(f"\n🧹 NETTOYAGE du routeur {self.id_routeur}")
        print(f"{'=' * 60}")

        try:
            if self.supprimer_du_maitre():
                print(f"✅ Routeur {self.id_routeur} nettoyé avec succès")
            else:
                print(f"⚠️  Échec avec le maître, tentative directe DB...")
                self.supprimer_directement_db()

        except Exception as e:
            print(f"❌ Erreur lors du nettoyage: {e}")

    def supprimer_du_maitre(self):
        """Informer le serveur maître que ce routeur se déconnecte"""
        try:
            print(f"  Connexion au maître {self.ip_maitre}:{self.port_maitre}...")
            socket_maitre = socket.socket()
            socket_maitre.settimeout(3)  # Timeout court

            socket_maitre.connect((self.ip_maitre, self.port_maitre))

            message = f"DECONNEXION_ROUTEUR;{self.id_routeur}"
            print(f"  Envoi: {message}")

            socket_maitre.send(message.encode())
            reponse = socket_maitre.recv(1024).decode()
            socket_maitre.close()

            print(f"  Réponse du maître: {reponse}")

            if reponse == "OK":
                print(f"  ✓ Déconnexion confirmée par le maître")
                return True
            else:
                print(f"  ❌ Réponse inattendue: {reponse}")
                return False

        except socket.timeout:
            print(f"  ⚠️ Timeout: Le maître ne répond pas")
            return False
        except ConnectionRefusedError:
            print(f"  ⚠️ Connexion refusée: Le maître est hors ligne")
            return False
        except Exception as e:
            print(f"  ⚠️ Erreur communication avec le maître: {e}")
            return False

    def supprimer_directement_db(self):
        """Supprime directement de la base de données"""
        try:
            print(f"  Tentative de connexion directe à la base...")

            if bd.connecter():
                curseur = bd.connexion.cursor()

                # 1. Mettre à jour le statut
                curseur.execute(
                    "UPDATE noeuds SET statut='inactif' WHERE id_noeud=%s",
                    (self.id_routeur,)
                )
                print(f"  ✓ Statut mis à 'inactif'")

                # 2. Supprimer les règles de routage
                curseur.execute(
                    "DELETE FROM table_routage WHERE id_routeur=%s OR destination=%s",
                    (self.id_routeur, self.id_routeur)
                )
                rows_deleted = curseur.rowcount
                print(f"  ✓ {rows_deleted} règles de routage supprimées")

                bd.connexion.commit()
                curseur.close()
                print(f"  ✓ Base de données mise à jour")
                return True
            else:
                print(f"  ❌ Impossible de connecter à la base")
                return False

        except Exception as e:
            print(f"  ❌ Erreur suppression DB: {e}")
            return False

    def enregistrer_aupres_maitre(self):
        """Enregistre le routeur auprès du serveur maître"""
        try:
            print(f"\n📡 Connexion au maître {self.ip_maitre}:{self.port_maitre}...")

            socket_maitre = socket.socket()
            socket_maitre.settimeout(10)
            socket_maitre.connect((self.ip_maitre, self.port_maitre))

            cle = self.cle_publique[0]
            message = f"ENREGISTRER_ROUTEUR;{self.id_routeur};{self.port_routeur};{cle};0"

            print(f"  Envoi: {message}")
            socket_maitre.send(message.encode())

            reponse = socket_maitre.recv(1024).decode()
            socket_maitre.close()

            print(f"  Réponse: {reponse}")

            if reponse == "OK":
                print(f"✅ Routeur {self.id_routeur} enregistré")
                return True
            else:
                print(f"❌ Erreur enregistrement: {reponse}")
                return False

        except socket.timeout:
            print(f"❌ Timeout: Serveur maître inaccessible")
            return False
        except ConnectionRefusedError:
            print(f"❌ Connexion refusée: Vérifiez que le serveur maître tourne")
            return False
        except Exception as e:
            print(f"❌ Erreur connexion au maître: {e}")
            return False

    def obtenir_info_noeud(self, id_noeud):
        """Récupère les informations d'un nœud depuis le serveur maître"""
        try:
            socket_maitre = socket.socket()
            socket_maitre.settimeout(5)
            socket_maitre.connect((self.ip_maitre, self.port_maitre))

            message = f"OBTENIR_INFO_NOEUD;{id_noeud.upper()}"
            socket_maitre.send(message.encode())
            reponse = socket_maitre.recv(1024).decode()
            socket_maitre.close()

            if reponse != "NON_TROUVE" and reponse != "ERREUR_FORMAT" and reponse != "ERREUR_BD":
                parties = reponse.split(":")
                if len(parties) >= 3:
                    return {
                        'type': parties[0],
                        'ip': parties[1],
                        'port': int(parties[2])
                    }
            return None

        except Exception as e:
            print(f"Routeur {self.id_routeur}: Erreur récupération info nœud: {e}")
            return None

    def traiter_message(self, donnees_chiffrees):
        """Traite un message oignon reçu"""
        print(f"\n{'=' * 60}")
        print(f"Routeur {self.id_routeur}: TRAITEMENT DU MESSAGE")
        print(f"{'=' * 60}")

        try:
            print(f"Données reçues (chiffrées): {donnees_chiffrees}")

            message_dechiffre = dechiffrer(donnees_chiffrees, self.cle_privee)
            print(f"Message déchiffré: {message_dechiffre}")

            type_couche, info1, info2 = decoder_couche_routage(message_dechiffre)

            if type_couche == "ERROR":
                print(f"❌ Format de message invalide")
                return False

            print(f"\nRésultat décodage:")
            print(f"  • Type: {type_couche}")

            if type_couche == "NEXT":
                prochain_saut = info1
                donnees_suivantes = info2
                print(f"  • Prochain saut: {prochain_saut}")
                print(f"  • Données chiffrées: {donnees_suivantes[:30]}...")

                print(f"\n🔄 TRANSMISSION: Envoi à {prochain_saut}")
                info_prochain = self.obtenir_info_noeud(prochain_saut)
                if info_prochain:
                    print(f"  Routeur trouvé: {info_prochain['ip']}:{info_prochain['port']}")
                    success = self.transmettre_au_routeur(info_prochain['ip'], info_prochain['port'],
                                                          str(donnees_suivantes))
                    if success:
                        print(f"  ✅ Message transmis à {prochain_saut}")
                    else:
                        print(f"  ❌ Échec de transmission à {prochain_saut}")
                    return success
                else:
                    print(f"  ❌ Nœud {prochain_saut} non trouvé")
                    return False

            elif type_couche == "DEST":
                destination = info1
                message_final = info2
                print(f"  ⚠️  DESTINATION FINALE VISIBLE: {destination}")
                print(f"  • Message: {message_final[:50]}...")

                print(f"\n🔔 DERNIER SAUT: Livraison à {destination}")
                info_client = self.obtenir_info_noeud(destination)
                if info_client:
                    print(f"  Client trouvé: {info_client['ip']}:{info_client['port']}")
                    success = self.livrer_message_client(info_client['ip'], info_client['port'], str(message_final))
                    if success:
                        print(f"  ✅ Message livré à {destination}")
                    else:
                        print(f"  ❌ Échec de livraison à {destination}")
                    return success
                else:
                    print(f"  ❌ Client {destination} non trouvé")
                    return False

        except Exception as e:
            print(f"\n❌ ERREUR dans traiter_message: {e}")
            return False

    def transmettre_au_routeur(self, ip_suivant, port_suivant, donnees_chiffrees):
        """Transmet un message au routeur suivant"""
        try:
            print(f"  Connexion à {ip_suivant}:{port_suivant}...")
            socket_suivant = socket.socket()
            socket_suivant.settimeout(10)
            socket_suivant.connect((ip_suivant, port_suivant))

            print(f"  Envoi de {len(donnees_chiffrees)} caractères...")
            socket_suivant.send(donnees_chiffrees.encode())
            socket_suivant.close()
            return True

        except Exception as e:
            print(f"  ❌ Erreur transmission: {e}")
            return False

    def livrer_message_client(self, ip_client, port_client, message_texte):
        """Livré un message au client final"""
        try:
            print(f"  Connexion au client {ip_client}:{port_client}...")
            socket_client = socket.socket()
            socket_client.settimeout(10)
            socket_client.connect((ip_client, port_client))

            print(f"  Livraison du message ({len(message_texte)} caractères)...")
            socket_client.send(message_texte.encode())
            socket_client.close()
            return True

        except Exception as e:
            print(f"  ❌ Erreur livraison: {e}")
            return False

    def demarrer_serveur(self):
        """Démarre le serveur du routeur"""
        serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serveur.bind(('0.0.0.0', self.port_routeur))
        serveur.listen(10)

        serveur.settimeout(1.0)

        print(f"\n{'=' * 60}")
        print(f"ROUTEUR {self.id_routeur} DÉMARRÉ")
        print(f"Port: {self.port_routeur}")
        print(f"Clé César: {self.cle_publique[0]}")
        print(f"Maître: {self.ip_maitre}:{self.port_maitre}")
        print(f"{'=' * 60}")
        print("En attente de messages... (Ctrl+C pour arrêter)")
        print(f"{'=' * 60}\n")

        while self.serveur_running:
            try:
                connexion, adresse = serveur.accept()
                print(f"\n Connexion de {adresse[0]}:{adresse[1]}")

                donnees = connexion.recv(4096).decode().strip()
                if donnees:
                    print(f"   Message reçu ({len(donnees)} caractères)")

                    thread = threading.Thread(
                        target=self.traiter_message,
                        args=(donnees,)
                    )
                    thread.daemon = True
                    thread.start()
                    print(f"   Thread démarré")

                connexion.close()

            except socket.timeout:
                continue
            except KeyboardInterrupt:
                print(f"\n Interruption par l'utilisateur")
                break
            except Exception as e:
                if self.serveur_running:
                    print(f" Erreur acceptation: {e}")
                continue

        serveur.close()
        print(f"\n Serveur {self.id_routeur} arrêté")
        
        self.cleanup()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python routeur.py <id_routeur> <port_routeur> <ip_maitre>")
        print("Exemple: python routeur.py R1 7100 10.128.200.14")
        sys.exit(1)

    id_routeur = sys.argv[1]
    port_routeur = int(sys.argv[2])
    ip_maitre = sys.argv[3]

    print(f" Initialisation du routeur {id_routeur}")
    print(f"   Port: {port_routeur}")
    print(f"   Maître: {ip_maitre}:9000")

    routeur = None
    
    try:
        routeur = Routeur(id_routeur, port_routeur, ip_maitre)

        if routeur.enregistrer_aupres_maitre():
            routeur.demarrer_serveur()
        else:
            print(f" Échec de l'enregistrement")

    except KeyboardInterrupt:
        print(f"\n  Interruption avant démarrage")
        if routeur:
            routeur.cleanup()
    except Exception as e:
        print(f"\n Erreur fatale: {e}")
        if routeur:
            routeur.cleanup()
