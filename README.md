# Cataclysm DDA Telegram Bot, Changelog Announcer, and Data Downloader

This repository contains three main components:

*   **CataBot:** A Telegram bot that provides information about the game Cataclysm: Dark Days Ahead (CDDA). It uses pre-processed game data to allow users to search for items, crafting recipes, monster information, and more.
*   **Changelog Announcer:** A tool that monitors the Cataclysm: DDA GitHub repository for new releases and automatically announces them to a specified Telegram chat.
*   **Download Data:** A module responsible for downloading and processing all Cataclysm DDA game definitions (items, recipes, monsters, etc.) into a structured JSON format. This data is then utilized by `CataBot` for its search functionalities.

## CataBot

CataBot is a Telegram bot designed to provide helpful information for players of Cataclysm: Dark Days Ahead.

### Features

*   **Game Information Search:** Look up details about in-game items, crafting recipes, monster stats, and more.
*   **Release Updates:** Get notifications about new game releases (can be combined with the Changelog Announcer).

### Setup

1.  **Download game data:**
    *   `CataBot` relies on game data (items, recipes, monsters, etc.) that is processed by the `download_data` module. Ensure you have run this module at least once to generate the necessary data files.
    *   See the `## Download Data` section for instructions on how to run it (`python -m download_data`).
2.  **Clone the repository:**
    ```bash
    git clone git@github.com:Tairesh/catabot.git
    cd catabot 
    ```
