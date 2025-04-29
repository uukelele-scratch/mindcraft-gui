# mindcraft-gui
Installer + GUI for Mindcraft.

> [!NOTE]
> If you've noticed the mentions of "part 1 of the installer", it's because this is going to be distributed via an INNO setup file - the file will extract the `_internal` deps folder and `main.exe` to the installation folder.

## Build instructions [DEV]
1. Clone the repo:
    ```cmd
    git clone https://github.com/uukelele-scratch/mindcraft-gui.git && cd mindcraft-gui
    ```
2. Install requirements:
    ```cmd
    python -m pip install -r src/requirements.txt
    ```
    ###### You need to install requirements, so that PyInstaller can include them in the build.
3. Build:
    ```cmd
    .\build.bat
    ```
4. Run!
    ```cmd
    .\dist\main\main.exe
    ```

> [!NOTE]
> The app's configuration and other necessary data will be stored in `.\dist\main\` by default. However, once this is distributed via INNO Setup and installed to `Program Files` or `appdata`, it will be structured more like an actual Windows application.