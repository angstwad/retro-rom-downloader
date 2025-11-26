import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin, unquote

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import track
from thefuzz import process

console = Console()


def run_checks():
    """
    Runs pre-flight checks to verify the presence of required system utilities.

    This function checks for the availability of `aria2c` and `unzip` in the system's
    PATH. It ensures that these tools are installed and can be executed. If any of the
    tools are not found, the process will terminate with an error message.

    Raises:
        SystemExit: If either `aria2c` or `unzip` commands are not installed or not in
        the system's PATH.
    """
    console.print("Running pre-flight checks...")
    try:
        subprocess.run(["which", "aria2c"], check=True, capture_output=True)
        console.print("[green]aria2c found.[/green]")
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            "[bold red]Error:[/ ] aria2c is not installed or not in your PATH. "
            "Please install it to continue."
        )
        sys.exit(1)
    try:
        subprocess.run(["which", "unzip"], check=True, capture_output=True)
        console.print("[green]unzip found.[/green]")
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            "[bold red]Error:[/ ] unzip is not installed or not in your PATH. "
            "Please install it to continue."
        )
        sys.exit(1)


def get_links(url: str) -> list[str]:
    """
    Fetches and extracts downloadable `.zip` file links from the given URL.

    This function makes an HTTP GET request to the provided URL, parses
    the HTML content, and finds all anchor (`<a>`) tags with `href`
    attributes. It filters the links to include only those pointing to
    `.zip` files and returns them as full absolute URLs.

    Args:
        url (str): The URL to fetch links from.

    Returns:
        list[str]: A list of absolute URLs pointing to `.zip` files.
    """
    console.print(f"Fetching links from [bold cyan]{url}[/bold cyan]...")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error fetching URL:[/ ] {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.endswith("/") and href.endswith(".zip"):
            decoded_href = unquote(href)
            links.append(urljoin(url, decoded_href))

    console.print(f"Found {len(links)} potential files.")
    return links


def read_games_list(file_path: str) -> list[str]:
    """Reads a list of games from a text file."""
    console.print(f"Reading games list from [bold cyan]{file_path}[/bold cyan]...")
    try:
        with open(file_path, "r") as f:
            games = [line.strip() for line in f if line.strip()]
        console.print(f"Found {len(games)} games in the list.")
        return games
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/] Games list file not found at {file_path}")
        return []


def get_canonical_name(filename: str) -> str:
    """
    Processes a filename to generate its canonical form by removing tags within parentheses and the
    `.zip` file extension.

    Args:
        filename (str): The name of the file to process.

    Returns:
        str: The canonical name after processing.
    """
    # Remove all tags in parentheses
    name = re.sub(r'\s*\([^)]*\)', '', filename)
    # Remove file extension
    name = name.replace(".zip", "").strip()
    return name


def build_canonical_map(links: list[str], region: str) -> dict[str, list[str]]:
    """
    Builds a canonical mapping of filenames to links filtered by a specific region.

    This function processes a list of links and organizes them into a dictionary,
    grouping them under their canonical names. Only links containing the specified
    region in their path are included in the mapping. For each canonical name, a
    list of corresponding links is stored.

    Args:
        links: List of strings representing file links to be processed.
        region: A string representing the region to filter the links.

    Returns:
        A dictionary where the keys are canonical names (as determined by the
        `get_canonical_name` function) and the values are lists of links
        corresponding to those canonical names.
    """
    canonical_map = {}
    region_str = f"({region})"

    # First, filter links by region
    regional_links = [link for link in links if region_str in link]

    for link in regional_links:
        filename = link.split("/")[-1]
        canonical_name = get_canonical_name(filename)
        if canonical_name not in canonical_map:
            canonical_map[canonical_name] = []
        canonical_map[canonical_name].append(link)
    return canonical_map


def select_best_version(matches: list[str]) -> str | None:
    """
    Selects the best version from a list of matched filenames based on specific scoring rules.

    The selection process involves analyzing the filenames for specific patterns or tags
    that influence their scores. Penalties are applied for filenames containing certain tags
    like "(beta", "(proto", "(sample)", and boosts are given for revisions indicated as "(rev <number>)".
    The match with the highest score is selected as the best version.

    Args:
        matches (list[str]): A list of filenames represented as strings.

    Returns:
        str | None: The best matching filename as a string, or None if the input list is empty.
    """
    if not matches:
        return None

    best_match = None
    highest_score = -1

    for match in matches:
        score = 100
        filename = match.split("/")[-1].lower()

        # Penalize betas and other unwanted versions
        if any(tag in filename for tag in ["(beta", "(proto", "(sample)"]):
            score -= 50

        # Boost revisions
        rev_match = re.search(r"\(rev (\d+)\)", filename)
        if rev_match:
            score += int(rev_match.group(1))

        if score > highest_score:
            highest_score = score
            best_match = match

    return best_match


