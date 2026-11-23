"""Shared setup and fixtures for all backend tests."""

import os

# Importing `app.main` builds the app, and that needs APP_ENV.
# pytest loads this file before any test module, so every test runs
# as "test", also on a computer or CI runner without a `.env` file.
os.environ["APP_ENV"] = "test"
