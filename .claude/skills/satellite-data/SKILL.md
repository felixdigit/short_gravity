---
name: satellite-data
description: Query SpaceTrack for ASTS satellite orbital data and TLE information
allowed-tools: Bash, Read
---

# Satellite Data Lookup

SpaceTrack credentials are in `.env.local`:
- SPACE_TRACK_USERNAME
- SPACE_TRACK_PASSWORD

Key ASTS satellites (NORAD IDs):
- BlueBird satellites launched 2024

Reference docs:
- @SATELLITE_INTEGRATION_SUMMARY.md
- @SATELLITE_ARCHITECTURE.md

API endpoint: https://www.space-track.org/basicspacedata/query/class/gp/
