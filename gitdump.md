/Users/dammy/.zshrc:7: command not found: openclaw
dammy@macs-MacBook-Pro AetherProject % git pull                                                      
Your configuration specifies to merge with the ref 'refs/heads/main'
from the remote, but no such ref was fetched.
dammy@macs-MacBook-Pro AetherProject % git push
Enumerating objects: 4, done.
Counting objects: 100% (4/4), done.
Delta compression using up to 12 threads
Compressing objects: 100% (4/4), done.
Writing objects: 100% (4/4), 2.33 KiB | 2.33 MiB/s, done.
Total 4 (delta 0), reused 0 (delta 0), pack-reused 0 (from 0)
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: 
remote: - GITHUB PUSH PROTECTION
remote:   —————————————————————————————————————————
remote:     Resolve the following violations before pushing again
remote: 
remote:     - Push cannot contain secrets
remote: 
remote:     
remote:      (?) Learn how to resolve a blocked push
remote:      https://docs.github.com/code-security/secret-scanning/working-with-secret-scanning-and-push-protection/working-with-push-protection-from-the-command-line#resolving-a-blocked-push
remote:     
remote:     
remote:       —— GCP API Key Bound to a Service Account ————————————
remote:        locations:
remote:          - commit: b7c6c6103418aeb940c48bda3eba7d20fb31c619
remote:            path: aether_link.py:9
remote:     
remote:        (?) To push, remove secret from commit(s) or follow this URL to allow the secret.
remote:        https://github.com/DamilolaAdegunwa/AetherProject/security/secret-scanning/unblock-secret/3J7J6CRUcC6mxUrF2OAneqN3bxS
remote:     
remote: 
remote: 
To https://github.com/DamilolaAdegunwa/AetherProject.git
 ! [remote rejected] main -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/DamilolaAdegunwa/AetherProject.git'
dammy@macs-MacBook-Pro AetherProject % git add .
dammy@macs-MacBook-Pro AetherProject % git commit -m "save"
On branch main
Your branch is based on 'origin/main', but the upstream is gone.
  (use "git branch --unset-upstream" to fixup)

nothing to commit, working tree clean
dammy@macs-MacBook-Pro AetherProject % git branch --unset-upstream
dammy@macs-MacBook-Pro AetherProject % git push                   
fatal: The current branch main has no upstream branch.
To push the current branch and set the remote as upstream, use

    git push --set-upstream origin main

To have this happen automatically for branches without a tracking
upstream, see 'push.autoSetupRemote' in 'git help config'.

dammy@macs-MacBook-Pro AetherProject % git push --set-upstream origin main
Enumerating objects: 4, done.
Counting objects: 100% (4/4), done.
Delta compression using up to 12 threads
Compressing objects: 100% (4/4), done.
Writing objects: 100% (4/4), 2.33 KiB | 2.33 MiB/s, done.
Total 4 (delta 0), reused 0 (delta 0), pack-reused 0 (from 0)
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: 
remote: - GITHUB PUSH PROTECTION
remote:   —————————————————————————————————————————
remote:     Resolve the following violations before pushing again
remote: 
remote:     - Push cannot contain secrets
remote: 
remote:     
remote:      (?) Learn how to resolve a blocked push
remote:      https://docs.github.com/code-security/secret-scanning/working-with-secret-scanning-and-push-protection/working-with-push-protection-from-the-command-line#resolving-a-blocked-push
remote:     
remote:     
remote:       —— GCP API Key Bound to a Service Account ————————————
remote:        locations:
remote:          - commit: b7c6c6103418aeb940c48bda3eba7d20fb31c619
remote:            path: aether_link.py:9
remote:     
remote:        (?) To push, remove secret from commit(s) or follow this URL to allow the secret.
remote:        https://github.com/DamilolaAdegunwa/AetherProject/security/secret-scanning/unblock-secret/3J7J6CRUcC6mxUrF2OAneqN3bxS
remote:     
remote: 
remote: 
To https://github.com/DamilolaAdegunwa/AetherProject.git
 ! [remote rejected] main -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/DamilolaAdegunwa/AetherProject.git'
dammy@macs-MacBook-Pro AetherProject % git push --set-upstream origin main
Enumerating objects: 4, done.
Counting objects: 100% (4/4), done.
Delta compression using up to 12 threads
Compressing objects: 100% (4/4), done.
Writing objects: 100% (4/4), 2.33 KiB | 2.33 MiB/s, done.
Total 4 (delta 0), reused 0 (delta 0), pack-reused 0 (from 0)
To https://github.com/DamilolaAdegunwa/AetherProject.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
dammy@macs-MacBook-Pro AetherProject % 