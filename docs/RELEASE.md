# Release Process

## Versioning Strategy

We follow [Semantic Versioning 2.0.0](https://semver.org/).

* **Major (X.y.z)**: Breaking changes to the Optimizer Engine or Rule format.
* **Minor (x.Y.z)**: New features (e.g., new AI prompts, new Analysis tab).
* **Patch (x.y.Z)**: Bug fixes and minor UI tweaks.

## Creating a Release

1. **Update Documentation**:
    * Ensure `README.md` reflects any new features.
    * Update `CHANGELOG.md` (if maintained).

2. **Tagging**:

    ```bash
    git tag -a v1.0.0 -m "Release v1.0.0: Initial MVP release with AI Coach"
    git push origin v1.0.0
    ```

3. **GitHub Release**:
    * Draft a new release on GitHub using the pushed tag.
    * Attach the zipped source code (GitHub does this automatically).
    * (Optional) Attach a built Docker image if using a registry.

## Verify Build

Before tagging, run the local verification suite:

```bash
python -m compileall src/
python -m pytest tests/  # if tests exist
```

And verify Docker build:

```bash
docker compose build --no-cache
docker compose up
```
