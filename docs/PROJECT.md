# Turning XI

**Tagline:** Turn synthetic football events into evidence-grounded stories, personalized insights, and broadcast-ready recaps—updated when the match record changes.

**Challenge:** The Synthetic Match Insights Engine for Premier League Studio

**Keywords:** Synthetic Match Insights, Football Analytics, Agentic AI, Microsoft Foundry, Explainable AI, Broadcast Production, Evidence-Grounded Storytelling

## Overview

Turning XI helps fans and analysts understand how football turning points develop, and helps broadcast teams keep stories consistent after record corrections.

A reproducible synthetic match provides the events, statistics and completed phases visible at the replay time. Microsoft Foundry produces structured explanations for Fan and Analyst audiences, with team preferences and English/Simplified Chinese output. Deeper analysis lets the model select bounded read-only tools to inspect sequences, recent windows and personnel state.

Explanations link to events. Structured claims and references are checked; rejected claims are replaced with computed facts. The Broadcast desk previews and exports the same versioned payload, and demonstrates how withdrawing a synthetic goal updates match facts and identifies dependent content for withdrawal.

The project connects explanation, evidence and correction in one workflow. Its goal is understandable, personalized and traceable football storytelling.

All clubs, players and events are fictional. The project uses synthetic event data. The AI runtime uses Foundry inference through Azure Responses. The application combines a Python backend with a JavaScript interface.

## Microsoft and Azure technologies

Microsoft Foundry provides model inference through Azure Responses. Azure Container Apps hosts the containerized application; Azure Container Registry and ACR Tasks support image storage and cloud builds. An Azure Monitor Log Analytics workspace supports optional operational logging. Azure Resource Manager/Bicep defines the infrastructure, with Azure CLI and Microsoft Entra ID supporting management authentication and release verification. See [Azure deployment architecture](AZURE_DEPLOYMENT.md).
