# Contributing

Bug reports and pull requests are welcome on GitHub.

## Reporting a bug

Open an issue with a description of what happened and what you
expected instead. Include the version (see CHANGELOG.md), your
Python version, and the browser you saw the problem in.

## Submitting a pull request

- Keep each PR focused on a single fix or feature — small PRs get
  reviewed faster and merged more often.
- If your change touches accounting logic in `ledger/services.py`,
  add or update a test in `test_ledger.py` to cover it.
- Run `pytest` locally and make sure all tests pass before
  submitting.
- The frontend is plain HTML/CSS/JS with no build step — please
  keep it that way.

## Coding conventions

- Backend: standard Python; business logic belongs in
  `services.py`, HTTP handling in `routes/`.
- Money is always integer cents server-side; never introduce
  floating-point arithmetic for balances.