def filter_links(
        links: list[str], games: list[str], region: str
) -> tuple[list[str], set[str]]:
    """
    Filters a list of links based on a list of games and region specifications.

    This function processes a set of links and matches them against a list of games,
    using a fuzzy matching algorithm to identify the best matches for game names. It
    then selects the best-suited link version for each matched game.

    Args:
        links (list[str]): A list of link URLs to be filtered and matched.
        games (list[str]): A list of game titles to match against the links.
        region (str): A string representing the region for filtering and matching.

    Returns:
        tuple[list[str], set[str]]: A tuple where the first element is a list of
        filtered and deduplicated links and the second is a set of matched game
        titles.
    """
    canonical_map = build_canonical_map(links, region)
    final_links = []
    matched_games = set()
    canonical_names = list(canonical_map.keys())

    for game in track(games, description="Matching games..."):
        # Fuzzy match against the canonical names
        match = process.extractOne(game, canonical_names, score_cutoff=85)
        if match:
            best_canonical_name = match[0]
            all_versions = canonical_map[best_canonical_name]
            best_version = select_best_version(all_versions)
            if best_version:
                final_links.append(best_version)
                matched_games.add(game)

    # Remove duplicates
    return list(set(final_links)), matched_games


def write_links_to_file(links: list[str], file_path: str):
    """
    Writes a list of links to a specified file. Each link is written on a new line.

    This function opens the provided file in write mode and writes the links sequentially.
    It logs the number of links being written to the console for tracking purposes.

    Args:
        links (list[str]): A list of strings, where each string is a link to be written to the file.
        file_path (str): The path to the file where the links will be written.
    """
    console.print(f"Writing {len(links)} links to [bold cyan]{file_path}[/bold cyan]...")
    with open(file_path, "w") as f:
        for link in links:
            f.write(f"{link}\n")


def download_roms(aria2c_input_file: str, output_dir: str):
    """
    Downloads ROMs using aria2c with specified input file and output directory.

    This function serves as a wrapper around the aria2c command-line utility to
    download files as specified in an input file. It configures aria2c with
    multi-threaded connections for faster downloads. Additionally, it handles and
    alerts regarding errors during the execution of the downloading process.

    Args:
        aria2c_input_file (str): Path to the input file listing the URLs or
            download information for aria2c.
        output_dir (str): Path to the directory where the downloaded files will
            be saved.

    Raises:
        subprocess.CalledProcessError: If the aria2c command fails during execution.
        FileNotFoundError: If aria2c is not installed or not found in the system's
            PATH environment variable.
    """
    console.print(f"Starting download process with aria2c...")

    command = [
        "aria2c",
        "-i",
        aria2c_input_file,
        "-d",
        output_dir,
        "--console-log-level=warn",
        "-x",
        "16",
        "-s",
        "16",
        "-k",
        "1M",
    ]

    try:
        subprocess.run(command, check=True)
        console.print("[bold green]Download complete![/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error during download:[/ ] {e}")
    except FileNotFoundError:
        # This should not happen due to the pre-flight check, but as a fallback
        console.print(
            "[bold red]Error:[/ ] aria2c is not installed or not in your PATH. "
            "Please install it to continue."
        )


