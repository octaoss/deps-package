#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import re
import glob
import gzip
import hashlib
import xml.etree.ElementTree as ET
import json

def sha256_checksum(data):
    return hashlib.sha256(data).hexdigest()

def get_repo_info():
    # Get repository owner and name from environment
    repo = os.environ.get("GITHUB_REPOSITORY", "octaoss/deps-package")
    parts = repo.split("/")
    if len(parts) == 2:
        return parts[0], parts[1]
    return "octaoss", "deps-package"

def download_packages():
    print("=== Downloading packages from GitHub Releases ===")
    
    # Ensure temp directories exist and are clean
    shutil.rmtree("temp_apt", ignore_errors=True)
    shutil.rmtree("temp_rpm", ignore_errors=True)
    os.makedirs("temp_apt", exist_ok=True)
    os.makedirs("temp_rpm", exist_ok=True)
    
    try:
        # Get list of all releases
        result = subprocess.run(
            ["gh", "release", "list", "--limit", "100", "--json", "tagName"],
            capture_output=True,
            text=True,
            check=True
        )
        releases = json.loads(result.stdout)
        print(f"Found {len(releases)} releases.")
    except Exception as e:
        print(f"Error fetching releases: {e}")
        return []

    downloaded_any = False
    for release in releases:
        tag = release["tagName"]
        print(f"Checking assets for release: {tag}")
        
        # Download Debian packages
        apt_dir = os.path.join("temp_apt", tag)
        os.makedirs(apt_dir, exist_ok=True)
        try:
            subprocess.run(
                ["gh", "release", "download", tag, "--pattern", "*.deb", "--dir", apt_dir],
                check=True
            )
            # Remove directory if empty
            if not os.listdir(apt_dir):
                os.rmdir(apt_dir)
            else:
                downloaded_any = True
                print(f"Downloaded Debian packages for {tag}")
        except subprocess.CalledProcessError:
            os.rmdir(apt_dir)
            
        # Download RPM packages
        rpm_dir = os.path.join("temp_rpm", tag)
        os.makedirs(rpm_dir, exist_ok=True)
        try:
            subprocess.run(
                ["gh", "release", "download", tag, "--pattern", "*.rpm", "--dir", rpm_dir],
                check=True
            )
            # Remove directory if empty
            if not os.listdir(rpm_dir):
                os.rmdir(rpm_dir)
            else:
                downloaded_any = True
                print(f"Downloaded RPM packages for {tag}")
        except subprocess.CalledProcessError:
            os.rmdir(rpm_dir)
            
    return downloaded_any

