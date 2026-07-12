# SUST Hackathon

Super Agent is a synthetic multi-provider liquidity, anomaly, and coordination
prototype. It does not connect to real wallets or execute financial actions.

## Verify the prototype

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m engine.main
.\.venv\Scripts\python.exe -m alerts.main

cd ..\frontend
npm run lint
npm run build
```

MongoDB/JWT setup and demo accounts are documented in
[`docs/MONGODB_AND_AUTH.md`](docs/MONGODB_AND_AUTH.md). Data assumptions and
current evaluation boundaries are in
[`docs/DATA_AND_ASSUMPTIONS.md`](docs/DATA_AND_ASSUMPTIONS.md) and
[`docs/RESPONSIBLE_DESIGN.md`](docs/RESPONSIBLE_DESIGN.md).

> AI-assisted development on this project is logged in
> [`/prompts`](prompts/README.md).
