# Deployment

This repository is prepared for Streamlit Community Cloud deployment.

## Current status

- GitHub repository is public
- app entrypoint is at the repo root: `streamlit_app.py`
- deployment dependencies are in the repo root: `requirements.txt`
- processed Book II data is already committed, so the deployed app does not need a separate build step

## Streamlit Community Cloud target

Use these settings in Community Cloud:

- Repository: `hanzhenzhujene/aristotle-virtue-graph`
- Branch: `main`
- Main file path: `streamlit_app.py`

## Final step still required

The remaining action must be done in a browser session connected to a Streamlit Community Cloud account with GitHub access.

Per the official deployment flow, the last step is:

1. Go to `share.streamlit.io`
2. Click **Create app**
3. Select the repository `hanzhenzhujene/aristotle-virtue-graph`
4. Set the main file path to `streamlit_app.py`
5. Click **Deploy**

Official docs:

- [Deploy your app on Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Connect your GitHub account](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account)

## After deployment

Once the live URL exists, put it in the top section of `README.md` in place of the deployment-ready placeholder link.
