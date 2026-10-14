import mysql.connector
import socket
import os #import autorisé pour detecter l'os
import subprocess #import autorisé pour faire les cmd dans le terminal


class BaseDonneesRouteur:
    def __init__(self):
        self.connexion = None
        self.host = "localhost"
        self.database = "routage_oignon"

        self.app_user = "utilisateur_routage2"
        self.app_password = "votre_mot_de_passe_fort"
        self.port_mysql = 3306

        self.is_windows = os.name == 'nt'

        print(f"[BD] Système détecté: {'Windows' if self.is_windows else 'Linux/Mac'}")
        print(f"[BD] IP locale détectée pour MySQL : {self._get_local_ip()}")
        print("[BD] Initialisation auto MariaDB...")

    # ------------------------------------------------------
    # 0. Méthode universelle pour créer utilisateur/base
    # ------------------------------------------------------
    def _initialisation_root_shell(self):
        """Méthode pour créer utilisateur/base (Linux: sudo mysql, Windows: mot de passe)."""
        print("[BD] Tentative d'initialisation de la base de données...")

        # --- LINUX/Mac (utilise sudo mysql) ---
        if not self.is_windows:
            print("[BD] Détection Linux/Mac. Création via 'sudo mysql'...")

            sql_commands = f"""
            CREATE USER IF NOT EXISTS '{self.app_user}'@'localhost' IDENTIFIED BY '{self.app_password}';
            GRANT ALL PRIVILEGES ON *.* TO '{self.app_user}'@'localhost';
            CREATE USER IF NOT EXISTS '{self.app_user}'@'%' IDENTIFIED BY '{self.app_password}';
            GRANT ALL PRIVILEGES ON *.* TO '{self.app_user}'@'%';
            FLUSH PRIVILEGES;
            CREATE DATABASE IF NOT EXISTS {self.database};
            """

            try:
                result = subprocess.run(
                    ['sudo', 'mysql', '-e', sql_commands],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode == 0:
                    print("[BD] Création via 'sudo mysql' réussie ✔")
                    return True
                else:
                    if "sudo: a password is required" in result.stderr:
                        print("\n[INFO] 'sudo' demande votre mot de passe utilisateur Linux.")
                        print("       Relancez et entrez votre mot de passe Linux quand sudo le demande.")
                    print(f"[ERREUR] sudo mysql: {result.stderr}")
                    return False

            except Exception as e:
                print(f"[ERREUR] Exécution sudo: {e}")
                return False

        # --- WINDOWS (demande mot de passe root) ---
        else:
            print("[BD] Détection Windows. Demande du mot de passe root...")
            root_password = input("[BD] Veuillez entrer le mot de passe MySQL root : ")

            try:
                root_conn = mysql.connector.connect(
                    host=self.host,
                    user="root",
                    password=root_password,
                    port=self.port_mysql,
                    auth_plugin='mysql_native_password'
                )
                print("[BD] Connexion root réussie ✔")

            except mysql.connector.Error as err:
                print(f"[ERREUR] Connexion root échouée : {err}")
                print("[INFO] Mot de passe incorrect ou service non démarré.")
                return False
                
            cursor = root_conn.cursor()
            try:
                print("[BD] Création de l'utilisateur et de la base...")

                commands = [
                    f"CREATE USER IF NOT EXISTS '{self.app_user}'@'localhost' IDENTIFIED BY '{self.app_password}';",
                    f"GRANT ALL PRIVILEGES ON *.* TO '{self.app_user}'@'localhost';",
                    f"CREATE USER IF NOT EXISTS '{self.app_user}'@'%' IDENTIFIED BY '{self.app_password}';",
                    f"GRANT ALL PRIVILEGES ON *.* TO '{self.app_user}'@'%';",
                    "FLUSH PRIVILEGES;",
                    f"CREATE DATABASE IF NOT EXISTS {self.database};"
                ]

                for cmd in commands:
                    cursor.execute(cmd)

                root_conn.commit()
                cursor.close()
                root_conn.close()

                print("[BD] Utilisateur et base créés avec succès ✔")
                return True

            except mysql.connector.Error as err:
                print(f"[ERREUR] Exécution SQL: {err}")
                cursor.close()
                root_conn.close()
                return False

    # ------------------------------------------------------
    # 1. Connexion
    # ------------------------------------------------------
    def connecter(self):
        if not self._initialisation_root_shell():
            print("[ERREUR] Initialisation DB impossible.")
            return False

        try:
            self.connexion = mysql.connector.connect(
                host=self.host,
                user=self.app_user,
                password=self.app_password,
                database=self.database,
                port=self.port_mysql
            )
            print("[BD] Connexion utilisateur OK ✔")
        except Exception as e:
            print(f"[ERREUR] Connexion SQL utilisateur: {e}")
            try:
                self.connexion = mysql.connector.connect(
                    host=self.host,
                    user=self.app_user,
                    password=self.app_password,
                    port=self.port_mysql
                )
                cursor = self.connexion.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                cursor.execute(f"USE {self.database}")
                print("[BD] Base de données créée ✔")
            except Exception as e2:
                print(f"[ERREUR] Création de la base: {e2}")
                return False

        self.creer_tables()
        return True

    # ------------------------------------------------------
    # 2. Création tables (inchangé)
    # ------------------------------------------------------
    def creer_tables(self):
        curseur = self.connexion.cursor()

        curseur.execute("""
            CREATE TABLE IF NOT EXISTS noeuds (
                id_noeud VARCHAR(50) PRIMARY KEY,
                type_noeud VARCHAR(10),
                ip VARCHAR(50),
                port INT,
                cle_publique_e BIGINT,
                cle_publique_n BIGINT,
                statut VARCHAR(10) DEFAULT 'actif'
            );
        """)

        curseur.execute("""
            CREATE TABLE IF NOT EXISTS table_routage (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_routeur VARCHAR(50),
                destination VARCHAR(50),
                prochain_saut VARCHAR(50),
                ip_suivante VARCHAR(50),
                port_suivant INT
            );
        """)

        self.connexion.commit()
        print("[BD] Tables OK ✔")

    # ------------------------------------------------------
    # 3. Vérifier connexion (inchangé)
    # ------------------------------------------------------
    def est_connecte(self):
        return self.connexion is not None and self.connexion.is_connected()

    # ------------------------------------------------------
    # 4. Vérifier tables (inchangé)
    # ------------------------------------------------------
    def verifier_tables(self):
        try:
            if not self.est_connecte():
                return False

            curseur = self.connexion.cursor()
            curseur.execute("SHOW TABLES LIKE 'noeuds'")
            noeuds_ok = curseur.fetchone() is not None

            curseur.execute("SHOW TABLES LIKE 'table_routage'")
            routage_ok = curseur.fetchone() is not None

            return noeuds_ok and routage_ok
        except Exception as e:
            print(f"[ERREUR] Vérification tables: {e}")
            return False

    # ------------------------------------------------------
    # 5. Enregistrer noeud (inchangé)
    # ------------------------------------------------------
    def enregistrer_noeud(self, id_noeud, type_noeud, ip, port, e=None, n=None):
        try:
            if not self.est_connecte():
                print("[BD] Base de données non connectée")
                return False

            curseur = self.connexion.cursor()
            curseur.execute(
                """INSERT INTO noeuds (id_noeud, type_noeud, ip, port, cle_publique_e, cle_publique_n) 
                   VALUES (%s, %s, %s, %s, %s, %s) 
                   ON DUPLICATE KEY UPDATE ip=%s, port=%s, cle_publique_e=%s, cle_publique_n=%s, statut='actif'""",
                (id_noeud, type_noeud, ip, port, e, n, ip, port, e, n)
            )
            self.connexion.commit()
            print(f"[BD] Noeud {id_noeud} ({type_noeud}) enregistré - {ip}:{port}")
            return True
        except Exception as e:
            print(f"[ERREUR] Enregistrement noeud: {e}")
            return False

    # ------------------------------------------------------
    # 6. Obtenir info noeud (inchangé)
    # ------------------------------------------------------
    def obtenir_info_noeud(self, id_noeud):
        try:
            if not self.est_connecte():
                return None

            curseur = self.connexion.cursor()
            curseur.execute(
                "SELECT type_noeud, ip, port, cle_publique_e, cle_publique_n FROM noeuds WHERE id_noeud=%s AND statut='actif'",
                (id_noeud,)
            )
            resultat = curseur.fetchone()
            if resultat:
                return {
                    'type': resultat[0],
                    'ip': resultat[1],
                    'port': resultat[2],
                    'cle_publique': (resultat[3], resultat[4]) if resultat[3] and resultat[4] else None
                }
            return None
        except Exception as e:
            print(f"[ERREUR] Récupération noeud: {e}")
            return None

    # ------------------------------------------------------
    # 7. Obtenir tous routeurs (inchangé)
    # ------------------------------------------------------
    def obtenir_tous_routeurs(self):
        try:
            if not self.est_connecte():
                return []

            curseur = self.connexion.cursor()
            curseur.execute(
                "SELECT id_noeud, ip, port, cle_publique_e, cle_publique_n FROM noeuds WHERE type_noeud='routeur' AND statut='actif'"
            )

            return [
                {
                    'id': ligne[0],
                    'ip': ligne[1],
                    'port': ligne[2],
                    'cle_publique': (ligne[3], ligne[4])
                }
                for ligne in curseur.fetchall()
            ]
        except Exception as e:
            print(f"[ERREUR] Récupération routeurs: {e}")
            return []

    # ------------------------------------------------------
    # 8. Obtenir tous clients (inchangé)
    # ------------------------------------------------------
    def obtenir_tous_clients(self):
        try:
            if not self.est_connecte():
                return []

            curseur = self.connexion.cursor()
            curseur.execute(
                "SELECT id_noeud, ip, port FROM noeuds WHERE type_noeud='client' AND statut='actif'"
            )

            return [
                {'id': ligne[0], 'ip': ligne[1], 'port': ligne[2]}
                for ligne in curseur.fetchall()
            ]
        except Exception as e:
            print(f"[ERREUR] Récupération clients: {e}")
            return []

    # ------------------------------------------------------
    # 9. Ajouter règle routage (inchangé)
    # ------------------------------------------------------
    def ajouter_regle_routage(self, id_routeur, destination, prochain_saut, ip_suivante, port_suivant):
        try:
            if not self.est_connecte():
                return False

            curseur = self.connexion.cursor()
            curseur.execute(
                "INSERT INTO table_routage (id_routeur, destination, prochain_saut, ip_suivante, port_suivant) "
                "VALUES (%s, %s, %s, %s, %s)",
                (id_routeur, destination, prochain_saut, ip_suivante, port_suivant)
            )
            self.connexion.commit()
            print(f"[BD] Règle routage ajoutée: {id_routeur} -> {destination} via {prochain_saut}")
            return True
        except Exception as e:
            print(f"[ERREUR] Ajout règle routage: {e}")
            return False

    # ------------------------------------------------------
    # 10. Obtenir IP locale (inchangé)
    # ------------------------------------------------------
    @staticmethod
    def _get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"


bd = BaseDonneesRouteur()