def generate_apt_repo(repo_owner, repo_name):
    print("=== Generating APT Repository ===")
    
    # Ensure debian structure exists
    debian_dir = "debian"
    shutil.rmtree(debian_dir, ignore_errors=True)
    os.makedirs(debian_dir, exist_ok=True)
    
    # Check if we have any debian packages
    deb_files = glob.glob("temp_apt/**/*.deb", recursive=True)
    if not deb_files:
        print("No Debian packages found.")
        return []

    # Run apt-ftparchive to scan packages
    try:
        result = subprocess.run(
            ["apt-ftparchive", "packages", "temp_apt"],
            capture_output=True,
            text=True,
            check=True
        )
    except Exception as e:
        print(f"Error running apt-ftparchive: {e}")
        return []

    blocks = result.stdout.strip().split("\n\n")
    arch_blocks = {}
    parsed_packages = []

    for block in blocks:
        if not block.strip():
            continue
            
        # Extract metadata
        pkg_name = re.search(r"^Package:\s*(.*)$", block, re.MULTILINE)
        version = re.search(r"^Version:\s*(.*)$", block, re.MULTILINE)
        arch = re.search(r"^Architecture:\s*(.*)$", block, re.MULTILINE)
        desc = re.search(r"^Description:\s*(.*)$", block, re.MULTILINE)
        
        if not (pkg_name and version and arch):
            continue
            
        pkg = pkg_name.group(1).strip()
        ver = version.group(1).strip()
        architecture = arch.group(1).strip()
        description = desc.group(1).strip() if desc else ""
        
        # Replace relative Filename with absolute GitHub Release URL
        # Filename format: temp_apt/<tag>/<filename>.deb
        filename_match = re.search(r"^Filename:\s*(temp_apt/([^/]+)/([^/\n]+))$", block, re.MULTILINE)
        if filename_match:
            full_match_str = filename_match.group(1)
            tag = filename_match.group(2)
            filename = filename_match.group(3)
            absolute_url = f"https://github.com/{repo_owner}/{repo_name}/releases/download/{tag}/{filename}"
            block = block.replace(f"Filename: {full_match_str}", f"Filename: {absolute_url}")
            
            parsed_packages.append({
                "name": pkg,
                "version": ver,
                "architecture": architecture,
                "description": description,
                "type": "deb",
                "url": absolute_url
            })
            
        if architecture not in arch_blocks:
            arch_blocks[architecture] = []
        arch_blocks[architecture].append(block)

    # Distribute 'all' packages to other architectures
    if 'all' in arch_blocks:
        all_packages = arch_blocks['all']
        for arch in list(arch_blocks.keys()):
            if arch != 'all':
                arch_blocks[arch].extend(all_packages)

    active_architectures = list(arch_blocks.keys())
    for arch, blocks in arch_blocks.items():
        arch_dir = os.path.join(debian_dir, "dists/stable/main/binary-", arch)
        # Fix path concat
        arch_dir = f"debian/dists/stable/main/binary-{arch}"
        os.makedirs(arch_dir, exist_ok=True)
        
        packages_content = "\n\n".join(blocks) + "\n"
        
        # Write Packages
        with open(os.path.join(arch_dir, "Packages"), "w") as f:
            f.write(packages_content)
            
        # Write Packages.gz
        subprocess.run(["gzip", "-fk", os.path.join(arch_dir, "Packages")], check=True)

    # Write release.conf
    architectures_str = " ".join(active_architectures)
    conf_content = f"""APT::FTPArchive::Release::Origin "Custom Linux Repository";
APT::FTPArchive::Release::Label "Custom Linux Repository";
APT::FTPArchive::Release::Suite "stable";
APT::FTPArchive::Release::Codename "stable";
APT::FTPArchive::Release::Architectures "{architectures_str}";
APT::FTPArchive::Release::Components "main";
APT::FTPArchive::Release::Description "Repository for custom Debian/Ubuntu packages";
"""
    os.makedirs(os.path.join(debian_dir, "conf"), exist_ok=True)
    with open(os.path.join(debian_dir, "conf/release.conf"), "w") as f:
        f.write(conf_content)
        
    # Generate Release file
    try:
        release_result = subprocess.run(
            ["apt-ftparchive", "-c", "conf/release.conf", "release", "dists/stable"],
            cwd=debian_dir,
            capture_output=True,
            text=True,
            check=True
        )
        with open(os.path.join(debian_dir, "dists/stable/Release"), "w") as f:
            f.write(release_result.stdout)
    except Exception as e:
        print(f"Error generating Release file: {e}")
        return parsed_packages

    # Sign Release if GPG key is present
    try:
        subprocess.run(
            ["gpg", "--yes", "-abs", "-o", "dists/stable/Release.gpg", "dists/stable/Release"],
            cwd=debian_dir,
            check=True
        )
        subprocess.run(
            ["gpg", "--yes", "--clearsign", "-o", "dists/stable/InRelease", "dists/stable/Release"],
            cwd=debian_dir,
            check=True
        )
        print("Successfully signed APT repository.")
    except Exception as e:
        print("GPG signing skipped or failed (GPG key may not be configured):", e)

    return parsed_packages

