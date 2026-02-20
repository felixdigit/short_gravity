# SHORT GRAVITY — Architecture Overview

**Version:** 1.0  
**Last Updated:** 2026-01-20  
**Status:** Initial Architecture Definition

---

## Product Definition

**Short Gravity** is an autonomous intelligence aggregator and visualization engine for the space economy. It provides real-time anomaly detection, orbital asset verification, and synthesized strategic briefings.

### Deployment Targets
- **Web Terminal:** Full-fidelity "Mission Control" experience (desktop/mobile responsive)
- **iOS App:** "Pocket Radar" for push notifications, quick-glance telemetry, mobile-native briefings

---

## Core Components

| Component | Function | Output |
|-----------|----------|--------|
| **Signal Engine** | Autonomous anomaly detection across regulatory, physical, and market data streams | Raw signals flagging deviations from baseline |
| **Cockpit** | 1:1 digital twin of orbital environment | Real-time visualization of satellite positions, coverage, line-of-sight |
| **Briefing** | Synthesis layer combining Signal + Verification | Structured intelligence reports with investment/strategic implications |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ACCESS POINTS                                   │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐     │
│  │      WEB TERMINAL           │    │         iOS APP                 │     │
│  │  (React + Next.js)          │    │    (React Native + Expo)        │     │
│  │  - Full dashboards          │    │    - Push notifications         │     │
│  │  - 3D orbital viz           │    │    - Quick-glance telemetry     │     │
│  │  - Deep research            │    │    - Mobile briefings           │     │
│  └──────────────┬──────────────┘    └───────────────┬─────────────────┘     │
└─────────────────┼───────────────────────────────────┼───────────────────────┘
                  │                                   │
                  └───────────────┬───────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                           API GATEWAY (Supabase Edge)                        │
│                    Authentication • Rate Limiting • Routing                  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────────────┐
│   SIGNAL ENGINE   │   │     COCKPIT       │   │        BRIEFING           │
│                   │   │                   │   │                           │
│  ┌─────────────┐  │   │  ┌─────────────┐  │   │  ┌─────────────────────┐  │
│  │ Listeners   │  │   │  │ TLE Parser  │  │   │  │ Claude API          │  │
│  │ - Regulatory│  │   │  │ (SGP4/SDP4) │  │   │  │ (Synthesis Engine)  │  │
│  │ - Physical  │  │   │  └──────┬──────┘  │   │  └──────────┬──────────┘  │
│  │ - Market    │  │   │         │         │   │             │             │
│  └──────┬──────┘  │   │  ┌──────▼──────┐  │   │  ┌──────────▼──────────┐  │
│         │         │   │  │ Propagator  │  │   │  │ Report Generator    │  │
│  ┌──────▼──────┐  │   │  │ (Position   │  │   │  │ - Signal Context    │  │
│  │ Baseline    │  │   │  │  Calc)      │  │   │  │ - Asset Verify      │  │
│  │ Calculator  │  │   │  └──────┬──────┘  │   │  │ - Implications      │  │
│  └──────┬──────┘  │   │         │         │   │  └─────────────────────┘  │
│         │         │   │  ┌──────▼──────┐  │   │                           │
│  ┌──────▼──────┐  │   │  │ Coverage    │  │   └───────────────────────────┘
│  │ Anomaly     │  │   │  │ Calculator  │  │
│  │ Detector    │  │   │  └─────────────┘  │
│  └─────────────┘  │   │                   │
│                   │   └───────────────────┘
└───────────────────┘

                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER (Supabase)                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   PostgreSQL    │  │    Realtime     │  │         Storage             │  │
│  │   - Users       │  │   - Signals     │  │   - TLE Archives            │  │
│  │   - Watchlists  │  │   - Positions   │  │   - Report PDFs             │  │
│  │   - Briefings   │  │   - Alerts      │  │   - Historical Data         │  │
│  │   - Baselines   │  │                 │  │                             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL DATA SOURCES                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Space-Track │  │ SEC/EDGAR   │  │ Market APIs │  │ News/Regulatory     │ │
│  │ (TLE Data)  │  │ (Filings)   │  │ (Prices)    │  │ (RSS/Webhooks)      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Summary

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Web Frontend** | Next.js 14+ (App Router) | SSR, API routes, optimal for dashboards |
| **iOS Frontend** | React Native + Expo | Native performance, shared logic with web |
| **3D Visualization** | Three.js / React Three Fiber | WebGL orbital rendering |
| **Backend** | Supabase (Edge Functions, PostgreSQL) | Serverless, real-time, row-level security |
| **AI Synthesis** | Claude API (Sonnet/Opus) | High-quality analysis generation |
| **Orbital Mechanics** | satellite.js (SGP4/SDP4) | Industry-standard propagation |
| **Auth** | Supabase Auth + JWT | Cross-platform, secure |
| **Push Notifications** | Expo Push + APNs | Native iOS integration |

---

## Document Index

| File | Purpose |
|------|---------|
| `01-SIGNAL-ENGINE.md` | Anomaly detection system architecture |
| `02-COCKPIT.md` | Orbital visualization architecture |
| `03-BRIEFING.md` | AI synthesis layer architecture |
| `04-DATA-MODEL.md` | Database schema and relationships |
| `05-API-CONTRACTS.md` | Endpoint definitions and types |
| `06-WEB-FRONTEND.md` | Next.js web application structure |
| `07-IOS-APP.md` | React Native mobile app structure |
| `08-DEPLOYMENT.md` | CI/CD, hosting, and infrastructure |
| `09-SECURITY.md` | Auth, RLS, and compliance |

---

## Quick Start for AI Editing

When working with these architecture files:

1. **Each file is self-contained** — edit independently
2. **Cross-references use relative links** — update if you rename files
3. **Code blocks are implementation hints** — not final code
4. **Tables define contracts** — keep them updated when changing APIs
5. **Version and date at top** — update when making significant changes

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-20 | Next.js over pure React for web | Need SSR for SEO, API routes reduce backend complexity |
| 2026-01-20 | Supabase over custom backend | Real-time built-in, RLS for security, edge functions for scale |
| 2026-01-20 | satellite.js for orbital math | Proven SGP4/SDP4 implementation, runs client-side |
| 2026-01-20 | Claude for synthesis | Best quality for financial/strategic analysis |
