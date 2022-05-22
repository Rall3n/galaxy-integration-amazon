import psutil
import json
import os
import uuid
import tempfile
import shutil
from termcolor import colored
from pathlib import Path
from fog.buildtools import update_changelog_file
from galaxy.tools import zip_folder_to_file

from invoke import task, call

from src.version import __version__

REPO_PATH = Path(__file__).resolve().parent
DIST_PATH = Path(REPO_PATH, "dist").resolve()
SRC_PATH = Path(REPO_PATH, "src").resolve()
FOG_RELEASE_PATH = Path(REPO_PATH, "fog_release").resolve()
GALAXY_PATH = f"{os.environ['programfiles(x86)']}\\GOG Galaxy\\GalaxyClient.exe"
PLUGIN_PATH = f"{os.environ['localappdata']}\\GOG.com\\Galaxy\\plugins\\installed\\amazon_dev"

PLUGIN_GUID = str(uuid.uuid3(uuid.NAMESPACE_DNS, 'Rall3n/galaxy-integration-amazon'))

PIP_PLATFORM = 'win32'


@task(optional=['output'])
def build_manifest(c, output=str(DIST_PATH)):
    out_path = Path(output)

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

    with out_path.joinpath('manifest.json').open('w') as file_:
        json.dump(manifest, file_, indent=4)


@task(optional=['output'])
def build(c, output=str(DIST_PATH)):
    out_path = Path(output)

    print(f'[{colored("TASK", "yellow")}] Building plugin ...')
    try:
        shutil.rmtree(output, ignore_errors=True)

        with tempfile.NamedTemporaryFile(mode="r+", delete=False) as pipenvLockTmp:
            pipenvLockTmp.write(c.run('pipenv lock -r', hide=True).stdout)
            pipenvLockTmp.seek(0)

        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as pipReqTmp:
            c.run(f'pipenv run pip-compile {Path(pipenvLockTmp.name).as_posix()} --output-file=-', out_stream=pipReqTmp, hide=True)
            pipReqTmp.seek(0)

        args = [
            'pip', 'install',
            '-r', pipReqTmp.name,
            '--platform', PIP_PLATFORM,
            '--target', out_path.as_posix(),
            '--python-version', '37',
            '--no-compile',
            '--no-deps'
        ]

        c.run(' '.join(args), echo=True, hide=True)

        for dir in out_path.glob('*.dist-info'):
            shutil.rmtree(dir)
        for test in [*out_path.rglob('test_*.py'), *out_path.rglob('*_test.py')]:
            test.unlink()

        shutil.copytree(SRC_PATH, Path(output).resolve(), dirs_exist_ok=True)

        build_manifest(c, output)
    finally:
        if pipenvLockTmp:
            os.unlink(pipenvLockTmp.name)
        if pipReqTmp:
            os.unlink(pipReqTmp.name)


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
    with c.cd('C:\\Windows\\System32'):
        c.run(f'"{galaxy_path}"', asynchronous=True, hide=True)


@task(optional=['out_dir'])
def update_changelog(c, out_dir=str(REPO_PATH)):
    update_changelog_file(repo_path=str(REPO_PATH), out_dir=out_dir)


@task(pre=[call(build)], optional=['archive_name'])
def dist(c, archive_name=f'amazon_{PLUGIN_GUID}.zip'):
    archive_path = Path(archive_name).resolve()

    print(f'[{colored("TASK", "yellow")}] Creating zipped file for distribution ...')
    archive_path.unlink(missing_ok=True)

    update_changelog(c)

    zip_folder_to_file(str(DIST_PATH), archive_name)


@task(optional=['output'])
def update_fog_release(c, output=str(FOG_RELEASE_PATH)):
    out_path = Path(output)

    print(f'[{colored("TASK", "yellow")}] Pushing to fog_release branch ...')

    shutil.copytree(SRC_PATH, out_path, dirs_exist_ok=True)
    build_manifest(c, output=out_path)
    create_requirements_file(c, output=out_path)

    print(f'[{colored("TASK", "yellow")}] Copying `current_version.json` ...')
    shutil.copy2(str(Path(REPO_PATH, 'current_version.json')), out_path)


@task
def create_requirements_file(c, output=str(REPO_PATH)):
    out_path = Path(output)

    print(f'[{colored("TASK", "yellow")}] Generating `requirements.txt` from Pipfile.lock ...')
    packages = []
    root = None

    with open(Path(REPO_PATH, 'Pipfile.lock')) as f:
        root = json.load(f)

    for name, pkg in root["default"].items():
        if 'index' not in pkg:
            continue

        version = pkg["version"]
        packages.append(f'{name}{version}')

    with out_path.joinpath('requirements.txt').open('w') as _file:
        _file.write('\n'.join(packages))
