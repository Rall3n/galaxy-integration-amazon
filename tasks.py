import psutil
import json
import os
import uuid
import tempfile
import shutil
from termcolor import colored
from pathlib import Path
from distutils.dir_util import copy_tree
from glob import glob
from fog import buildtools
from galaxy.tools import zip_folder_to_file

from invoke import task, call

from src.version import __version__

REPO_PATH = Path(__file__).resolve().parent
DIST_PATH = Path(REPO_PATH, "dist").resolve()
GALAXY_PATH = 'C:\\Program Files (x86)\\GOG Galaxy\\GalaxyClient.exe'
PLUGIN_PATH = f"{os.environ['localappdata']}\\GOG.com\\Galaxy\\plugins\\installed\\amazon_dev"

PLUGIN_GUID = str(uuid.uuid3(uuid.NAMESPACE_DNS, 'Rall3n/galaxy-integration-amazon'))


@task(optional=['output'])
def build_manifest(c, output=str(DIST_PATH)):
    print(f'[{colored("TASK", "yellow")}] Generating manifest ...')

    manifest = {
        "name": "Amazon Games plugin",
        "platform": "amazon",
        "guid": PLUGIN_GUID,
        "version": __version__,
        "description": "Amazon Games plugin",
        "author": "Rall3n",
        "email": "nb.rallen@gmail.com",
        "url": "https://github.com/Rall3n/galaxy-integration-amazon",
        "script": "plugin.py"
    }

    with open(os.path.join(output, "manifest.json"), "w") as file_:
        json.dump(manifest, file_, indent=4)


@task(optional=['output'])
def build(c, output=str(DIST_PATH)):
    print(f'[{colored("TASK", "yellow")}] Building plugin ...')
    try:
        with tempfile.NamedTemporaryFile(mode="r+", delete=False) as tmp:
            tmp.write(c.run('pipenv lock -r', hide=True).stdout)
            tmp.seek(0)

            buildtools.build(src='src', output=output, requirements=tmp.name)
            
            # buildtools.build only copies *.py files
            if Path(output, 'splash').resolve().exists():
                shutil.rmtree(Path(output, 'splash').resolve())

            shutil.copytree('src/splash', Path(output, 'splash').resolve())

            build_manifest(c, output)
    finally:
        if tmp:
            os.unlink(tmp.name)


@task
def deploy(c, galaxy_path=GALAXY_PATH):
    print(f'[{colored("TASK", "yellow")}] Deploying to Galaxy for tests ...')
    for proc in psutil.process_iter(attrs=['exe'], ad_value=''):
        if proc.info['exe'] == galaxy_path:
            print(f'[{colored("TASK", "yellow")}] Galaxy at {galaxy_path} is running!. Terminating ...')
            for child in proc.children():
                child.terminate()
            proc.terminate()
            break
    else:
        print('[ERR] Galaxy instance not found.')

    build(c, output=PLUGIN_PATH)

    print(f'[{colored("TASK", "yellow")}] Reopening Galaxy from {galaxy_path} ...')
    c.run(galaxy_path, asynchronous=True, hide=True)


@task(optional=['out_dir'])
def update_changelog(c, out_dir=str(REPO_PATH)):
    buildtools.update_changelog_file(repo_path=str(REPO_PATH), out_dir=out_dir)


@task(pre=[call(build)], optional=['archive_name'])
def dist(c, archive_name=f'amazon_{PLUGIN_GUID}.zip'):
    print(f'[{colored("TASK", "yellow")}] Creating zipped file for distribution ...')
    if Path(archive_name).resolve().exists():
        Path(archive_name).resolve().unlink()

    update_changelog(c)

    zip_folder_to_file(str(DIST_PATH), archive_name)
