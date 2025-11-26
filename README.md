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

The tool has two main commands: `download` and `rename`.

### `download`

This command downloads ROMs based on a list of games.

```bash
download-rom download --games-list <path_to_games.txt> --output-dir <dir> --url <rom_url>
```

**Arguments:**

* `--games-list`: A text file with one game name per line. See the `top_lists` directory for examples.
* `--output-dir`: The directory to save the ROMs.
* `--url`: The Myrient URL to scrape for ROMs.
* `--region`: The preferred region (e.g., `USA`, `Europe`). Defaults to `USA`.
* `--no-unzip`: A flag to disable automatic unzipping.

**Example:**

This command will download the top 100 NES games to the `nes` directory.

```bash
download-rom download --games-list ./top_lists/nes-top-100.txt --output-dir nes --url 'https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%20Entertainment%20System%20(Headered)/'
```

### `rename`

This command cleans up the filenames of your downloaded ROMs.

```bash
download-rom rename <directory>
```

**Example:**

```bash
download-rom rename ./nes
```

This will rename all files in the `nes` directory, removing tags like `(USA)` or `(Rev 1)` and cleaning up names (e.g.,
"Zelda II, The" becomes "The Zelda II").