def generate_rpm_repo(repo_owner, repo_name):
    print("=== Generating RPM Repository ===")
    
    fedora_dir = "fedora"
    shutil.rmtree(fedora_dir, ignore_errors=True)
    os.makedirs(fedora_dir, exist_ok=True)
    
    # Gather RPMs and build tag mapping
    rpm_to_tag = {}
    rpm_files = glob.glob("temp_rpm/**/*.rpm", recursive=True)
    
    if not rpm_files:
        print("No RPM packages found.")
        return []

    # Copy all RPMs to fedora/ so createrepo_c can analyze them
    for rpm_path in rpm_files:
        parts = rpm_path.split(os.sep)
        if len(parts) >= 3:
            tag = parts[-2]
            filename = parts[-1]
            rpm_to_tag[filename] = tag
            shutil.copy2(rpm_path, os.path.join(fedora_dir, filename))

    # Run createrepo_c
    try:
        subprocess.run(["createrepo_c", "--no-database", fedora_dir], check=True)
    except Exception as e:
        print(f"Error running createrepo_c: {e}")
        return []

    # Post-process YUM metadata to point to absolute URLs
    repodata_dir = os.path.join(fedora_dir, "repodata")
    repomd_path = os.path.join(repodata_dir, "repomd.xml")
    
    if not os.path.exists(repomd_path):
        print("repomd.xml not generated!")
        return []

    # Parse and modify XML files
    tree = ET.parse(repomd_path)
    root = tree.getroot()
    
    ns = {"repo": "http://linux.duke.edu/metadata/repo"}
    ET.register_namespace("", "http://linux.duke.edu/metadata/repo")
    
    parsed_packages = []
    
    for data_elem in root.findall("repo:data", ns):
        data_type = data_elem.get("type")
        if data_type not in ["primary", "filelists", "other"]:
            continue
            
        location_elem = data_elem.find("repo:location", ns)
        if location_elem is None:
            continue
            
        relative_href = location_elem.get("href")
        gz_path = os.path.join(fedora_dir, relative_href)
        
        if not os.path.exists(gz_path):
            continue
            
        # Read and decompress
        with gzip.open(gz_path, "rb") as f:
            xml_content = f.read()
            
        xml_str = xml_content.decode("utf-8")
        
        # Extract metadata for the landing page (only once, from primary.xml)
        if data_type == "primary":
            # Simple parse of package names, versions, architectures
            # Since primary.xml is small and well-structured, we can extract them
            try:
                # Parse temporary ET to get package list
                temp_root = ET.fromstring(xml_content)
                temp_ns = {
                    "common": "http://linux.duke.edu/metadata/common",
                    "rpm": "http://linux.duke.edu/metadata/rpm"
                }
                for pkg_elem in temp_root.findall(".//common:package", temp_ns):
                    name_elem = pkg_elem.find("common:name", temp_ns)
                    arch_elem = pkg_elem.find("common:arch", temp_ns)
                    ver_elem = pkg_elem.find("common:version", temp_ns)
                    desc_elem = pkg_elem.find("common:description", temp_ns)
                    
                    if name_elem is not None and ver_elem is not None:
                        pkg_name = name_elem.text
                        pkg_arch = arch_elem.text if arch_elem is not None else "x86_64"
                        pkg_ver = ver_elem.get("ver")
                        if ver_elem.get("rel"):
                            pkg_ver += f"-{ver_elem.get('rel')}"
                        pkg_desc = desc_elem.text if desc_elem is not None else ""
                        
                        # Find filename
                        rpm_filename = None
                        loc_elem = pkg_elem.find("common:location", temp_ns)
                        if loc_elem is not None:
                            rpm_filename = os.path.basename(loc_elem.get("href"))
                            
                        if rpm_filename and rpm_filename in rpm_to_tag:
                            tag = rpm_to_tag[rpm_filename]
                            absolute_url = f"https://github.com/{repo_owner}/{repo_name}/releases/download/{tag}/{rpm_filename}"
                            parsed_packages.append({
                                "name": pkg_name,
                                "version": pkg_ver,
                                "architecture": pkg_arch,
                                "description": pkg_desc,
                                "type": "rpm",
                                "url": absolute_url
                            })
            except Exception as ex:
                print(f"Error parsing primary XML for landing page: {ex}")
        
        # Replace relative href with absolute URL
        for filename, tag in rpm_to_tag.items():
            old_href = f'href="{filename}"'
            new_href = f'href="https://github.com/{repo_owner}/{repo_name}/releases/download/{tag}/{filename}"'
            xml_str = xml_str.replace(old_href, new_href)
            
        modified_xml_content = xml_str.encode("utf-8")
        
        # Compress again
        temp_gz_path = gz_path + ".tmp"
        with gzip.open(temp_gz_path, "wb") as f:
            f.write(modified_xml_content)
            
        # Recalculate checksums and sizes
        uncompressed_size = len(modified_xml_content)
        uncompressed_sha = sha256_checksum(modified_xml_content)
        
        with open(temp_gz_path, "rb") as f:
            compressed_content = f.read()
        compressed_size = len(compressed_content)
        compressed_sha = sha256_checksum(compressed_content)
        
        os.replace(temp_gz_path, gz_path)
        
        # Update repomd.xml elements
        checksum_elem = data_elem.find("repo:checksum", ns)
        if checksum_elem is not None:
            checksum_elem.text = compressed_sha
            
        open_checksum_elem = data_elem.find("repo:open-checksum", ns)
        if open_checksum_elem is not None:
            open_checksum_elem.text = uncompressed_sha
            
        size_elem = data_elem.find("repo:size", ns)
        if size_elem is not None:
            size_elem.text = str(compressed_size)
            
        open_size_elem = data_elem.find("repo:open-size", ns)
        if open_size_elem is not None:
            open_size_elem.text = str(uncompressed_size)

    # Save the updated repomd.xml
    tree.write(repomd_path, encoding="utf-8", xml_declaration=True)

    # Sign repomd.xml if GPG key is present
    try:
        subprocess.run(
            ["gpg", "--yes", "--detach-sign", "--armor", "repodata/repomd.xml"],
            cwd=fedora_dir,
            check=True
        )
        print("Successfully signed RPM repository.")
    except Exception as e:
        print("GPG signing for RPM skipped or failed:", e)

    # Clean up RPM files so we don't commit them to git
    for filename in rpm_to_tag.keys():
        rpm_path = os.path.join(fedora_dir, filename)
        if os.path.exists(rpm_path):
            os.remove(rpm_path)

    return parsed_packages

