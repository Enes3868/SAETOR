import random

def chiffrer_cesar(texte, cle):
    resultat = ""
    for char in texte:
        if char == '|':
            resultat += '|'
        elif 'A' <= char <= 'Z':
            code = ord(char) - ord('A')
            code_chiffre = (code + cle) % 26
            resultat += chr(code_chiffre + ord('A'))
        elif 'a' <= char <= 'z':
            code = ord(char) - ord('a')
            code_chiffre = (code + cle) % 26
            resultat += chr(code_chiffre + ord('a'))
        else:
            resultat += char
    return resultat


def dechiffrer_cesar(texte, cle):
    resultat = ""
    for char in texte:
        if char == '|':
            resultat += '|'
        elif 'A' <= char <= 'Z':
            code = ord(char) - ord('A')
            code_clair = (code - cle) % 26
            resultat += chr(code_clair + ord('A'))
        elif 'a' <= char <= 'z':
            code = ord(char) - ord('a')
            code_clair = (code - cle) % 26
            resultat += chr(code_clair + ord('a'))
        else:
            resultat += char
    return resultat


def generer_cles():
    cle = random.randint(1, 25)
    return (cle, None), (cle, None)


def encoder_couche_routage(prochain, donnees, destination, est_dernier=False):
    """
    Crée une couche de routage.

    Pour un routeur intermédiaire: NEXT|prochain_saut|donnees_chiffrees
    Pour le dernier routeur: DEST|destination|message_clair

    Pour compatibilité ascendante: si est_dernier=False, utilise l'ancien format
    """
    if est_dernier:
        return f"DEST|{destination}|{donnees}"
    else:
        return f"NEXT|{prochain}|{donnees}"


def decoder_couche_routage(chaine):
    """
    Décode une couche de routage.
    Supporte à la fois l'ancien et le nouveau format.
    """
    if not chaine or "|" not in chaine:
        return "ERROR", "", ""

    parties = chaine.split("|", 2)

    if len(parties) < 3:
        return "ERROR", "", ""

    if parties[0] == "NEXT":
        return "NEXT", parties[1], parties[2]
    elif parties[0] == "DEST":
        return "DEST", parties[1], parties[2]
    else:
        return "NEXT", parties[0], f"{parties[1]}|{parties[2]}"


def chiffrer(msg, pub):
    cle, _ = pub
    return chiffrer_cesar(str(msg), cle)


def dechiffrer(msg, priv):
    cle, _ = priv
    return dechiffrer_cesar(str(msg), cle)


def texte_vers_nombre_segmente(texte, taille=5):
    segments = []
    for i in range(0, len(texte), taille):
        segment = texte[i:i + taille]
        nombre = 0
        for char in segment:
            code = ord(char) - 32
            nombre = nombre * 95 + code
        segments.append(nombre)
    return segments


def nombre_vers_texte_segmente(segments):
    texte = ""
    for nombre in segments:
        if nombre == 0:
            continue
        segment = ""
        temp = nombre
        while temp > 0:
            temp, code = divmod(temp, 95)
            segment = chr(code + 32) + segment
        texte += segment

    return texte
