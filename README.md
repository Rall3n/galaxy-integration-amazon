# GOG Galaxy 2.0 - Amazon Games Integration

This plugin was created to import games owned in the Amazon Games App into the GOG Galaxy 2.0 Client.
Allegedly this app could replace the official Twitch App to access games redeemed through Prime Gaming, although the latter is still supported.

This plugin doesn't require any credentials, because it doesn't need to authenticate against an API. That's because Amazon uses a different, slightly complicated authentication scheme for their endpoints. _And because I don't want to be responsible for people losing their Amazon accounts because of this._

## Installation

Get the corresponding zip archive for your OS from the [latest releases](https://github.com/Rall3n/galaxy-integration-amazon/releases/latest) and extract the contents into a seperate folder in the dedicated plugin directory:
* Windows: `C:\Users\%username%\AppData\Local\GOG.com\Galaxy\plugins\installed`
* ~~MacOS~~: _Due to lack of hardware no support_

## Development

This project uses [pipenv](https://github.com/pypa/pipenv) for dependency management.

### Install the required dependencies

```bash
pipenv install --dev
```

### Build the package

```bash
pipenv run [build | deploy | dist [--a=<zip_archive.zip>]]
```