def export_public_key():
    print("=== Exporting GPG Public Key ===")
    try:
        key_result = subprocess.run(
            ["gpg", "--list-keys", "--with-colons"],
            capture_output=True,
            text=True,
            check=True
        )
        
        key_id = None
        for line in key_result.stdout.splitlines():
            if line.startswith("pub:"):
                parts = line.split(":")
                if len(parts) >= 5:
                    key_id = parts[4]
                    break
                    
        if key_id:
            print(f"Found key ID: {key_id}")
            with open("public.key", "w") as f:
                subprocess.run(["gpg", "--export", "--armor", key_id], stdout=f, check=True)
            shutil.copy2("public.key", "debian/public.key")
            shutil.copy2("public.key", "fedora/public.key")
            print("Public key exported successfully.")
            return True
        else:
            print("No public GPG key found.")
    except Exception as e:
        print(f"Could not export public key: {e}")
    return False

def generate_client_configs(repo_owner, repo_name, has_gpg):
    print("=== Generating Client Configurations ===")
    repo_url = os.environ.get("REPO_URL", f"https://{repo_owner}.github.io/{repo_name}")
    
    # Generate Yum/Dnf .repo file
    repo_content = f"""[deps-{repo_name}]
name=Deps {repo_name} Repository
baseurl={repo_url}/fedora
enabled=1
gpgcheck=0
"""
    if has_gpg:
        repo_content = f"""[deps-{repo_name}]
name=Deps {repo_name} Repository
baseurl={repo_url}/fedora
enabled=1
gpgcheck=1
gpgkey={repo_url}/public.key
"""
    
    # Write both standard names
    with open("fedora/deps-oktanio.repo", "w") as f:
        f.write(repo_content)
    with open(f"fedora/deps-{repo_name}.repo", "w") as f:
        f.write(repo_content)
    print("Generated client configurations.")

