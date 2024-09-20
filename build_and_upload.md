change version go to pyproject.toml& scr/utility_toolkit/__init__.py and update the version

build 
```bash
python -m build 
```

upload to pypi
```bash
twine upload dist/* --skip-existing
```