import sys
from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox, QDialog

def appui_conv():
    try:
        val = float(degre.text())
    except ValueError:
        zoneconv.setText("Erreur")
        return

    if choix.currentText() == "°C -> K":
        res = val + 273.15
    else:
        res = val - 273.15
    zoneconv.setText(f"{res:.2f}")

class AideDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aide - Conversion de Température")

        layout = QGridLayout()

        texte = QLabel(
            "💡 Utilisation du convertisseur :\n\n"
            "- Entrez une température dans le champ 'Température'.\n"
            "- Choisissez la conversion (°C -> K ou K -> °C).\n"
            "- Cliquez sur 'Convertir' pour voir le résultat.\n\n"
            "Formules :\n"
            "  °C -> K :  T(K) = T(°C) + 273.15\n"
            "  K -> °C :  T(°C) = T(K) - 273.15"
        )
        texte.setWordWrap(True)

        bouton_fermer = QPushButton("Fermer")
        bouton_fermer.clicked.connect(self.close)

        layout.addWidget(texte, 0, 0)
        layout.addWidget(bouton_fermer, 1, 0)

        self.setLayout(layout)

def ouvrir_aide():
    dlg = AideDialog()
    dlg.exec()

app = QApplication(sys.argv)
root = QWidget()
root.resize(600, 400)
root.setWindowTitle("Conversion de Température")
grid = QGridLayout()

choix = QComboBox()
choix.addItem("°C -> K")
choix.addItem("K -> °C")
temp = QLabel("Température :")
degre = QLineEdit()
c = QLabel("°C")
conv = QPushButton("Convertir")
conv.clicked.connect(appui_conv)
conversion = QLabel("Conversion :")
zoneconv = QLineEdit("")
zoneconv.setEnabled(False)
k = QLabel("K")
intero = QPushButton("?")
intero.clicked.connect(ouvrir_aide)

if choix.currentText() == "°C -> K":
    c.setText("°C")
    k.setText("K")
elif choix.currentText() == "K -> °C":
    c.setText("K")
    k.setText("°C")

grid.addWidget(temp, 1, 1)
grid.addWidget(degre, 1, 2)
grid.addWidget(c, 1, 3)
grid.addWidget(conv, 2, 2)
grid.addWidget(choix, 2, 3)
grid.addWidget(conversion, 3, 1)
grid.addWidget(zoneconv, 3, 2)
grid.addWidget(k, 3, 3)
grid.addWidget(intero, 4, 3)

root.setLayout(grid)
root.show()

sys.exit(app.exec())
