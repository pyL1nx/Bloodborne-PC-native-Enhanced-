# **Bloodborne PC (Native Linux Port) - Enhanced Edition**

An optimized, native Linux build of the *Bloodborne* PC port featuring a custom C-based runtime achievement tracking engine and an interactive companion UI launcher.

---

## **Features**
* **Native Linux Performance:** Built to run directly through Vulkan with optimized frame pacing.
* **Custom C Trophy Hook:** Intercepts internal engine calls (`sceNpTrophyUnlockTrophy`) in `runtime_services.c` to accurately capture milestone and boss unlocks in real time[cite: 1].
* **JSON Serialization & UI Sync:** Automatically writes unlocks to a local JSON file (`achievements.json`), which seamlessly updates the companion launcher's trophy progress tracker[cite: 1].
* **FSR Support:** Integrated temporal upscaling options (FSR 3.1, FSR 4, and FSR 4.1.1) for high-fidelity rendering on Linux systems.

---

## **Prerequisites (Arch Linux)**
Before building the project, ensure you have the required build dependencies installed:
```bash
sudo pacman -S --needed base-devel cmake vulkan-headers glslang zydis xbyak miniz
```
## **Building & Running**

    Clone the repository:
    
    git clone [https://github.com/pyL1nx/Bloodborne-PC-native-Enhanced-.git](https://github.com/pyL1nx/Bloodborne-PC-native-Enhanced-.git)
    cd Bloodborne-PC-native-Enhanced-

    Compile the engine:
    
    bash build.sh

    Launch the game and launcher:
    
    bash launcher/bb-launcher.sh

## **Project Structure**

    src/ - Core engine modifications, including the custom runtime_services.c achievement hook.

    launcher/ - Python-based companion UI for tracking trophies and configuring game options.

    tests/ - Backend verification and unit tests for achievement data logging.

## **License**

This project is licensed under the GNU General Public License v2.0 or later. See the LICENSE file for details.

Note: This repository contains code modifications only and does not include copyrighted game assets, system dumps (CUSA03173), or proprietary binaries.
