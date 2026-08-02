### To update agents
`docker buildx build -f system-agent/Dockerfile.agent.arm64  --platform linux/arm64 -t yagatito/system-agent-arm64:1.0  --push ./system-agent`
`docker buildx build -f system-agent/Dockerfile.agent.amd64  --platform linux/amd64 -t yagatito/system-agent-amd64:1.0  --push ./system-agent`

