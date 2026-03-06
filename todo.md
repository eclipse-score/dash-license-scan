# Next steps:

## internal quality
- improve `_eval` code with comments, type-safety, ...
## docs
- update README (e.g. on how to use as an action)
- improve understandability of status column in markdown output, e.g. Legend or "Explain" dropdown as we have with stderr.
## new features
- auto discovery of lock files (e.g. **/requirements.txt), see how dependabot does it!
- add a parseable outputter next to markdown, specifically json
- improve concept for dev dependency vs prod dependency. Currently only uv supported
- dont provide auto PR comment on EVERY pr in the repo! Only when dependencies change!
## bug
- remove optional dependencies in [braket] from pypi entries, e.g. sphinx[plotting] -> sphinx


## far far away - not important or too early
- try out in some repos
- adjust cicd-workflows license-check.yml to call this action instead of bazel version
- setup pypi releases - later!
- remove dash from tooling repo
- clarify open questions towards eclipse license guys
- Show delta in PR, not only the new scan (nice to have)
