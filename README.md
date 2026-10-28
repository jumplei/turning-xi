# Turning XI

**Every turning point, explained.**

Turn football events into evidence-grounded stories, personalized insights, and broadcast-ready recaps—updated when the match record changes.

Turning XI helps fans and analysts understand how a match develops, and lets broadcast operators see which stories and graphics need updating after a record correction. Built for **The Synthetic Match Insights Engine for Premier League Studio**.

## Live demo

[Open Turning XI](https://ca-matchmind.jollystone-6e63690c.eastus2.azurecontainerapps.io)

Open the hosted demo directly—no sign-in or access token is required. Press Play to follow the match and its AI explanations. The hosted demo is scheduled to remain available through the judging deadline, November 10, 2026 at 11:59 p.m. Pacific.

## Try it locally

Use Python 3.9 or later. Keep dependencies in a project virtual environment.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
AZURE_OPENAI_API_KEY= AZURE_OPENAI_ENDPOINT= .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000/. This starts an offline version with labelled templates and computed facts. It does not call a model. Automated tests also use mocked model transports.

## Connect Microsoft Foundry

Copy `.env.example` to `.env`, then enter your own resource endpoint, model deployment name and server-side API key. Start the server with a request allowance, for example:

```sh
PHASELENS_SESSION_CALL_LIMIT=20 PHASELENS_SESSION_SECONDS=1800 .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

This example allows up to 20 reserved model request slots over 30 minutes. Real model requests incur charges on your Azure account. A slot limit controls application requests; it is not an Azure billing cap. Deep analysis can reserve two slots. Restarting this example creates a new session allowance. Health checks do not call the model.

The integration uses the Azure Responses API with a model deployed in Microsoft Foundry. Development has been tested against an existing `gpt-6-luna` deployment; model availability and supported parameters depend on your resource. API keys remain on the server. Never commit `.env`.

## What to explore

- **Match replay:** Play, pause, seek and change speed. Key moments lists only events that have occurred by the playhead.
- **Turning points:** Select a completed phase, inspect its sequence and replay it.
- **The Turning XI read:** Compare Fan/Analyst, team perspectives, and English/Simplified Chinese. Inspect supporting events through See the evidence.
- **Recaps:** Generate a story through the current playhead, including the final result at full time.
- **Broadcast desk:** Preview/export versioned graphics data, withdraw a synthetic goal entry, inspect affected-content withdrawals, and export a correction patch.

See [the walkthrough](docs/DEMO.md), [architecture](docs/ARCHITECTURE.md), [validation](docs/TESTING.md) and [project description](docs/PROJECT.md).

## How it works

```text
Seeded synthetic events → visible match prefix → computed facts and phases
  → direct explanation OR model-selected read-only evidence tools
  → reference and typed-fact checks → explanation or labelled fallback
  → personalized story / recap / overlay / correction patch
```

Fast explanations use one model request. Deliberate deeper analysis uses a tool-selection request followed by a structured narrative request. Tools inspect event sequences, recent playing-time windows and personnel state. They cannot read future events or mutate the match record.

Figures are computed in Python and checked against structured claims. The code checks supplied event references and supported roster-style player names. It does not prove every qualitative interpretation or tactical causal claim. Successful Foundry output, cached output, computed facts and template fallbacks have distinct labels.

## Synthetic match and correction

Dataset v3, seed 42, contains 1,085 events. It models two halves, added time, a condensed interval, ends changing, restarts, point-snapshot offside, discipline, second-caution dismissal and five substitutions across three in-play windows. The event-location pitch is not continuous player tracking.

The example goal at 60:30 completes a recovery-to-shot sequence. Withdrawing that goal changes the full-time score from 2–1 to 1–1. This demonstrates correction of an event record. It does not resimulate an alternative match or perform video officiating. Downloaded files cannot be recalled automatically; the correction patch communicates withdrawals to downstream consumers.

All clubs, players and events are fictional. No real Premier League footage or match dataset is included.

## Verify

```sh
.venv/bin/python -m unittest discover -s tests -v
node tests/navigation.test.js
node tests/replay-policy.test.js
node tests/presentation.test.js
```

Node.js is needed only for the standalone JavaScript checks; there are no frontend package dependencies. The latest local Python run passed 66 tests. Real Foundry samples have also exercised the workflow, including a full-time response after the goal-evidence fix; this is sample verification rather than a reliability benchmark.

## Microsoft and Azure technologies

| Technology | Role in Turning XI |
|---|---|
| **Microsoft Foundry / Azure Responses API** | Model-generated explanations, recaps and bounded evidence-tool selection |
| **Azure Container Apps, Consumption** | Hosts FastAPI and the JavaScript frontend together behind HTTPS |
| **Azure Container Registry (ACR), Basic** | Stores the private Linux application image |
| **ACR Tasks** | Builds and checks the container image remotely |
| **Azure Monitor Log Analytics** | Provisioned operational logging workspace; persistent ingestion is disabled for this demo |
| **Azure Resource Manager and Bicep** | Defines and validates the hosting infrastructure through staged deployment |
| **Azure CLI and Microsoft Entra ID** | Authenticates management operations and deployment verification |

The hosting design uses `eastus2`, one container at 0.5 vCPU / 1 GiB, 0–1 replicas, HTTPS ingress, and health probes. Runtime credentials use Container Apps secret references. See [Azure architecture and deployment guide](docs/AZURE_DEPLOYMENT.md) and the [Bicep templates](infra/main.bicep).

The AI workflow uses one model deployment. Managed-identity model authentication is available as an application option; the API-key configuration keeps credentials server-side. The broadcast artifact registry is browser-local and bounded. Application caps control requests rather than providing an Azure billing hard stop.
