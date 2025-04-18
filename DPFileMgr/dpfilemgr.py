#! /usr/bin/env python3
#IBM DataPower Support 2025 DataPower File Manager v1.0 - Dominic Micale dmmicale (at) us.ibm.com
#Python3 required, Python 3.13.3 tested.
#1) Connect to DataPower using Rest Management Interface with command arguments (url eg. https://192.168.0.2, port eg. 5554)
#2) Identify available files to download or upload based on domain and subdir command arguments.  Default setting is to download only.  --upload-path will specify a file or dir.

import os
import requests
import base64
import argparse


def get_auth_header(user, password):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def parse_selection(sel, total):
    sel = sel.strip().lower()
    if sel == "all":
        return list(range(total))
    parts = [p.strip() for p in sel.split(",")]
    chosen = set()
    for p in parts:
        if "-" in p:
            a, b = p.split("-", 1)
            try:
                start, end = int(a) - 1, int(b) - 1
            except ValueError:
                continue
            for i in range(max(0, start), min(end, total - 1) + 1):
                chosen.add(i)
        else:
            try:
                idx = int(p) - 1
            except ValueError:
                continue
            if 0 <= idx < total:
                chosen.add(idx)
    return sorted(chosen)


def download_file(base_url, port, headers, verify_ssl, href, domain):
    url = f"{base_url}:{port}{href}"
    print(f"▶️  Downloading {url}")
    r = requests.get(url, headers=headers, verify=verify_ssl)
    r.raise_for_status()

    try:
        data = r.json()
    except ValueError:
        raw = r.content
        rel = href.split(f"/mgmt/filestore/{domain}/", 1)[-1]
        os.makedirs(os.path.dirname(rel), exist_ok=True)
        with open(rel, "wb") as f:
            f.write(raw)
        print(f"  ✅ saved raw to {rel}")
        return

    fb = data.get("file", data)
    if isinstance(fb, dict):
        b64 = fb.get("value")
        name = fb.get("name", href)
    elif isinstance(fb, str):
        b64 = fb
        name = href
    else:
        print("  ⚠️ unexpected file format")
        return

    if not b64:
        print("  ⚠️ no base64 payload")
        return

    content = base64.b64decode(b64)
    rel = name.split(f"/mgmt/filestore/{domain}/", 1)[-1]
    os.makedirs(os.path.dirname(rel), exist_ok=True)
    with open(rel, "wb") as f:
        f.write(content)
    print(f"  ✅ saved {rel}")


def process_dir(base_url, port, headers, verify_ssl, domain, href, download_all):
    full = f"{base_url}:{port}{href}"
    print(f"\n▶️  Requesting {full}")
    r = requests.get(full, headers=headers, verify=verify_ssl)
    r.raise_for_status()
    data = r.json()

    loc = data["filestore"]["location"]
    locs = loc if isinstance(loc, list) else [loc]

    for l in locs:
        print(f"\n📂  {l['name']}  (files: {l.get('files',0)}, dirs: {l.get('directories',0)})")

        files = l.get("file")
        if isinstance(files, dict): files = [files]
        files = files or []

        if files:
            for i, f in enumerate(files, 1):
                print(f"  {i}. {f['name']}  → {base_url}:{port}{f['href']}")

            if download_all:
                indices = list(range(len(files)))
            else:
                choice = input("  Enter file #s to download (all, 1-3,5), or Enter to skip: ").strip()
                indices = parse_selection(choice, len(files)) if choice else []

            for idx in indices:
                download_file(base_url, port, headers, verify_ssl, files[idx]["href"], domain)

        subs = l.get("directory")
        if isinstance(subs, dict): subs = [subs]
        subs = subs or []
        for sd in subs:
            process_dir(base_url, port, headers, verify_ssl, domain, sd["href"], download_all)


