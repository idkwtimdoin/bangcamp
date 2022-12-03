# BANGCAMPS

<p align="center">
  <img src="docs/312140.jfif">
</p>

> setup
```shell
$ pip3 install virtualenv                           # installation
$ python3 -m virtualenv venv                        # init venv
$ source venv/bin/activate                          # activate
$ (venv) pip3 install --upgrade pip
$ (venv) pip3 install -r requirements.txt           # install requirements for venv
```
> usage
```shell
Usage: scrape_bc.py [OPTIONS]

Options:
  -u, --url TEXT               album url  [required]
  -D, --dest my/secret/folder  destination folder. default  [default:
                               downloads]
  --help                       Show this message and exit.
```
> example
```shell
$ python3 scrape_bc.py -D "my/downloads/folder" -u "no example provided"
```
