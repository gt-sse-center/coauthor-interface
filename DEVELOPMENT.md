TODO: this file will be updated with a PR to transition to UV

## 🛠️ Disabling OpenAI in Development

By default, the server will read an OpenAI API key from your `config/api_keys.csv`.  
If you’d like to run the backend locally **without** needing an actual OpenAI key, set the `DEV_MODE` environment variable to `true`. In this mode:

- All calls to `/api/query` Query GPT-3 will immediately return empty suggestions (`[]`).  