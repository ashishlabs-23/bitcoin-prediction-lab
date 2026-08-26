"""
scripts/deploy_firebase.py — Direct Firebase Hosting Deployment Engine
======================================================================
Deploys web frontend directly to Firebase Hosting using Google Cloud
Service Account credentials and official Firebase Hosting REST API v1beta1.
"""

import os
import sys
import json
import gzip
import hashlib
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Ensure utf-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ID = "btcognitive"
SITE_ID = "btcognitive"
PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service_account.json"))

SCOPES = [
    "https://www.googleapis.com/auth/firebase.hosting",
    "https://www.googleapis.com/auth/cloud-platform"
]


def get_auth_token():
    """Generates fresh OAuth2 access token from service account credentials."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Service account file not found at: {SERVICE_ACCOUNT_FILE}")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    creds.refresh(Request())
    return creds.token


def compute_sha256(file_path):
    """Computes SHA256 hex digest of file contents."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def deploy_to_firebase_hosting():
    """Executes full Firebase Hosting version creation, file upload, and release."""
    print("=" * 70)
    print("🚀 Initiating Direct Firebase Hosting Deployment for BTCognitive")
    print(f"   Project ID:  {PROJECT_ID}")
    print(f"   Site ID:     {SITE_ID}")
    print(f"   Public Dir:  {PUBLIC_DIR}")
    print("=" * 70)

    # 1. Authenticate
    print("\n[1/5] Authenticating via Google Cloud Service Account...")
    token = get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("  ✓ OAuth2 Token acquired successfully.")

    # 2. Collect files, gzip them, and calculate gzip hashes
    print("\n[2/5] Indexing web assets, applying gzip compression, and computing SHA-256 hashes...")
    file_map = {}  # "/path/to/file": gzipped_hash
    hash_to_gzipped_bytes = {}  # gzipped_hash: gzipped_bytes
    hash_to_rel_path = {}  # gzipped_hash: rel_path
    
    ignore_patterns = [".netlify", "node_modules", ".git", ".DS_Store"]

    for root, _, files in os.walk(PUBLIC_DIR):
        if any(ignored in root for ignored in ignore_patterns):
            continue
        for file in files:
            if file.startswith(".") or any(ignored in file for ignored in ignore_patterns):
                continue
            abs_path = os.path.join(root, file)
            rel_path = "/" + os.path.relpath(abs_path, PUBLIC_DIR).replace("\\", "/")
            
            with open(abs_path, "rb") as f:
                raw_bytes = f.read()
            
            gzipped_bytes = gzip.compress(raw_bytes, compresslevel=9)
            gzipped_hash = hashlib.sha256(gzipped_bytes).hexdigest()
            
            file_map[rel_path] = gzipped_hash
            hash_to_gzipped_bytes[gzipped_hash] = gzipped_bytes
            hash_to_rel_path[gzipped_hash] = rel_path
            
            print(f"  • {rel_path} ({len(raw_bytes):,} raw bytes -> {len(gzipped_bytes):,} gzip bytes, SHA256: {gzipped_hash[:12]}...)")

    # 3. Create a new Version on Firebase Hosting
    print("\n[3/5] Creating new Firebase Hosting version...")
    version_config = {
        "config": {
            "headers": [
                {
                    "glob": "**",
                    "headers": {
                        "X-Content-Type-Options": "nosniff",
                        "X-Frame-Options": "DENY",
                        "Referrer-Policy": "strict-origin-when-cross-origin"
                    }
                }
            ],
            "rewrites": [
                {
                    "glob": "**",
                    "path": "/index.html"
                }
            ]
        }
    }
    
    create_ver_url = f"https://firebasehosting.googleapis.com/v1beta1/sites/{SITE_ID}/versions"
    res = requests.post(create_ver_url, headers=headers, json=version_config)
    if res.status_code not in (200, 201):
        print(f"❌ Failed to create version: {res.status_code} {res.text}")
        sys.exit(1)
    
    version_data = res.json()
    version_name = version_data["name"]
    print(f"  ✓ Version created: {version_name}")

    # 4. Populate files to determine upload requirements
    print("\n[4/5] Populating files and uploading assets...")
    pop_url = f"https://firebasehosting.googleapis.com/v1beta1/{version_name}:populateFiles"
    pop_res = requests.post(pop_url, headers=headers, json={"files": file_map})
    if pop_res.status_code not in (200, 201):
        print(f"❌ Failed to populate files: {pop_res.status_code} {pop_res.text}")
        sys.exit(1)
    
    pop_data = pop_res.json()
    upload_url = pop_data.get("uploadUrl", "")
    upload_required = pop_data.get("uploadRequiredHashes", [])
    print(f"  • Files required for upload: {len(upload_required)} of {len(file_map)}")

    # Upload each required file (gzipped bytes)
    for file_hash in upload_required:
        rel_path = hash_to_rel_path[file_hash]
        gzipped_bytes = hash_to_gzipped_bytes[file_hash]
        target_upload_url = f"{upload_url}/{file_hash}"
        
        upload_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream"
        }
        u_res = requests.post(target_upload_url, headers=upload_headers, data=gzipped_bytes)
        if u_res.status_code not in (200, 201):
            print(f"❌ Failed to upload {rel_path}: {u_res.status_code} {u_res.text}")
            sys.exit(1)
        print(f"  ✓ Uploaded: {rel_path}")

    # Finalize version
    patch_url = f"https://firebasehosting.googleapis.com/v1beta1/{version_name}?update_mask=status"
    patch_res = requests.patch(patch_url, headers=headers, json={"status": "FINALIZED"})
    if patch_res.status_code != 200:
        print(f"❌ Failed to finalize version: {patch_res.status_code} {patch_res.text}")
        sys.exit(1)
    print("  ✓ Version state: FINALIZED")

    # 5. Release the version to live channel
    print("\n[5/5] Releasing version to production live channel...")
    release_url = f"https://firebasehosting.googleapis.com/v1beta1/sites/{SITE_ID}/releases?versionName={version_name}"
    rel_res = requests.post(release_url, headers=headers)
    if rel_res.status_code not in (200, 201):
        print(f"❌ Failed to release version: {rel_res.status_code} {rel_res.text}")
        sys.exit(1)
    
    release_data = rel_res.json()
    print("=" * 70)
    print("🎉 DEPLOYMENT SUCCESSFUL!")
    print(f"   Release Name: {release_data.get('name', 'N/A')}")
    print(f"   Live URL:     https://{SITE_ID}.web.app")
    print(f"   Alt Domain:   https://{SITE_ID}.firebaseapp.com")
    print("=" * 70)


if __name__ == "__main__":
    deploy_to_firebase_hosting()
