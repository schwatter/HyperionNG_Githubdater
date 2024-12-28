# -*- coding: utf-8 -*-

"""    Update HyperionNG direct from github actions    """	

__progname__    = "HyperionNG_Githubdater"
__version__     = "1.0"
__author__      = "schwatter"
__date__        = "2024-12-26"

import os
import requests
from bs4 import BeautifulSoup
import zipfile

# GitHub-Token (ersetze durch deinen persönlichen Token mit Zugriff auf öffentliche Repos)
TOKEN = "ghp_yourToken"

# URL der GitHub-Actions-Seite
BASE_URL = "https://github.com"
ACTIONS_URL = "https://github.com/hyperion-project/hyperion.ng/actions"
MAX_PAGES = 2  # Maximale Anzahl der Seiten, die durchsucht werden
MAX_DOWNLOADS = 2  # Maximale Anzahl an Downloads, die gesucht werden
artifact_name = "debian_buster_armv7"  # Name des gesuchten Artifacts

# Header für die GitHub-API-Anfragen
HEADERS = {
    "Authorization": "Bearer {}".format(TOKEN),
    "Accept": "application/vnd.github.v3+json",
}

# Funktion zum Extrahieren von Workflow-Links
def get_workflow_links(page_url):
    response = requests.get(page_url)
    if response.status_code != 200:
        print("Fehler beim Abrufen der Seite:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    workflow_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Überprüfen, ob der Link "actions/runs/" enthält
        if "/actions/runs/" in href:
            # Wenn der Link auf "/workflow" endet, überspringen wir ihn
            if href.endswith("/workflow"):
                continue
            # Andernfalls fügen wir den Link der Liste hinzu
            workflow_links.append(BASE_URL + href)
    
    # Rückgabe der Liste der Links ohne Duplikate
    return workflow_links

# Funktion zum Prüfen eines Workflow-Runs auf das spezifische Artifact
def check_artifact(run_url, artifact_name):
    print "Pruefe Workflow: {}".format(run_url)
    response = requests.get(run_url)
    if response.status_code != 200:
        print "Fehler beim Abrufen der Workflow-Seite: {}".format(response.status_code)
        return False

    # Nach dem Suchbegriff suchen
    if artifact_name in response.text:
        print "Suchbegriff '{}' gefunden auf der Seite: {}".format(artifact_name, run_url)
        return True
    return False

# Funktion zum Herunterladen des Artifacts
def download_artifact(owner, repo, run_id, artifact_name):
    url = "https://api.github.com/repos/{}/{}/actions/runs/{}/artifacts".format(owner, repo, run_id)
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print "Fehler beim Abrufen der Artifacts: {}".format(response.status_code)
        return

    data = response.json()
    artifacts = data.get("artifacts", [])
    for artifact in artifacts:
        if artifact.get("name") == artifact_name:
            download_url = artifact.get("archive_download_url")
            if download_url:
                download_response = requests.get(download_url, headers=HEADERS)
                if download_response.status_code == 200:
                    # Speichern im /tmp Verzeichnis
                    file_name = "/tmp/{}.zip".format(artifact_name)
                    with open(file_name, "wb") as f:
                        f.write(download_response.content)
                    print "Artifact wurde erfolgreich heruntergeladen: {}".format(file_name)
                    extract_zip(file_name)  # ZIP entpacken
                else:
                    print "Fehler beim Herunterladen des Artifacts: {}".format(download_response.status_code)
            else:
                print "Keine gueltige Download-URL gefunden."
            return
    print "Kein Artifact mit dem Namen '{}' gefunden.".format(artifact_name)

# Funktion zum Entpacken der ZIP-Datei
def extract_zip(zip_file):
    try:
        print("Entpacke ZIP-Datei: {}".format(zip_file))
        
        # Überprüfen, ob die ZIP-Datei existiert
        if not os.path.exists(zip_file):
            print("Die Datei {} existiert nicht.".format(zip_file))
            return

        # Öffnen der ZIP-Datei und Entpacken
        zip_ref = zipfile.ZipFile(zip_file, 'r')
        # Entpacken in das /tmp Verzeichnis
        zip_ref.extractall("/tmp")
        zip_ref.close()
        
        print("ZIP-Datei erfolgreich entpackt.")
    except Exception as e:
        print("Fehler beim Entpacken der ZIP-Datei: {}".format(e))

# Funktion zum Entpacken und Installieren des Archivs
def install_file():
    # Suchen nach *.tar.gz-Dateien in /tmp
    tar_files = [f for f in os.listdir("/tmp") if f.endswith(".tar.gz")]
    if not tar_files:
        print "Keine .tar.gz Dateien gefunden in /tmp."
        return

    # Auswahl der Datei vom Benutzer
    print "\nGefundene .tar.gz Dateien in /tmp:"
    for idx, file in enumerate(tar_files, start=1):
        print "{}. {}".format(idx, file)

    try:
        choice = int(raw_input("\nWaehle eine Nummer zum Installieren (0 zum Abbrechen): "))
        if choice == 0:
            print "Abgebrochen."
        elif 1 <= choice <= len(tar_files):
            selected_file = tar_files[choice - 1]
            os.system("/etc/init.d/hyperion stop")
            # Entpacken des Archives
            tar_file_path = os.path.join("/tmp", selected_file)
            os.system("tar -xvf {} -C /tmp/".format(tar_file_path))
            # Entfernen des alten Verzeichnisses und Kopieren des neuen
            os.system("rm -rf /usr/share/hyperion")
            os.system("cp -r /tmp/share/hyperion /usr/share")
            print "Installation abgeschlossen. Bitte mache einen vollstaendigen Neustart."
            os.system("rm -rf /tmp/bin")
            os.system("rm -rf /tmp/share")
            os.system("rm -rf /tmp/debian_buster_armv7.zip")
        else:
            print "Ungueltige Auswahl."
    except ValueError:
        print "Ungueltige Eingabe."

# Hauptprogramm
def main():
    print "Suche nach Workflows..."
    current_page = 1
    workflow_links = []
    workflows_with_artifacts = []

    while current_page <= MAX_PAGES and len(workflows_with_artifacts) < MAX_DOWNLOADS:
        # Holen der Links von der aktuellen Seite
        page_url = "{}?page={}".format(ACTIONS_URL, current_page)
        print "Durchsuche Seite {}: {}".format(current_page, page_url)
        page_workflows = get_workflow_links(page_url)

        if not page_workflows:
            print "Keine Workflows auf Seite {} gefunden.".format(current_page)
            break

        # Workflows durchgehen und prüfen, ob der gesuchte Artifact-Name vorhanden ist
        for link in page_workflows:
            if check_artifact(link, artifact_name):
                # Run-ID extrahieren
                run_id = link.split("/")[-1]
                workflows_with_artifacts.append({
                    "run_id": run_id,
                    "link": link
                })
            
            # Wenn die maximale Anzahl von Downloads erreicht ist, abbrechen
            if len(workflows_with_artifacts) >= MAX_DOWNLOADS:
                break

        current_page += 1

    # Wenn Artifacts gefunden wurden, dem Nutzer eine Auswahl anbieten
    if workflows_with_artifacts:
        print "\nGefundene Workflows mit Artifact '{}':".format(artifact_name)
        for idx, workflow in enumerate(workflows_with_artifacts, start=1):
            print "{}. {}".format(idx, workflow["link"])

        # Auswahl vom Nutzer
        try:
            choice = int(raw_input("\nWaehle eine Nummer zum Herunterladen des Artifacts (0 zum Abbrechen): "))
            if choice == 0:
                print "Abgebrochen."
            elif 1 <= choice <= len(workflows_with_artifacts):
                selected_workflow = workflows_with_artifacts[choice - 1]
                print "Ausgewaehlter Workflow: {}".format(selected_workflow["link"])
                download_artifact("hyperion-project", "hyperion.ng", selected_workflow["run_id"], artifact_name)

                # Installation des heruntergeladenen Files
                print "Installiere heruntergeladenes Artifact..."
                # Menü für die Installation anzeigen
                install_choice = raw_input("Moechten Sie das heruntergeladene Artifact installieren? (1: Install, 0: Abbrechen): ")
                if install_choice == "1":
                    install_file()
                else:
                    print "Installation abgebrochen."
            else:
                print "Ungueltige Auswahl."
        except ValueError:
            print "Ungueltige Eingabe."
    else:
        print "Kein Artifact mit dem Namen '{}' in den Workflows gefunden.".format(artifact_name)

if __name__ == "__main__":
    main()
