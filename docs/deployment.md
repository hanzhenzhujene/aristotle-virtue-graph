# Deployment

This repository is deployed on Streamlit Community Cloud.

## Current status

- GitHub repository is public
- live app URL: `https://aristotle-virtue-graph.streamlit.app/`
- app entrypoint is at the repo root: `streamlit_app.py`
- deployment dependencies are in the repo root: `requirements.txt`
- processed Book II data is already committed, so the deployed app does not need a separate build step

## Streamlit Community Cloud target

Current hosted target:

- Repository: `hanzhenzhujene/aristotle-virtue-graph`
- Branch: `main`
- Main file path: `streamlit_app.py`

Official docs:

- [Deploy your app on Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Connect your GitHub account](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account)
- [App settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)

## Updating the deployment

If the app is redeployed under a different URL, update:

1. `README.md`
2. `docs/deployment.md`

Keep the README top CTA pointed at the real live dashboard, not at deployment setup instructions.

## Verified hosted target

The current public app should be configured in Streamlit Community Cloud as:

- Repository: `hanzhenzhujene/aristotle-virtue-graph`
- Branch: `main`
- Main file path: `streamlit_app.py`
- Live URL: `https://aristotle-virtue-graph.streamlit.app/`

If the live dashboard stops reflecting GitHub pushes, check those three settings first and then
use **Manage app** -> **Reboot app**.

## Change the public URL

Streamlit Community Cloud lets you replace the generated hostname with a custom subdomain.
This is a dashboard setting, not a repository change.

From the deployed app or from `share.streamlit.io`:

1. Open **Manage app**
2. Open **Settings**
3. On the **General** tab, find **App URL**
4. Enter a new subdomain between 6 and 63 characters
5. Click **Save**

If the URL changes, update the links in:

1. `README.md`
2. `docs/deployment.md`
