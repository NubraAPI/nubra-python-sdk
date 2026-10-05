# Contributing

Thanks for helping improve the Nubra Python SDK samples repo.

## Before You Contribute

- Check existing issues before opening a new one
- Use `examples/` for runnable Python samples
- Use `snippets/` for partial fragments
- Use `schemas/` for response shapes and SDK surface references
- Keep examples defaulted to `NubraEnv.UAT` unless the example specifically teaches environment switching

## Local Validation

Run the lightweight validator before opening a pull request:

```powershell
py tools/validate_examples.py
```

## Pull Request Guidelines

- Keep changes focused and easy to review
- Prefer descriptive filenames over numeric suffixes when adding new content
- Avoid committing secrets, credentials, or live account identifiers
- For mutating trading examples, use placeholders and UAT-safe defaults
- Update the README when adding new top-level conventions

## Issues

- Use GitHub Issues for bugs, docs problems, and feature requests
- Use private security reporting for vulnerabilities. See [SECURITY.md](SECURITY.md)
