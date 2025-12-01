# Docker Deployment Guide

This guide covers how to build, publish, and deploy Prompt Engineer using Docker.

## Table of Contents
- [Local Development](#local-development)
- [Docker Hub Setup](#docker-hub-setup)
- [GitHub Actions Setup](#github-actions-setup)
- [Manual Publishing](#manual-publishing)
- [Automated Releases](#automated-releases)

## Local Development

### Build the Docker Image

```bash
# Build from the repository root
docker build -t prompt-engineer .

# Build with a specific tag
docker build -t prompt-engineer:v0.1.0 .
```

### Run Locally

```bash
# Using docker-compose (recommended for development)
docker-compose up

# Using docker run
docker run -it --rm \
  -p 7860:7860 \
  -v $(pwd)/workspace:/workspace \
  -v prompt-engineer-config:/root/.prompt-engineer \
  prompt-engineer

# Run on a different port
docker run -it --rm \
  -p 8080:8080 \
  -v $(pwd)/workspace:/workspace \
  prompt-engineer \
  prompt-engineer --workspace /workspace --port 8080
```

### Test the Container

```bash
# Access the application at http://localhost:7860
# Stop with Ctrl+C

# View logs
docker-compose logs -f

# Clean up
docker-compose down
docker volume rm prompt-engineer-config  # If you want to reset config
```

## Docker Hub Setup

### 1. Create a Docker Hub Account

1. Go to [Docker Hub](https://hub.docker.com/)
2. Sign up for a free account
3. Create a new repository:
   - Name: `prompt-engineer`
   - Visibility: Public (or Private if you have a paid plan)
   - Description: "CLI-based developer workbench for rapid AI prompt engineering iteration"

### 2. Create Access Token

1. Go to Account Settings → Security → [Access Tokens](https://hub.docker.com/settings/security)
2. Click "New Access Token"
3. Name: `github-actions` (or similar)
4. Permissions: Read & Write
5. **Copy the token** (you won't see it again!)

### 3. Test Docker Hub Login Locally

```bash
# Login to Docker Hub
docker login -u yourusername

# Tag your image
docker tag prompt-engineer yourusername/prompt-engineer:latest

# Push to Docker Hub
docker push yourusername/prompt-engineer:latest
```

## GitHub Actions Setup

### 1. Add GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add two secrets:
   - **Name**: `DOCKER_USERNAME`
     - **Value**: Your Docker Hub username
   - **Name**: `DOCKER_PASSWORD`
     - **Value**: The access token you created (NOT your Docker Hub password)

### 2. Update Workflow File

The workflow file `.github/workflows/docker-publish.yml` is already configured. You just need to update the Docker Hub username in the README examples.

### 3. Workflow Triggers

The workflow will automatically:
- **Build** on every push to `main` or pull request
- **Push to Docker Hub** on pushes to `main` (not PRs)
- **Tag releases** when you create a git tag like `v1.0.0`

### 4. Verify Workflow

1. Push a commit to `main`:
   ```bash
   git add .
   git commit -m "Add Docker support"
   git push origin main
   ```

2. Check the Actions tab on GitHub:
   - You should see a workflow running
   - It will build for `linux/amd64` and `linux/arm64`
   - On success, the image will be pushed to Docker Hub

## Manual Publishing

### Build and Push a Specific Version

```bash
# Login to Docker Hub
docker login -u yourusername

# Build for multiple platforms
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yourusername/prompt-engineer:v0.1.0 \
  -t yourusername/prompt-engineer:latest \
  --push .
```

### Single Platform Build (faster for testing)

```bash
docker build -t yourusername/prompt-engineer:test .
docker push yourusername/prompt-engineer:test
```

## Automated Releases

### Creating a Release

1. **Tag your release** (use semantic versioning):
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

2. **GitHub Actions will automatically**:
   - Build the Docker image
   - Tag it with:
     - `v0.1.0` (exact version)
     - `0.1` (major.minor)
     - `0` (major)
     - `latest` (if pushed to main)
   - Push all tags to Docker Hub

3. **Users can then pull**:
   ```bash
   # Latest version
   docker pull yourusername/prompt-engineer:latest

   # Specific version
   docker pull yourusername/prompt-engineer:v0.1.0

   # Major.minor version (gets latest patch)
   docker pull yourusername/prompt-engineer:0.1
   ```

### Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md` (if you have one)
- [ ] Commit changes
- [ ] Create and push git tag: `git tag v0.1.0 && git push origin v0.1.0`
- [ ] Verify GitHub Actions build succeeds
- [ ] Verify image appears on Docker Hub
- [ ] Test pulling and running the image
- [ ] Create GitHub Release (optional)

## Multi-Platform Builds

The GitHub Actions workflow builds for both `linux/amd64` and `linux/arm64`, which means it will work on:
- Intel/AMD servers and desktops
- Apple Silicon Macs (M1, M2, M3)
- ARM-based cloud instances

### Local Multi-Platform Build

```bash
# Set up buildx
docker buildx create --name mybuilder --use
docker buildx inspect --bootstrap

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yourusername/prompt-engineer:latest \
  --push .
```

## Troubleshooting

### Build Fails in GitHub Actions

1. Check the Actions logs for specific errors
2. Common issues:
   - Missing GitHub secrets (DOCKER_USERNAME, DOCKER_PASSWORD)
   - Incorrect Docker Hub credentials
   - Syntax errors in Dockerfile

### Image Won't Run

```bash
# Check image exists
docker images | grep prompt-engineer

# Run with verbose output
docker run -it prompt-engineer prompt-engineer --help

# Check logs
docker logs <container-id>
```

### Permission Issues with Volumes

```bash
# On Linux, if you get permission errors:
docker run -it --rm \
  -p 7860:7860 \
  -v $(pwd):/workspace \
  --user $(id -u):$(id -g) \
  yourusername/prompt-engineer
```

## Best Practices

1. **Always tag releases**: Use semantic versioning (v1.0.0, v1.0.1, etc.)
2. **Test locally first**: Build and run the image locally before pushing
3. **Use `.dockerignore`**: Keep images small by excluding unnecessary files
4. **Layer caching**: Order Dockerfile commands from least to most frequently changed
5. **Security**: Never commit secrets, use GitHub secrets instead
6. **Multi-platform**: Build for both amd64 and arm64 for maximum compatibility

## Example: Complete Release Flow

```bash
# 1. Make changes and commit
git add .
git commit -m "feat: Add new feature"

# 2. Update version in pyproject.toml
# version = "0.2.0"

# 3. Test locally
docker build -t prompt-engineer:v0.2.0 .
docker run -it --rm -p 7860:7860 prompt-engineer:v0.2.0

# 4. Commit version bump
git add pyproject.toml
git commit -m "chore: Bump version to 0.2.0"

# 5. Create and push tag
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin main
git push origin v0.2.0

# 6. GitHub Actions will:
#    - Build the image
#    - Push to Docker Hub with tags: v0.2.0, 0.2, 0, latest

# 7. Users can now pull:
docker pull yourusername/prompt-engineer:latest
```

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Hub](https://hub.docker.com/)
- [GitHub Actions for Docker](https://docs.docker.com/build/ci/github-actions/)
- [Docker Buildx](https://docs.docker.com/buildx/working-with-buildx/)
