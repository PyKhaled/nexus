# Installation and Validation

The template requires Python 3, Make, Docker, and `curl` for the complete local
workflow. Its starter service has no third-party Python dependencies.

```sh
cp .env.example .env
make check
make run
```

In another terminal, verify `http://127.0.0.1:8000/healthz` and
`http://127.0.0.1:8000/readyz`.

Build and exercise the container contract with:

```sh
make smoke
```

After copying the template, add and lock the dependencies required by the real
service and update this guide with its reproducible setup procedure.
