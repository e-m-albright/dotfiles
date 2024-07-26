
```
ln -s ~/code/ext/memory/sh/.zshrc ~/.zshrc

// TODO can't I make this point to the same conda?
// TODO read file path from this dir
ln -s ~/code/ext/memory/sh/.zshrc_conda ~/.zshrc_conda

# greadlink & gshred
brew install coreutils

```

populate testing env (docker is better of course)

export $(cat ../.env | xargs) && go test ./internal/identities


Kill hanging processes taking up ports
```
lsof -i tcp:8080
kill -9 <PID>
```


### Destroy git history

instead of fussing with BFG / git-filter-branch, if you include sensitive info and can afford to clean wipe a branch history like here, run this

```
# create a branch with no history
git checkout --orphan latest_branch

git add -A
git commit -am "Wiping history"

git log -n 5

git branch -D main
git branch -m main

git push -f origin main
git gc --aggressive --prune=all
```

Use a commit from another repo (forked/copied repos)
```
git --git-dir=../lens/.git format-patch -k -1 --stdout 9be53d921c0b3645a60ee710c3909da114f1f59e | git am -3 -k
```





[user]
	name = Evan Albright
	email = ichbinevan@gmail.com

[alias]
  # I'm not sure, add and commit in one go?
  ac = "!git add . && git commit -am"

  ap = add -p

  # Show branches w/ info
  b = "!git for-each-ref --sort='-authordate' --format='%(authordate)%09%(objectname:short)%09%(refname)' refs/heads | sed -e 's-refs/heads/--'"
  ba = branch -a

  # Get the current branch name (not so useful in itself, but used in other aliases)
  branch-name = "!git rev-parse --abbrev-ref HEAD"

  co = checkout
  cob = checkout -b
  cot = checkout --track

  c = commit
  cm = commit -m
  cam = commit -am

  d = diff
  ds = diff --stat
  dc = diff --cached

  f = fetch -p
  
  l = log --pretty=format:"%C(yellow)%h\\ %ad%Cred%d\\ %Creset%s%Cblue\\ [%cn]" --decorate --date=short
  lg = log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit

  m = merge

  # Given a merge commit, find the span of commits that exist(ed) on that
  # branch. Again, not so useful in itself, but used by other aliases.
  merge-span = "!f() { echo $(git log -1 $2 --merges --pretty=format:%P | cut -d' ' -f1)$1$(git log -1 $2 --merges --pretty=format:%P | cut -d' ' -f2); }; f"
  # Find the commits that were introduced by a merge
  merge-log = "!git log `git merge-span .. $1`"
  # Show the changes that were introduced by a merge
  merge-diff = "!git diff `git merge-span ... $1`"

  pl = pull
  pu = push
  
  publish = "!git push -u origin $(git branch-name)"
  unpublish = "!git push origin :$(git branch-name)"

  # Interactively rebase all the commits on the current branch
  # rebase-branch = "!git rebase -i `git merge-base master HEAD`"  

  s = status
  ss = status -sb

  st = stash
  stl = stash list
  sta = stash apply
  sts = stash save
  stp = stash pop

  # wait for me!
  wfm = commit -a --amend
  
  contributors = shortlog -s -n -e

  alias = ! git config --get-regexp ^alias\\. | sed -e s/^alias\\.// -e s/\\ /\\ =\\ /

[remote "origin"]
	prune = true