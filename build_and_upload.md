## Generate requirements.txt


### Scan the code using sonarqube locally

```bash
docker pull sonarqube
docker run -d --name sonarqube -p 9000:9000 -v ~/docker_data/sonarqube/conf:/opt/sonarqube/conf -v ~/docker_data/sonarqube/data:/opt/sonarqube/data -v ~/docker_data/sonarqube/logs:/opt/sonarqube/logs -v ~/docker_data/sonarqube/extensions:/opt/sonarqube/extensions sonarqube
```


2. Set sonar qube admin password:

set the password to `admin` in the sonarqube container to wiwna9-wakmiw-zEkjun


Install SonarScanner and add it to your system's PATH.
```bash
 brew install sonar-scanner
```

3. Generate admin token for sonarqube:
   1. go to http://127.0.0.1:9000/account/security/
   2. Generate a token for the admin user.
   3. Token: admin
   4. Name: admin
   5. type: Global Analysis Token
   6. copy the token to use it later.
   
4. Create a new project in SonarQube and generate a token for the project.
   1. create new project in SonarQube and generate a token for the project.
   2. Project Name: utility_toolkit
   3. Project Key: utility_toolkit
   4. How do you want to analyze your repository? Locally.
   5. Token: Use existing token as in point 3 -> 6

4. If you generate a token, you can use it to run the SonarScanner:

# get token as input from user
```bash
echo -n "Enter the token: "
read token
```

```bash
sonar-scanner \
  -Dsonar.projectKey=utility_toolkit \
  -Dsonar.sources=. \
  -Dsonar.host.url=http://127.0.0.1:9000 \
  -Dsonar.token=${token}
```



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

## create version and take changes from develop branch
```bash
git checkout -b release-0.1.9
```

Fetch the latest changes from the remote repository:
```bash
git fetch origin
```

Merge the changes from the other branch (e.g., develop) into your current branch if needed:
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
git tag -a v0.1.9 -m "release 0.1.9"
git push origin v0.1.9
git push origin release-0.1.9
git push bitbucket v0.1.9
git push bitbucket release-0.1.9
```



## install from bitbucket
```bash
pip install git+https://bitbucket.org/username/reponame.git@branchname
```

## install using ssh
```bash
 pip install git+ssh://git@bitbucket.org/olah-healthcare/utility-toolkit.git@branchname
```