import socket
import sys
import os
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QFileDialog, QMessageBox

# ------------
# -VARIABLE CLE SECRETE-
# ------------

SECRET_KEY = "cle_secrete"

# ------------
# -FONCTION CHARGER LE CSS-
# ------------

def ChargerLeCSS(fichier):
    try:
        with open(fichier, 'r') as rd:
            return rd.read()
    except FileNotFoundError:
        return ""

# ------------
# -FENÊTRE DE CONNEXION-
# ------------

class LoginWindow(QtWidgets.QWidget):
    login_successful = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Connexion")
        self.setStyleSheet(ChargerLeCSS("main.css"))

        self.user_label = QtWidgets.QLabel("Login :", self)
        self.user_input = QtWidgets.QLineEdit(self)

        self.password_label = QtWidgets.QLabel("Mot de Passe :", self)
        self.password_input = QtWidgets.QLineEdit(self)
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        self.login_button = QtWidgets.QPushButton("Se connecter", self)
        self.login_button.clicked.connect(self.verifier_login)

        layout = QtWidgets.QGridLayout()
        layout.setSpacing(15)
        layout.addWidget(self.user_label, 0, 0)
        layout.addWidget(self.user_input, 0, 1)
        layout.addWidget(self.password_label, 1, 0)
        layout.addWidget(self.password_input, 1, 1)
        layout.addWidget(self.login_button, 2, 0, 1, 2)
        self.setLayout(layout)

    def verifier_login(self):
        user = self.user_input.text()
        password = self.password_input.text()
        if user == "user" and password == "password":
            self.login_successful.emit()
            self.close()
        else:
            QMessageBox.critical(self, "Erreur", "Login ou mot de passe incorrect")

# ------------
# -FONCTION GUI-
# ------------

class Interface_Application(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.user_correct = "user"
        self.password_correct = "password"
        self.thread = None
        self.worker = None

    def init_ui(self):
        self.setWindowTitle('SAE3.02')
        self.setStyleSheet(ChargerLeCSS('main.css'))

        self.ip_label = QtWidgets.QLabel('IP du serveur maitre  :')
        self.ip_input = QtWidgets.QLineEdit(self)
        self.ip_input.setText('localhost')

        self.port_label = QtWidgets.QLabel('Port du serveur maitre  :')
        self.port_input = QtWidgets.QLineEdit(self)
        self.port_input.setText('12345')

        self.envoie_button = QtWidgets.QPushButton('Envoyer le programme', self)
        self.envoie_button.clicked.connect(self.Envoie_Programme)

        self.resultat_text = QtWidgets.QTextEdit(self)
        self.resultat_text.setReadOnly(True)

        grille = QtWidgets.QGridLayout()
        grille.setSpacing(15)
        grille.addWidget(self.ip_label, 3, 0)
        grille.addWidget(self.ip_input, 3, 1)
        grille.addWidget(self.port_label, 4, 0)
        grille.addWidget(self.port_input, 4, 1)
        grille.addWidget(self.envoie_button, 6, 3, 1, 2)
        grille.addWidget(self.resultat_text, 1, 3, 5, 2)

        self.setLayout(grille)

    def Envoie_Programme(self):
        self.envoie_button.setEnabled(False)

        ip_serveur = self.ip_input.text()
        port_serveur = int(self.port_input.text())

        options = QFileDialog.Option.DontUseNativeDialog
        chemin_fichier, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionnez le programme",
            "",
            "Tous les fichiers (*)",
            options=options
        )

        if not chemin_fichier:
            self.envoie_button.setEnabled(True)
            return

        try:
            with open(chemin_fichier, "rb") as f:
                programme = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de lire le fichier : {str(e)}")
            self.envoie_button.setEnabled(True)
            return

        _, extension_fichier = os.path.splitext(chemin_fichier)
        language_code = extension_fichier.lower().strip('.')

        self.resultat_text.clear()
        self.resultat_text.append("En attente du résultat...\n")

        self.thread = QtCore.QThread()
        self.worker = Worker(ip_serveur, port_serveur, programme, language_code)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.mettre_a_jour_resultat.connect(self.mettre_a_jour_resultat)
        self.worker.finished.connect(self.arret)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

# ------------
# -FONCTION METTRE A JOUR LE RESULTAT SUR LA GUI-
# ------------

    def mettre_a_jour_resultat(self, data):
        existing_text = "\n".join(line.strip() for line in self.resultat_text.toPlainText().splitlines())
        if data.strip() not in existing_text:
            self.resultat_text.append(data.strip())
            self.resultat_text.ensureCursorVisible()

# ------------
# -FONCTION STOP-
# ------------

    def arret(self):
        self.envoie_button.setEnabled(True)
        self.thread.quit()
        self.thread.wait()
        self.thread = None
        self.worker = None

# ------------
# -CLASSE WORKER POUR LA GESTION RÉSEAU-
# ------------

class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    mettre_a_jour_resultat = QtCore.pyqtSignal(str)

    def __init__(self, ip_serveur, port_serveur, programme, language_code):
        super().__init__()
        self.ip_serveur = ip_serveur
        self.port_serveur = port_serveur
        self.programme = programme
        self.language_code = language_code
        self.messages_affiches = set()  

    def run(self):
        try:
            socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.mettre_a_jour_resultat.emit("Connexion au serveur...")
            socket_client.connect((self.ip_serveur, self.port_serveur))
            socket_client.settimeout(300)  

            self.mettre_a_jour_resultat.emit("Envoi de l'en-tête...")
            header = f"{SECRET_KEY}:{self.language_code}:{len(self.programme)}".encode()
            socket_client.sendall(header)

            ack = socket_client.recv(1024).decode()
            if ack != "HEADER_RECUE":
                raise Exception("Problème lors de l'envoi de l'en-tête.")

            self.mettre_a_jour_resultat.emit("Programme envoyé. En attente de réponse...")
            socket_client.sendall(self.programme)

            result = b''
            while True:
                data = socket_client.recv(4096)
                if not data:  
                    break

                decoded_data = data.decode()
                if decoded_data == "ATTENTE":
                    if decoded_data not in self.messages_affiches:  
                        self.messages_affiches.add(decoded_data)
                elif decoded_data == "":
                    break
                else:
                    result += data
                    self.mettre_a_jour_resultat.emit(decoded_data)  

            if result:
                self.mettre_a_jour_resultat.emit(result.decode())
            else:
                self.mettre_a_jour_resultat.emit("Aucun résultat reçu du serveur.")
        except socket.timeout:
            self.mettre_a_jour_resultat.emit("Le serveur ne répond pas. Timeout expiré.")
        except Exception as e:
            self.mettre_a_jour_resultat.emit(f"Une erreur est survenue : {str(e)}")
        finally:
            try:
                socket_client.close()
            except Exception:
                pass
            self.finished.emit()



# ------------
# -FONCTION MAIN-
# ------------

def main():
    app = QtWidgets.QApplication(sys.argv)

    login_window = LoginWindow()
    interface_app = Interface_Application()

    login_window.login_successful.connect(interface_app.show)
    login_window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