def generate_landing_page(repo_owner, repo_name, packages, has_gpg):
    print("=== Generating Landing Page ===")
    repo_url = os.environ.get("REPO_URL", f"https://{repo_owner}.github.io/{repo_name}")
    
    # Sort packages by name
    packages = sorted(packages, key=lambda x: x["name"])
    
    deb_packages = [p for p in packages if p["type"] == "deb"]
    rpm_packages = [p for p in packages if p["type"] == "rpm"]
    
    # Pre-calculate strings for GPG and commands to prevent backslash/quote issues in f-strings
    if has_gpg:
        gpg_badge_html = f"""<div class="gpg-section">
            <h4>🔒 Signed Repository</h4>
            <p>This repository is signed with GPG for security. You can download the public key here: <a href="{repo_url}/public.key" target="_blank">public.key</a> or use the installation instructions below.</p>
        </div>"""
        ubuntu_key_cmd = f"curl -fsSL {repo_url}/public.key | sudo gpg --dearmor -o /etc/apt/keyrings/deps-{repo_name}.gpg"
        ubuntu_repo_cmd = f'echo "deb [signed-by=/etc/apt/keyrings/deps-{repo_name}.gpg] {repo_url}/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-{repo_name}.list'
    else:
        gpg_badge_html = ""
        ubuntu_key_cmd = "# Unsigned repository (less secure)"
        ubuntu_repo_cmd = f'echo "deb [trusted=yes] {repo_url}/debian stable main" | sudo tee /etc/apt/sources.list.d/deps-{repo_name}.list'

    # Pre-calculate package list HTML
    if not packages:
        empty_packages_html = "<p style='color: var(--text-secondary); text-align: center; padding: 2rem;'>No packages available in this repository yet.</p>"
    else:
        empty_packages_html = ""

    packages_html_list = []
    for p in packages:
        badge_class = "badge-deb" if p["type"] == "deb" else "badge-rpm"
        desc = p["description"] or "No description provided."
        packages_html_list.append(f"""
            <div class="package-card">
                <div class="package-info">
                    <h3>{p["name"]}</h3>
                    <p>{desc}</p>
                    <div class="package-meta">
                        <span class="badge {badge_class}">{p["type"]}</span>
                        <span class="badge badge-ver">{p["version"]}</span>
                        <span class="badge badge-arch">{p["architecture"]}</span>
                    </div>
                </div>
                <a href="{p["url"]}" class="download-btn" target="_blank">Download</a>
            </div>""")
    packages_html = "".join(packages_html_list)

    # HTML generation
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deps Package Repository</title>
    <style>
        :root {{
            --bg-color: #0b0f19;
            --container-bg: #151d30;
            --accent-color: #3b82f6;
            --accent-hover: #60a5fa;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --border-color: #1e293b;
            --code-bg: #0f172a;
            --success-color: #10b981;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: var(--container-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            padding: 2.5rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        }}
        
        header {{
            text-align: center;
            margin-bottom: 2.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
        }}
        
        h1 {{
            font-size: 2.25rem;
            font-weight: 800;
            background: linear-gradient(to right, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        
        h2 {{
            font-size: 1.5rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.5rem;
            color: #f3f4f6;
        }}
        
        .tabs {{
            display: flex;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1.5rem;
        }}
        
        .tab-btn {{
            background: none;
            border: none;
            color: var(--text-secondary);
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border-bottom: 2px solid transparent;
        }}
        
        .tab-btn:hover {{
            color: var(--text-primary);
        }}
        
        .tab-btn.active {{
            color: var(--accent-color);
            border-bottom-color: var(--accent-color);
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .instruction-step {{
            margin-bottom: 1.5rem;
        }}
        
        .instruction-step p {{
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #e2e8f0;
        }}
        
        .code-container {{
            position: relative;
            background-color: var(--code-bg);
            border-radius: 6px;
            border: 1px solid var(--border-color);
            margin-bottom: 1rem;
        }}
        
        pre {{
            padding: 1rem;
            overflow-x: auto;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 0.9rem;
            color: #cbd5e1;
        }}
        
        .copy-btn {{
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background-color: var(--container-bg);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .copy-btn:hover {{
            color: var(--text-primary);
            background-color: var(--border-color);
        }}
        
        .package-list {{
            margin-top: 2rem;
        }}
        
        .package-card {{
            background-color: var(--code-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.2s, border-color 0.2s;
        }}
        
        .package-card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-color);
        }}
        
        .package-info h3 {{
            font-size: 1.1rem;
            margin-bottom: 0.25rem;
            color: var(--text-primary);
        }}
        
        .package-info p {{
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }}
        
        .package-meta {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        
        .badge {{
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge-deb {{
            background-color: rgba(236, 72, 153, 0.15);
            color: #f472b6;
            border: 1px solid rgba(236, 72, 153, 0.3);
        }}
        
        .badge-rpm {{
            background-color: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}
        
        .badge-arch {{
            background-color: rgba(107, 114, 128, 0.15);
            color: #9ca3af;
            border: 1px solid rgba(107, 114, 128, 0.3);
        }}
        
        .badge-ver {{
            background-color: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        
        .download-btn {{
            background-color: var(--accent-color);
            color: white;
            text-decoration: none;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            font-weight: 600;
            border-radius: 6px;
            transition: background-color 0.2s;
        }}
        
        .download-btn:hover {{
            background-color: var(--accent-hover);
        }}
        
        .gpg-section {{
            background-color: rgba(59, 130, 246, 0.05);
            border: 1px dashed rgba(59, 130, 246, 0.3);
            padding: 1.25rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        
        .gpg-section h4 {{
            margin-bottom: 0.5rem;
            color: var(--accent-hover);
        }}
        
        .gpg-section p {{
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        
        .gpg-section a {{
            color: var(--accent-color);
            text-decoration: none;
            font-weight: 600;
        }}
        
        .gpg-section a:hover {{
            text-decoration: underline;
        }}
        
        footer {{
            text-align: center;
            margin-top: 3rem;
            color: var(--text-secondary);
            font-size: 0.875rem;
            border-top: 1px solid var(--border-color);
            padding-top: 1.5rem;
        }}
        
        footer a {{
            color: var(--text-primary);
            text-decoration: none;
        }}
        
        footer a:hover {{
            color: var(--accent-color);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{repo_name}</h1>
            <p class="subtitle">Custom Linux Package Repository</p>
        </header>

        {gpg_badge_html}

        <h2>Setup Instructions</h2>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('ubuntu')">Ubuntu / Debian</button>
            <button class="tab-btn" onclick="switchTab('fedora')">Fedora / RHEL / CentOS</button>
        </div>

        <!-- UBUNTU TAB -->
        <div id="ubuntu" class="tab-content active">
            <div class="instruction-step">
                <p>1. Register the repository GPG key (Recommended):</p>
                <div class="code-container">
                    <button class="copy-btn" onclick="copyCode('ubuntu-key')">Copy</button>
                    <pre id="ubuntu-key">{ubuntu_key_cmd}</pre>
                </div>
            </div>
            <div class="instruction-step">
                <p>2. Add the repository to sources list:</p>
                <div class="code-container">
                    <button class="copy-btn" onclick="copyCode('ubuntu-repo')">Copy</button>
                    <pre id="ubuntu-repo">{ubuntu_repo_cmd}</pre>
                </div>
            </div>
            <div class="instruction-step">
                <p>3. Update package index and install packages:</p>
                <div class="code-container">
                    <button class="copy-btn" onclick="copyCode('ubuntu-install')">Copy</button>
                    <pre id="ubuntu-install">sudo apt update
sudo apt install &lt;package-name&gt;</pre>
                </div>
            </div>
        </div>

        <!-- FEDORA TAB -->
        <div id="fedora" class="tab-content">
            <div class="instruction-step">
                <p>1. Add the repository configuration file:</p>
                <div class="code-container">
                    <button class="copy-btn" onclick="copyCode('fedora-repo')">Copy</button>
                    <pre id="fedora-repo">sudo curl -sL {repo_url}/fedora/deps-{repo_name}.repo -o /etc/yum.repos.d/deps-{repo_name}.repo</pre>
                </div>
            </div>
            <div class="instruction-step">
                <p>2. Update metadata cache and install packages:</p>
                <div class="code-container">
                    <button class="copy-btn" onclick="copyCode('fedora-install')">Copy</button>
                    <pre id="fedora-install">sudo dnf makecache
sudo dnf install &lt;package-name&gt;</pre>
                </div>
            </div>
        </div>

        <div class="package-list">
            <h2>Available Packages ({len(packages)})</h2>
            
            {empty_packages_html}
            
            {packages_html}
        </div>

        <footer>
            <p>Powered by GitHub Actions & Pages. View source on <a href="https://github.com/{repo_owner}/{repo_name}" target="_blank">GitHub</a>.</p>
        </footer>
    </div>

    <script>
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }}

        function copyCode(elementId) {{
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const btn = event.target;
                const originalText = btn.innerText;
                btn.innerText = 'Copied!';
                setTimeout(() => {{
                    btn.innerText = originalText;
                }}, 2000);
            }});
        }}
    </script>
</body>
</html>
"""
    with open("index.html", "w") as f:
        f.write(html_content)
    print("Generated landing page index.html successfully.")

def main():
    repo_owner, repo_name = get_repo_info()
    print(f"Repository: {repo_owner}/{repo_name}")
    
    # Download packages
    has_packages = download_packages()
    if not has_packages:
        print("No packages downloaded. Exiting.")
        # Create empty index.html so pages deployment doesn't fail
        generate_landing_page(repo_owner, repo_name, [], False)
        return
        
    # Export public key if GPG is configured
    has_gpg = export_public_key()
    
    # Generate repositories
    apt_packages = generate_apt_repo(repo_owner, repo_name)
    rpm_packages = generate_rpm_repo(repo_owner, repo_name)
    
    # Combine package lists
    all_packages = apt_packages + rpm_packages
    
    # Generate client configurations
    generate_client_configs(repo_owner, repo_name, has_gpg)
    
    # Generate index.html landing page
    generate_landing_page(repo_owner, repo_name, all_packages, has_gpg)
    
    # Clean up temp directories
    shutil.rmtree("temp_apt", ignore_errors=True)
    shutil.rmtree("temp_rpm", ignore_errors=True)
    print("=== Repository update completed successfully! ===")

if __name__ == "__main__":
    main()