def unzip_and_cleanup(output_dir: str):
    """
    Unzips all .zip files in the specified directory and deletes the .zip files after successful extraction.

    Iterates through all files in the given directory, selecting those with a ".zip" extension. Each .zip file
    is extracted into the specified directory, and upon successful extraction, the original .zip file is
    deleted. If an error occurs during the extraction process, an error message is displayed without
    interrupting the processing of other files.

    Args:
        output_dir (str): Path to the directory containing .zip files to be extracted.

    Raises:
        subprocess.CalledProcessError: If the extraction of a zip file fails due to issues in the
                                       subprocess execution.
        Exception: Any other exception encountered during the unzipping or file handling process.
    """
    console.print(f"\n[bold green]Unzipping files in {output_dir}...[/bold green]")
    output_path = Path(output_dir)
    zip_files = [f for f in output_path.iterdir() if f.suffix == ".zip"]

    for zip_path in track(zip_files, description="Unzipping..."):
        try:
            # Unzip to the same directory
            subprocess.run(["unzip", "-o", str(zip_path), "-d", str(output_path)], check=True, capture_output=True)
            # Remove the zip file after successful extraction
            zip_path.unlink()
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error unzipping {zip_path.name}:[/] {e.stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            console.print(f"[bold red]An error occurred with {zip_path.name}:[/] {e}")

    console.print("[bold green]Unzipping and cleanup complete![/bold green]")


def get_clean_name_for_rename(filename: str) -> str:
    """
    Generates a clean and formatted name for renaming a file by processing its original name.

    This function removes the file extension, cleans up tags within parentheses,
    and adjusts specific patterns such as moving ", The" from the end to the
    beginning of the name.

    Args:
        filename (str): The name of the file, including its extension.

    Returns:
        str: The cleaned and formatted name for renaming the file.
    """
    # Remove file extension
    name_without_ext = Path(filename).stem

    # Remove all tags in parentheses
    clean_name = re.sub(r'\s*\([^)]*\)', '', name_without_ext)

    # Move ", The" to the beginning
    if clean_name.endswith(', The'):
        clean_name = "The " + clean_name[:-5]

    return clean_name.strip()


class CLI:
    args: argparse.Namespace

    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description="A script to download and manage ROMs.")
        subparsers = parser.add_subparsers(dest="command", required=True)

        # Download subcommand
        parser_download = subparsers.add_parser("download", help="Download ROMs.")
        parser_download.add_argument(
            "--games-list",
            required=True,
            help="The path to a text file containing a list of game titles, one per line.",
        )
        parser_download.add_argument(
            "--url",
            required=True,
            help="The URL of the ROM directory to scrape for download links.",
        )
        parser_download.add_argument(
            "--output-dir",
            default="downloads",
            help="The directory where the downloaded ROMs will be saved. Defaults to 'downloads'.",
        )
        parser_download.add_argument(
            "--region",
            default="USA",
            help="The preferred region for ROMs (e.g., 'USA', 'Europe'). Defaults to 'USA'.",
        )
        parser_download.add_argument(
            "--aria2c-input-file",
            default="aria2c-input.txt",
            help="The path to write the list of URLs for aria2c. Defaults to 'aria2c-input.txt'.",
        )
        parser_download.add_argument(
            "--no-unzip",
            action="store_true",
            help="Disable automatic unzipping of downloaded files.",
        )

        # Rename subcommand
        parser_rename = subparsers.add_parser("rename", help="Rename downloaded ROMs.")
        parser_rename.add_argument(
            "directory",
            help="The directory containing the files to rename.",
        )

        self.args = parser.parse_args()

    def rename_command(self):
        """The main logic for the 'rename' subcommand."""
        root_path = Path(self.args.directory)
        if not root_path.is_dir():
            console.print(f"[bold red]Error:[/ ] {self.args.directory} is not a valid directory.")
            return

        # Find all files recursively
        files_to_rename = [f for f in root_path.rglob('*') if f.is_file()]

        console.print(f"Found {len(files_to_rename)} files to process.")

        for old_path in track(files_to_rename, description="Renaming files..."):
            clean_name = get_clean_name_for_rename(old_path.name)
            new_path = old_path.with_name(clean_name + old_path.suffix)

            if old_path != new_path:
                try:
                    # Ensure parent directory exists
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)
                    console.print(f"Renamed [cyan]{old_path.name}[/] to [green]{new_path.name}[/]")
                except Exception as e:
                    console.print(f"[bold red]Error renaming {old_path.name}:[/ ] {e}")

    def download_command(self):
        """The main logic for the 'download' subcommand."""
        Path(self.args.output_dir).mkdir(parents=True, exist_ok=True)
        run_checks()

        console.print("[bold green]Starting ROM download process...[/bold green]")

        links = get_links(self.args.url)
        if not links:
            console.print("[bold red]No links found. Exiting.[/bold red]")
            return

        games = read_games_list(self.args.games_list)
        if not games:
            console.print("[bold red]No games found in the list. Exiting.[/bold red]")
            return

        matched_links, matched_games = filter_links(links, games, self.args.region)

        if not matched_links:
            console.print(
                "[bold yellow]No matching ROMs found for the given criteria.[/bold yellow]"
            )
            return

        console.print(f"Found {len(matched_links)} matching ROMs.")

        missing_games = set(games) - matched_games
        if missing_games:
            console.print("\n[bold yellow]Could not find matches for the following games:[/bold yellow]")
            for game in sorted(list(missing_games)):
                console.print(f"- {game}")

        write_links_to_file(matched_links, self.args.aria2c_input_file)
        download_roms(self.args.aria2c_input_file, self.args.output_dir)

        if not self.args.no_unzip:
            unzip_and_cleanup(self.args.output_dir)

    def run(self):
        self.parse_args()
        if self.args.command == "download":
            self.download_command()
        elif self.args.command == "rename":
            self.rename_command()


def main():
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
