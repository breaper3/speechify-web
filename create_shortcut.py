import os
import win32com.client

def create_shortcuts():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    bat_launcher = os.path.join(project_dir, 'launch_speechify.bat')
    icon_path = os.path.join(project_dir, 'speechify_local', 'static', 'speechify.ico')

    shell = win32com.client.Dispatch('WScript.Shell')

    destinations = []
    userprofile = os.environ.get('USERPROFILE', '')
    appdata = os.environ.get('APPDATA', '')

    onedrive_desktop = os.path.join(userprofile, 'OneDrive', 'Desktop')
    local_desktop = os.path.join(userprofile, 'Desktop')
    start_menu = os.path.join(appdata, 'Microsoft', 'Windows', 'Start Menu', 'Programs')

    for p in [onedrive_desktop, local_desktop, start_menu]:
        if p and os.path.exists(p) and p not in destinations:
            destinations.append(p)

    created = []
    for dest in destinations:
        lnk_path = os.path.join(dest, 'Speechify Local.lnk')
        try:
            shortcut = shell.CreateShortcut(lnk_path)
            shortcut.TargetPath = bat_launcher
            shortcut.WorkingDirectory = project_dir
            shortcut.IconLocation = f'{icon_path},0'
            shortcut.Description = 'Speechify Local - Neural Voice Reader'
            shortcut.WindowStyle = 1 # Normal window
            shortcut.Save()
            created.append(lnk_path)
            print(f'Created shortcut: {lnk_path}')
        except Exception as e:
            print(f'Error creating shortcut at {lnk_path}: {e}')

    return created

if __name__ == '__main__':
    create_shortcuts()
