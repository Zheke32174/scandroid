# Scandroid Bridge Setup

This repository acts as a bridge between your device's filesystem and GitHub.

## Current Status
- **Snapshot**: `groot.html` contains a snapshot of the device's root directory.

## How to Update the Bridge
To update the snapshot from your device:

1.  **Generate Listing**: Open your browser on the device and navigate to `file:///`.
2.  **Save Page**: Save the page as `groot.html`.
3.  **Upload**: Commit and push the new `groot.html` to this repository.

## Future Improvements
- **Automated Sync**: A script could be added here to automatically generate and push this file.
- **Remote Access**: By enabling GitHub Pages, you can view this listing from anywhere (though links to local files will not work).

---

# Environment Restoration

This project uses a dev container for a persistent, reproducible Codespace environment.

## How to restore your environment

1. Open this repository in GitHub Codespaces or VS Code with the Dev Containers extension.
2. The `.devcontainer/devcontainer.json` file will automatically set up your environment.
3. Custom setup commands can be added to `.devcontainer/setup.sh`.
4. To add more tools or dependencies, edit `setup.sh` and rebuild the container.

## Tips
- Always commit your changes to keep your environment persistent.
- Use `setup.sh` for any customizations you want to persist across rebuilds.
