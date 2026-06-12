"""Download PDF files from Google Drive into a local directory.

Usage examples:
    python scripts/download_gdrive_pdfs.py --folder-id YOUR_FOLDER_ID
    python scripts/download_gdrive_pdfs.py --file-ids FILE_ID1,FILE_ID2 --out-dir data/gdrive
"""
import argparse
from pathlib import Path
from typing import List, Optional

from connectors.gdrive_connector import download_file, list_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download PDF files from Google Drive.")
    parser.add_argument("--folder-id", help="Google Drive folder ID containing PDFs.")
    parser.add_argument(
        "--file-ids",
        help="Comma-separated list of Drive file IDs to download instead of listing a folder.",
    )
    parser.add_argument(
        "--out-dir",
        default="data/gdrive",
        help="Local directory to save downloaded files. Default: data/gdrive",
    )
    parser.add_argument(
        "--credentials-json",
        help="Path to Google service account JSON credentials. If omitted, uses GOOGLE_APPLICATION_CREDENTIALS.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of files to list from the folder when folder-id is provided. Default: 100",
    )
    return parser.parse_args()


def choose_pdf_files(files: List[dict]) -> List[dict]:
    pdf_files = [f for f in files if f.get("mimeType") == "application/pdf"]
    return pdf_files


def download_files_by_ids(file_ids: List[str], out_dir: str, credentials_json: Optional[str]) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for file_id in file_ids:
        dest_path = Path(out_dir) / f"{file_id}.pdf"
        print(f"Downloading {file_id} -> {dest_path}")
        download_file(file_id, str(dest_path), credentials_json=credentials_json)
    print(f"Downloaded {len(file_ids)} file(s) to {out_dir}")


def download_folder_pdfs(folder_id: str, out_dir: str, credentials_json: Optional[str], limit: int) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    files = list_files(folder_id, credentials_json=credentials_json)
    if not files:
        print(f"No files found in folder {folder_id}")
        return

    pdf_files = choose_pdf_files(files)[:limit]
    if not pdf_files:
        print("No PDF files found in the provided folder.")
        return

    for file_info in pdf_files:
        file_id = file_info.get("id")
        name = file_info.get("name") or file_id
        safe_name = Path(name).name
        dest_path = Path(out_dir) / safe_name
        print(f"Downloading {name} ({file_id}) -> {dest_path}")
        download_file(file_id, str(dest_path), credentials_json=credentials_json)

    print(f"Downloaded {len(pdf_files)} PDF file(s) to {out_dir}")


def main() -> None:
    args = parse_args()
    if not args.folder_id and not args.file_ids:
        raise SystemExit("Provide either --folder-id or --file-ids")

    if args.file_ids:
        file_ids = [fid.strip() for fid in args.file_ids.split(",") if fid.strip()]
        if not file_ids:
            raise SystemExit("No valid file IDs provided")
        download_files_by_ids(file_ids, args.out_dir, args.credentials_json)
    else:
        download_folder_pdfs(args.folder_id, args.out_dir, args.credentials_json, args.limit)


if __name__ == "__main__":
    main()