3.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *Note: On Windows, the activation command is `venv\Scripts\activate`.*
4.  **Install dependencies (within the activated venv):**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Configure the bot token:**
    *   Navigate to the `config/` directory.
    *   Create a file named `token.txt` (you can copy `config/samples/token.txt` as a template).
    *   Paste your Telegram bot token into this file. You can obtain a token by talking to the [BotFather](https://t.me/botfather) on Telegram.
6.  **Run the bot (from the repository root, with venv active):**
    ```bash
    python -m catabot
    ```

### Usage Examples

Once the bot is running and you've added it to your Telegram chat, you can use the following commands:

*   `/search <query>` or `/s <query>`: Search for an item, monster, or craft. 
    *   Example: `/search spear`
*   `/item <query>` or `/i <query>`: Specifically search for an item.
    *   Example: `/item survivor_suit`
*   `/craft <query>` or `/c <query>` or `/recipe <query>` or `/r <query>`: Search for a crafting recipe.
    *   Example: `/craft makeshift_knife`
*   `/disassemble <query>` or `/disasm <query>` or `/d <query>` or `/uncraft <query>` or `/u <query>`: Search for items that can be disassembled from the given item.
    *   Example: `/disassemble radio`
*   `/monster <query>` or `/mob <query>` or `/m <query>`: Search for a monster.
    *   Example: `/monster zombie_cop`
*   `/release` or `/get_release`: Get information about the latest game release.

## Changelog Announcer

The Changelog Announcer is a script that monitors the official Cataclysm: DDA GitHub repository for new releases. When a new release is detected, it automatically sends a notification message to a pre-configured Telegram chat.

### Setup

1.  **Prerequisites:** Ensure `catabot` is set up and you have its Telegram token and the target chat ID for announcements.
2.  **Configuration:** The script requires configuration for the GitHub repository to monitor (e.g., `CleverRaven/Cataclysm-DDA`) and Telegram details (bot token, chat ID). This configuration is usually done within the script (e.g., `changelog/github.py`, `changelog/tgbot.py`) or a separate configuration file. <!-- TODO: Verify and replace this with specific confirmed details -->
3.  **Dependencies:** Make sure all dependencies are installed (refer to `requirements.txt`).
4.  **Running the announcer:**
    ```bash
    python -m changelog
    ```
    This will typically check for new releases once and then exit. For continuous monitoring, you'll need to schedule it using a tool like `cron` (see Deployment section).

## Download Data

The `download_data` module is a crucial component responsible for fetching and processing game data from the Cataclysm: DDA repositories. It gathers all items, recipes, monster information, and other game definitions, then compiles them into a structured JSON file.

This JSON data is then used by `CataBot` to provide its search results. Therefore, you must run this module at least once before `CataBot` can function fully.

### Usage

To download/update the game data:

1.  **Ensure dependencies are installed:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the script:**
    ```bash
    python -m download_data
    ```
    This will download the latest game data and create/update the necessary JSON file(s) in a designated location (e.g., a `data/` directory or similar, which `CataBot` will then access).

It's recommended to re-run this script periodically to keep the game data used by `CataBot` up-to-date with the latest version of Cataclysm: DDA.

## Deployment

### Dependencies

All Python dependencies required for both `catabot` and the `changelog` announcer are listed in the `requirements.txt` file. Install them using pip:

```bash
pip install -r requirements.txt
```

### Scheduling Regular Tasks (Cron)

To automatically update game data and check for new releases, you can set up cron jobs to run the `download_data` and `changelog` scripts periodically within the project's virtual environment.

1.  **Ensure your virtual environment is set up** as described in the `CataBot` setup section (e.g., in a directory named `venv` within your project root).

2.  **Open your crontab for editing:**
    ```bash
    crontab -e
    ```

3.  **Add new lines to schedule the scripts.** For example, to run both scripts every hour:
    ```cron
    0 * * * * cd /path/to/your/repo && /path/to/your/repo/venv/bin/python -m download_data
    0 * * * * cd /path/to/your/repo && /path/to/your/repo/venv/bin/python -m changelog
    ```
    *   **Important:**
        *   Replace `/path/to/your/repo/` with the absolute path to the directory where you cloned this repository (e.g., `/home/user/catabot/`).
        *   The paths `/path/to/your/repo/venv/bin/python` assume your virtual environment is named `venv` and is located directly within your project's root directory. Adjust if your setup differs.
        *   The `crontab.example` file in this repository might contain further project-specific examples or considerations.

4.  **Save and exit the crontab editor.**

This setup will ensure that `download_data` fetches the latest game definitions and `changelog` checks for new game releases once every hour.

### Running CataBot as a Systemd Service

To ensure `catabot` runs continuously in the background and restarts automatically on failure or system reboot, you can set it up as a systemd service.

1.  **Locate the example service file:** An example systemd service configuration is provided in `systemctl-example.toml` or a similarly named file (e.g., `catabot.service`).

2.  **Review and customize the service file:**
    *   Open `systemctl-example.toml` (or the actual example file).
    *   **Crucially, this file is a template (`.toml` format suggests it might be for a tool that generates a `.service` file, or it might be a directly usable example if named `.service`). You will likely need to adjust paths and user information.**
    *   Pay attention to fields like:
        *   `Description`: A description of the service.
        *   `ExecStart`: This is the most important line. It should specify the command to start the bot, typically `python -m catabot`. **Ensure the path to your Python interpreter and the path to the `catabot` module are correct.** For example:
            ```
            ExecStart=/path/to/your/repo/venv/bin/python -m catabot
            ```
            (Adjust `/usr/bin/python3` and `/path/to/your/repo/` as needed.)
        *   `WorkingDirectory`: Set this to the root directory of the cloned repository.
        *   `User`: Specify the user the bot should run as (e.g., a dedicated service user, or your own user).
        *   `Group`: Specify the group for the bot process.
        *   `Restart`: Usually set to `always` or `on-failure` to ensure the bot restarts if it crashes.

3.  **Create the actual `.service` file:**
    *   If `systemctl-example.toml` is a template for a tool like `systemd-service-generator`, use that tool to generate the `.service` file.
    *   If it's a direct example (e.g., if there's a `catabot.service.example`), copy it to `/etc/systemd/system/catabot.service` and edit it:
        ```bash
        sudo cp systemctl-example.toml /etc/systemd/system/catabot.service # Adjust filename if needed
        sudo nano /etc/systemd/system/catabot.service 
        ```

4.  **Reload systemd daemon:**
    ```bash
    sudo systemctl daemon-reload
    ```

5.  **Enable the service to start on boot:**
    ```bash
    sudo systemctl enable catabot.service
    ```

6.  **Start the service immediately:**
    ```bash
    sudo systemctl start catabot.service
    ```

7.  **Check the service status:**
    ```bash
    sudo systemctl status catabot.service
    ```
    You can also view its logs using `journalctl -u catabot.service`.

## License

This project is licensed under the terms of the license specified in the `LICENSE` file in the root of this repository.
