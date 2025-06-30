# Team IOSYS

[**Homepage**](https://osh-2025.github.io/iosys)

Team IOSYS of USTC OSH 2025 - not "IOSYS".

Yet another Graph File Agent.

![](./docs/final/assets/arch.svg)<br>
![](./docs/final/assets/webui.png)<br>
![](./docs/final/assets/webui-example-2.png)<br>
![](./docs/final/assets/kg-demo.png)

# Development

See [CONTRIBUTING.md](./CONTRIBUTING.md).

# Docker Image

1. Prepack the `.env` file. You may refer to [`./.env.example`](./.env.example).

2. Run the docker image:

```sh
docker run -v /path/to/.env:/app/.env -p 5173:5173 -p 8000:8000 -p 8001:8001 ghcr.io/osh-2025/iosys:latest
```

3. Access the web UI at `http://localhost:5173`. The A2A server is exposed at `http://localhost:8001`.