def create_remote_dir(base_url, port, headers, verify_ssl, remote_href):
    url = f"{base_url}:{port}{remote_href}"
    name = os.path.basename(remote_href)
    payload = {"directory": {"name": name}}
    print(f"▶️  Creating directory {url}")
    r = requests.put(url, headers=headers, json=payload, verify=verify_ssl)
    if r.status_code < 300:
        print(f"  ✅ directory created: {remote_href}")
    else:
        print(f"  ⚠️ failed to create directory {remote_href}: {r.status_code} {r.text}")


def upload_file(base_url, port, headers, verify_ssl, local_path, remote_dir_href, overwrite, domain):
    filename = os.path.basename(local_path)
    file_url = f"{base_url}:{port}{remote_dir_href}/{filename}"
    with open(local_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {"file": {"name": filename, "content": b64}}
    if overwrite:
        print(f"▶️  PUT {file_url}")
        r = requests.put(file_url, headers=headers, json=payload, verify=verify_ssl)
    else:
        post_url = f"{base_url}:{port}{remote_dir_href}"
        print(f"▶️  POST {post_url}")
        r = requests.post(post_url, headers=headers, json=payload, verify=verify_ssl)
        if r.status_code == 409:
            print("  ⚠️ already exists, retrying with PUT")
            r = requests.put(file_url, headers=headers, json=payload, verify=verify_ssl)
    if r.status_code < 300:
        print(f"  ✅ uploaded {local_path} to {remote_dir_href}")
    else:
        print(f"  ⚠️ upload failed {r.status_code}: {r.text}")


def upload_directory(local_path, base_url, port, headers, verify_ssl, domain, remote_base, overwrite):
    # If it's a directory, create remote dir and recurse
    if os.path.isdir(local_path):
        dir_name = os.path.basename(local_path.rstrip(os.sep))
        remote_dir_href = f"{remote_base}/{dir_name}"
        create_remote_dir(base_url, port, headers, verify_ssl, remote_dir_href)
        for entry in os.listdir(local_path):
            entry_path = os.path.join(local_path, entry)
            upload_directory(entry_path, base_url, port, headers, verify_ssl, domain, remote_dir_href, overwrite)
    else:
        # it's a file
        upload_file(base_url, port, headers, verify_ssl, local_path, remote_base, overwrite, domain)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url",         default="https://dphost.com")
    p.add_argument("--port",        default="5554")
    p.add_argument("--domain",      default="default", help="Domain (default: 'default')")
    p.add_argument("--subdir",                                                           help="Start at this subdir")
    p.add_argument("--download-all",  action="store_true",               help="Download all files without prompting")
    p.add_argument("--upload-path",                                    help="Local file or dir to upload")
    p.add_argument("--overwrite",     action="store_true",               help="Overwrite existing files on upload")
    p.add_argument("--user",          required=True)
    p.add_argument("--password",      required=True)
    p.add_argument("--skip-ssl",      action="store_true")
    args = p.parse_args()

    headers    = get_auth_header(args.user, args.password)
    verify_ssl = not args.skip_ssl

    # If upload-path specified, do upload and exit
    if args.upload_path:
        target = args.subdir.rstrip(":") if args.subdir else "local"
        remote_base = f"/mgmt/filestore/{args.domain}/{target}"
        upload_directory(args.upload_path, args.url, args.port, headers, verify_ssl,
                         args.domain, remote_base, args.overwrite)
        return

    # Otherwise do download mode
    if args.subdir:
        sd   = args.subdir.rstrip(":")
        href = f"/mgmt/filestore/{args.domain}/{sd}"
        process_dir(args.url, args.port, headers, verify_ssl, args.domain, href, args.download_all)
    else:
        base_href = f"/mgmt/filestore/{args.domain}"
        r = requests.get(f"{args.url}:{args.port}{base_href}", headers=headers, verify=verify_ssl)
        r.raise_for_status()
        base = r.json()["filestore"]["location"]
        locs = base if isinstance(base, list) else [base]
        for loc in locs:
            nm   = loc["name"].rstrip(":")
            href = f"/mgmt/filestore/{args.domain}/{nm}"
            process_dir(args.url, args.port, headers, verify_ssl, args.domain, href, args.download_all)

if __name__ == "__main__":
    main()
