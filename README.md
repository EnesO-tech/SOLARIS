# SOLARIS – Solar Aircraft & Drone Design Studio

Conceptual design of solar-powered aircraft, electric drones and multicopters. The physics engine is written in Python (`python/solaris`) and runs in the browser via Pyodide.

**Features:** sun position and irradiance by date, latitude and altitude · day/night energy balance with battery and altitude storage · perpetual-flight check · design-space and season maps · minimum-span sizing · multicopter momentum theory · animated 3D flight with day/night cycle and energy flow · built-in validation suite.

```bash
cd python
python -m solaris presets
python -m solaris run skysailor
python -m solaris size skysailor
python -m solaris validate
python -m pytest -q
```
