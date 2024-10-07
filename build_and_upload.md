## Generate requirements.txt
```bash
pipreqs . --force
```

## change version
```bash
go to pyproject.toml& scr/utility_toolkit/__init__.py and update the version
```

## update version and requirements in pyproject.toml
open file pyproject.toml and update requirements ad in requirements.txt and update version

## build
```bash
python -m build
```
   
## Upload to pypi
``` bash
twine upload dist/* --skip-existing
```

## create version
Ensure you're on the branch you want to update:
```bash
git checkout new_branch_name
```

Fetch the latest changes from the remote repository:
```bash
git fetch origin
```

Create a new branch to work on:
```bash
git checkout -b feature_branch_name origin/main
```

Merge the changes from the other branch (e.g., develop) into your current branch:
```bash
git merge develop
```

Alternatively, you can use rebase instead of merge:
```bash
git rebase develop
```



## To rebase your develop branch from an old_branch, you can follow these steps:
First, ensure you're on the develop branch:
```bash
git checkout develop
```

Fetch the latest changes from the remote repository:
```bash
git fetch origin
```

Rebase the develop branch onto old_branch:
```bash
git rebase old_branch
```

This command will take the commits from develop that are not in old_branch and replay them on top of old_branch.

## example:
update your code in develop branch

clone this code to a new branch
```bash
git checkout -b release-0.1.8 
git merge develop
git tag -a v0.1.8 -m "release 0.1.8"
git push origin v0.1.8
git push origin release-0.1.8
git push bitbucket v0.1.8
git push bitbucket release-0.1.8
```



## install from bitbucket
```bash
pip install git+https://bitbucket.org/username/reponame.git@branchname
```

## install using ssh
```bash
 pip install git+ssh://git@bitbucket.org/olah-healthcare/utility-toolkit.git@branchname
```