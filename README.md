# Karbon.io - Personal Carbon Footprint Tracker & Insights Assistant

An interactive, gamified environmental impact platform designed to help individuals track, understand, and reduce their carbon footprint through daily actions, real-time route simulations, and context-aware insights. 
This project was built from scratch as a high-fidelity Single Page Application (SPA) utilizing a modern, responsive Glassmorphic UI over an animated HTML5 Canvas connection map.

---

## 🌍 Hackathon Vertical
**Vertical**: Personal Carbon Footprint Tracker & Insights Assistant.
*Objective*: Empowers users to log simple daily activities, model route choices, visualize impact in real time, and receive tailored advice dynamically reacting to their behaviors.

---

## 🧠 Approach & Logic

### 1. Daily Tracked Savings
The dashboard tracks carbon offsets in three key categories: **Commute**, **Dietary Meals**, and **Household Energy**.
*   **Logical Engine**: The app evaluates active choices and sums up offsets:
    $$\text{Daily CO}_2\text{ Offsets} = \text{Commute Savings} + \text{Meal Savings} + \text{Energy Savings}$$
*   **Gamification**: The savings are translated to equivalent trees planted based on a baseline offset of 10 trees:
    $$\text{Trees Equivalent} = 10 + \lfloor\frac{\text{Total Offsets}}{1.5}\rfloor$$

### 2. Context-Aware Insights Engine
The **Live Insight** assistant acts as a dynamic advisor. Rather than showing static tips, the logical engine runs checks on the user's active choices:
*   If the user selects `car` or `transit` for their daily commute, the advisor recalculates potential offsets and prompts: *"Commute Alert: Switching to Transit or Biking could reduce your transit emissions by up to 4.6kg CO2 today."*
*   If the user selects `meat-light` or `vegetarian`, the assistant prompts dietary upgrades.
*   If the user adjusts their Route Planner transport mode to `car`, it reads the distance slider value ($D$) dynamically to output exact savings: *"Swapping your simulated {D}km car drive for an E-bike saves {Savings}kg CO2!"*
*   If all categories are fully optimized, it rotates high-impact ecological facts and custom logging suggestions.

### 3. Route Simulation Algorithm
The route planner simulates carbon savings dynamically by evaluating the active distance $D$ (from 1 to 50 km) against transport coefficients $C$:
$$\text{Simulated Savings} = D \times C$$
*   *E-Bike Coefficient ($C$)*: `0.27 kg/km`
*   *Bus Coefficient ($C$)*: `0.18 kg/km`
*   *Car Coefficient ($C$)*: `0.05 kg/km` (savings represent car-pooling or EV optimization compared to baseline gas vehicles)

Confirming a trip registers these savings directly to the user's Profile ledger, advances their position on the Global Leaderboard, and increases their rank progress in the **Stratosphere League**.

---

## 🛠️ Step-by-Step Setup & Execution

### Prerequisites
Make sure you have [Node.js](https://nodejs.org/) installed (v16.0.0 or higher recommended) and Python 3.10+.

### 1. Installation
Clone the repository, navigate to the folder, and install development dependencies:
```bash
git clone <repository-url>
cd CarbonFootprint
npm install
python -m pip install -r backend/requirements.txt
```

### 2. Run the Backend API
Launch the local FastAPI server:
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The backend uses `backend/karbon.db` by default for local persistence. Optional external services are read from environment variables only:

```bash
export GEMINI_API_KEY="..."
export GOOGLE_MAPS_API_KEY="..."
export FIREBASE_CREDENTIALS_PATH="/absolute/path/to/firebase-service-account.json"
```

If these are unset, the API stays usable with local SQLite storage, mocked route details, and deterministic insight fallbacks.

### 3. Run the Frontend Development Server
In another terminal, launch the local Vite server:
```bash
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

To point the frontend at a non-default API URL, set:
```bash
VITE_API_BASE_URL="http://127.0.0.1:8000" npm run dev
```

### 4. Build for Production
To build static production-ready bundles, run:
```bash
npm run build
```
Compiled assets will be outputted to the `/dist` folder.

---

## 📊 Assumed Coefficients & Metrics

The tracker operates on the following carbon offset coefficients (representing emissions saved compared to baseline high-carbon equivalents, e.g., driving a standard gasoline car or eating a high-meat diet):

| Category | Option | Savings Coefficient (kg CO₂ / day) | Baseline / Rationale |
| :--- | :--- | :--- | :--- |
| **Commute** | Walk | **4.8 kg** | Replaces 15km average car commute |
| **Commute** | Bike | **4.0 kg** | Replaces 15km average car commute (accounting for energy expenditure) |
| **Commute** | Transit | **3.2 kg** | Replaces single-occupancy vehicle travel |
| **Commute** | Car | **0.2 kg** | Carpooling or EV optimization compared to standard ICE vehicle |
| **Meals** | Vegan | **5.2 kg** | Compared to high-beef/meat diet footprint |
| **Meals** | Vegetarian | **3.6 kg** | Compared to high-meat diet |
| **Meals** | Meat-light | **1.6 kg** | Incorporating poultry/fish only |
| **Energy** | High Efficiency | **2.4 kg** | Smart thermostat & EnergyStar HVAC savings |
| **Energy** | Lights Off | **1.2 kg** | Shutting off unused light bulbs and peripherals |

### Route Planner Baseline (Emissions relative to average 22 MPG single passenger vehicle):
*   **E-Bike offset factor**: `0.27 kg/km`
*   **Bus offset factor**: `0.18 kg/km`
*   **Hybrid Car offset factor**: `0.05 kg/km`
*   *Tree absorption scale*: One mature tree absorbs roughly `20.0 kg` of CO₂ annually (modeled in our Profile stats ledger).

---

## 🔒 Security & Safe Handling

- **Data Privacy**: Dashboard metrics hydrate from the local FastAPI backend and persist to the local SQLite database by default.
- **Zero Tracker Bloat**: To stay strictly under the **10 MB size limit**, the project avoids pulling in large external UI component libraries or heavy backend databases.
- **API Keys**: No sensitive client keys are hardcoded. Optional Gemini, Google Maps, and Firebase Admin credentials are read only from environment variables and are not required for local demo mode.
