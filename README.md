# retro-rom-downloader

`retro-rom-downloader` was built to automate the process of downloading curated ROM collections
from [myrient.erista.me](https://myrient.erista.me). It takes a simple text file of game names, finds the best match
from a given Myrient directory, and downloads them for you.

It uses fuzzy matching to find the game you want and intelligently selects the best version (e.g., latest revision,
correct region) while avoiding bad dumps, betas, and prototypes. This allows you to download games for any system hosted
on Myrient (NES, SNES, Genesis, etc.) using just a simple list of game names.

## Features

* **Fuzzy Matching**: Finds games from a simple name, even if it's not a perfect match.
* **Smart Version Selection**: Automatically picks the best version of a game, preferring official releases and higher
  revisions.
* **Region Filtering**: Specify a region (like 'USA' or 'Europe') to get the right ROMs for your collection.
* **Bulk Downloading**: Uses `aria2c` for fast, parallel downloads.
* **Automatic Unzipping**: Extracts ROMs from their archives after download.
* **File Renaming**: Cleans up filenames to be neat and consistent.

## Prerequisites

Before you begin, you need to install a few command-line tools:

* **`aria2c`**: For downloading the files.
* **`unzip`**: For extracting the downloaded archives.

On macOS with [Homebrew](https://brew.sh), you can install them with:

```bash
brew install aria2 unzip
```

## Installation

This tool requires **Python 3.10 or higher**.

### With `uv` (Recommended)

First, install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, install the tool from GitHub:

```bash
uv tool install --from https://github.com/angstwad/retro-rom-downloader
```

### With `pipx`

```bash
pipx install git+https://github.com/angstwad/retro-rom-downloader.git
```

### With `pip`

```bash
pip install git+https://github.com/angstwad/retro-rom-downloader.git
```

## Usage

The tool is composed of two main commands: `download` to get the ROMs, and `rename` to clean up the filenames.

### The `top_lists` Directory

This project includes a `top_lists` directory containing curated lists of top games for various systems (NES, SNES, Genesis, etc.). These are plain text files with one game title per line. The script is designed to read just the game names; any extra text on the line, like scores or numbers, is ignored. You can easily create your own lists in the same format.

### Example Workflow: Downloading and Renaming a Collection

Here’s a complete workflow for downloading the top 100 Sega Genesis games and then cleaning up the filenames.

**Step 1: Download the Collection**

Use the `download` command, pointing to a game list and the corresponding URL on Myrient for that system's ROMs.

```bash
download-rom download \
  --games-list ./top_lists/genesis-top-100.txt \
  --output-dir ./genesis \
  --url 'https://myrient.erista.me/files/No-Intro/Sega%20-%20Mega%20Drive%20-%20Genesis/'
```

This will:
1.  Read the game names from `genesis-top-100.txt`.
2.  Scan the Myrient directory for matching files for the `USA` region (the default).
3.  Download the best-matched files into a new `genesis` directory.
4.  Automatically unzip the downloaded archives.

**Step 2: Rename and Clean Up**

After the download is complete, use the `rename` command on the output directory to standardize the filenames.

```bash
download-rom rename ./genesis
```

This will process all files in the `genesis` directory, renaming them from something like `Sonic the Hedgehog 2 (USA, Europe).md` to `Sonic the Hedgehog 2.md` and fixing titles like `"Aladdin (USA).md"` to `"Aladdin.md"`.

### Command Reference

#### `download`
Downloads ROMs based on a list of games.
```bash
download-rom download --games-list <path_to_games.txt> --output-dir <dir> --url <rom_url> [options]
```
*   `--games-list`: A text file with one game name per line.
*   `--output-dir`: The directory to save the ROMs.
*   `--url`: The Myrient URL to scrape for ROMs.
*   `--region`: The preferred region (e.g., `USA`, `Europe`). Defaults to `USA`.
*   `--no-unzip`: A flag to disable automatic unzipping.

#### `rename`
Cleans up the filenames of your downloaded ROMs.
```bash
download-rom rename <directory>
```

