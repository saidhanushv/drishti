# 🚀 Deployment Guide: Docker Container

Since your project relies on large, pre-computed files (`faiss_index`, `promotion_data.duckdb`) that are **ignored in Git**, you cannot simply deploy by connecting a web host to your GitHub repository. The host won't see those files.

**The Solution:** Build a **Docker Image** locally.
This "bakes" your local data files into a portable container image. You then push this image to a registry (like Docker Hub) and tell your hosting provider to run it.

---

## 📋 Prerequisites
1.  **Docker Desktop** installed and running.
2.  **Docker Hub Account** (free) -> [Sign up](https://hub.docker.com/).

---

## 🛠️ Step 1: Build the Image Locally
This step packages your frontend, backend, and **local data files** into one single artifact.

1.  Open your terminal in the root `drishti/` folder.
2.  Login to Docker Hub:
    ```bash
    docker login
    ```
3.  Build the image (replace `yourusername` with your Docker Hub username):
    ```bash
    docker build -t yourusername/drishti-app:latest .
    ```
    *This will take a few minutes as it compiles the Angular app and installs Python dependencies.*

4.  Verify it works locally:
    ```bash
    docker run -p 8000:8000 --env-file backend/.env yourusername/drishti-app:latest
    ```
    *Open `http://localhost:8000` to see your app running from the container.*

---

## ☁️ Step 2: Push to Docker Hub
Once confirmed working, upload the image to the cloud.

```bash
docker push yourusername/drishti-app:latest
```

---

## 🌍 Step 3: Hosting Options

### Option A: Render (Free Tier available)
1.  Go to [dashboard.render.com](https://dashboard.render.com/).
2.  Click **New +** -> **Web Service**.
3.  Select **"Deploy an existing image from a registry"**.
4.  Enter your image URL: `yourusername/drishti-app:latest`.
5.  **Environment Variables:**
    *   Add `OPENAI_API_KEY`, `AZURE_STORAGE_CONNECTION_STRING`, etc. here.
    *   Set `ENVIRONMENT` to `production`.
6.  **Plan:** Select the Free plan.
7.  Click **Create Web Service**.

### Option B: Azure App Service (Web App for Containers)
1.  Go to Azure Portal -> **Create a resource** -> **Web App**.
2.  **Publish:** Docker Container.
3.  **Operating System:** Linux.
4.  **Pricing Plan:** B1 (Basic) is recommended for stability, though an F1 (Free) tier exists (limitations apply).
5.  **Docker Tab:**
    *   Image Source: Docker Hub.
    *   Image and tag: `yourusername/drishti-app:latest`.
6.  **Review + Create.**
7.  Once created, go to **Settings** -> **Environment variables** to add your keys.

---

## 🔄 Updates
When you update your code or data:
1.  Re-run `docker build ...` locally.
2.  Re-run `docker push ...`.
3.  Your hosting provider will usually pull the new image automatically (or you can trigger a restart).
