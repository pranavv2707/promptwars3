/* ==========================================================================
   KARBON.IO - APPLICATION CORE LOGIC
   ========================================================================== */

// --------------------------------------------------------------------------
// 1. Global State Management & Security Utilities
// --------------------------------------------------------------------------

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Keyboard accessibility support
function setupKeyboardNavigation() {
  document.addEventListener('keydown', (e) => {
    // Alt+1-4 for navigation (accessibility shortcuts)
    if (e.altKey && e.key >= '1' && e.key <= '4') {
      e.preventDefault();
      const navItems = [
        DOM.navBtnCommandCenter,
        DOM.navBtnEcoArena,
        DOM.navBtnNotifications,
        DOM.navBtnProfile
      ];
      const navItem = navItems[parseInt(e.key) - 1];
      if (navItem) navItem.click();
    }

    // Escape to close modals
    if (e.key === 'Escape' && DOM.logImpactModal && DOM.logImpactModal.classList.contains('show')) {
      closeLogImpactModal();
    }
  });
}

// Enhance focus management for modals
function enhanceModalAccessibility(modal) {
  if (!modal) return;
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-labelledby', 'modal-title');

  const closeBtn = modal.querySelector('.btn-close, .btn-cancel, [aria-label="Close"]');
  if (closeBtn) {
    closeBtn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        closeBtn.click();
      }
    });
  }
}

// Add ARIA labels to button groups
function enhanceButtonAccessibility(button, label) {
  if (!button) return;
  button.setAttribute('aria-label', label);
  button.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      button.click();
    }
  });
}

// Bypasses the Vite empty proxy and connects directly to FastAPI on port 8000
//const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const CURRENT_USER_ID = "user_alex";
const CURRENT_CIRCLE_ID = "circle_demo_01";

function getSelectedEnergyActions() {
  const actions = [];
  if (state.energyEfficiency) actions.push("high_efficiency");
  if (state.energyLights) actions.push("lights_off");
  return actions;
}

function mapApiLeaderboardEntry(entry) {
  const tier = getTier(entry.co2_saved_total);
  return {
    name: entry.name,
    location: entry.location,
    tier: tier.label,
    class: tier.className,
    allTime: entry.co2_saved_total,
    month: entry.co2_saved_month,
    avatarColor: entry.is_current_user ? "#0f172a" : getAvatarColor(entry.rank),
    badge: entry.rank === 1 ? "⭐" : entry.is_current_user ? "🛡️" : "-",
    isUser: entry.is_current_user
  };
}

function getTier(totalSaved) {
  if (totalSaved >= 2400) return { label: "ELITE GUARDIAN", className: "tier-elite" };
  if (totalSaved >= 2200) return { label: "NET-ZERO HERO", className: "tier-netzero" };
  if (totalSaved >= 2050) return { label: "CARBON KNIGHT", className: "tier-carbon" };
  return { label: "ECO WARRIOR", className: "tier-warrior" };
}

function getAvatarColor(rank) {
  const colors = ["#10b981", "#3b82f6", "#ffb95f", "#64748b", "#8b5cf6"];
  return colors[(rank - 1) % colors.length];
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Backend request failed");
  }
  return data;
}

async function logDailyHabits(userId, commuteMode, mealType, energyActions, notes = "") {
  return apiRequest("/api/logs/daily", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      commute_mode: commuteMode,
      meal_type: mealType,
      energy_actions: energyActions,
      notes
    })
  });
}

async function fetchLeaderboard(circleId, currentUserId) {
  return apiRequest(`/api/leaderboard/${circleId}?user_id=${currentUserId}`);
}

async function fetchAIPersonalInsights(userId) {
  const insights = await apiRequest(`/api/users/${userId}/insights`);
  return insights.insight_tip;
}

async function fetchBackendHealth() {
  return apiRequest("/api/health");
}

async function refreshLiveAssistant() {
  const insight = await fetchAIPersonalInsights(CURRENT_USER_ID);
  const insightElement = document.getElementById("live-insight-text");
  if (insight && insightElement) {
    insightElement.textContent = insight;
  }
}

function updateBackendStatusToast(health) {
  if (!health.ok) return;
  const missing = [];
  if (!health.gemini_configured) missing.push("Gemini");
  if (!health.google_maps_configured) missing.push("Google Maps");
  if (missing.length > 0) {
    showToast(`${missing.join(" and ")} key not configured in backend/.env`);
  }
}

async function logCustomImpact(userId, actionKey, label) {
  return apiRequest("/api/logs/custom", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      action_key: actionKey,
      label
    })
  });
}

async function logRoute(userId, mode, distanceKm) {
  return apiRequest("/api/logs/route", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      origin: state.routeOrigin,
      destination: state.routeDestination,
      chosen_mode: mode,
      baseline_mode: "car"
    })
  });
}

async function syncLeaderboardFromBackend() {
  const leaderboard = await fetchLeaderboard(CURRENT_CIRCLE_ID, CURRENT_USER_ID);
  state.leaderboard = leaderboard.map(mapApiLeaderboardEntry);

  const currentUser = leaderboard.find(entry => entry.is_current_user);
  if (currentUser) {
    state.user.name = currentUser.name;
    state.user.co2SavedAllTime = currentUser.co2_saved_total;
    state.user.co2SavedMonth = currentUser.co2_saved_month;
    state.user.rank = currentUser.rank;
    state.user.leagueProgress = Math.min(100, Math.max(0, Math.round(currentUser.reduction_pct)));
  }

  updateEcoArenaView();
  updateProfileStats();
}

const state = {
  user: {
    name: "Alex Chen",
    co2SavedAllTime: 1894.2,
    co2SavedMonth: 320.4,
    level: 42,
    rank: 14,
    leagueProgress: 85
  },
  
  // Active tracking values (savings in kg/day)
  commuteMode: "bike",
  mealsMode: "vegan",
  energyEfficiency: true,
  energyLights: false,
  
  // Route planner state - London centered
  routeMode: "ebike",
  routeDistance: 11.5, // in km
  routeOrigin: "home",
  routeDestination: "office",
  routeStartCoords: null,
  routeEndCoords: null,
  
  // Active views
  currentTab: "view-command-center",
  leaderboardTab: "alltime",
  
  // Search query
  searchQuery: "",

  // Leaderboard mock database
  leaderboard: [
    { name: "Elena Greenheart", location: "Oslo, Norway", tier: "ELITE GUARDIAN", class: "tier-elite", allTime: 2482.5, month: 395.2, avatarColor: "#10b981", badge: "⭐", isUser: false },
    { name: "Hiroshi Tanaka", location: "Kyoto, Japan", tier: "NET-ZERO HERO", class: "tier-netzero", allTime: 2310.1, month: 410.5, avatarColor: "#3b82f6", badge: "-", isUser: false },
    { name: "Sofia Rossi", location: "Milan, Italy", tier: "CARBON KNIGHT", class: "tier-carbon", allTime: 2155.8, month: 298.1, avatarColor: "#ffb95f", badge: "-", isUser: false },
    { name: "Jordan Smith", location: "Austin, USA", tier: "ECO WARRIOR", class: "tier-warrior", allTime: 1980.4, month: 240.2, avatarColor: "#64748b", badge: "🛡️", isUser: false },
    { name: "Alex Chen", location: "Kensington, London", tier: "NET-ZERO HERO", class: "tier-netzero", allTime: 1894.2, month: 320.4, avatarColor: "#0f172a", badge: "🛡️", isUser: true }
  ]
};

// CO2 Savings constants for logging activity cards (kg CO2 / day saved)
const SAVINGS_VALUES = {
  commute: { walk: 4.8, bike: 4.0, transit: 3.2, car: 0.2 },
  meals: { vegan: 5.2, vegetarian: 3.6, "meat-light": 1.6 },
  energy: { efficiency: 2.4, lights: 1.2 }
};

// Route planner CO2 savings factors (kg saved per km)
const ROUTE_FACTORS = {
  car: 0.05,
  bus: 0.18,
  ebike: 0.27
};

// --------------------------------------------------------------------------
// 2. DOM Elements Cache
// --------------------------------------------------------------------------
let DOM = {};

function initDOM() {
  DOM = {
    // Navigation
    navBtnCommandCenter: document.getElementById("nav-command-center"),
    navBtnEcoArena: document.getElementById("nav-eco-arena"),
    navBtnNotifications: document.getElementById("nav-notifications"),
    navBtnProfile: document.getElementById("nav-profile"),
    mobileMenuToggle: document.getElementById("mobile-menu-toggle"),
    mobileMenuClose: document.getElementById("mobile-menu-close"),
    sidebar: document.querySelector(".sidebar"),
    
    // View containers
    viewCommandCenter: document.getElementById("view-command-center"),
    viewEcoArena: document.getElementById("view-eco-arena"),
    viewNotifications: document.getElementById("view-notifications"),
    viewProfile: document.getElementById("view-profile"),
    
    // Summary Card
    btnToggleToday: document.getElementById("btn-toggle-today"),
    btnToggleWeek: document.getElementById("btn-toggle-week"),
    treesCounter: document.getElementById("trees-counter"),
    summaryTreesText: document.getElementById("summary-trees-text"),
    
    // Commute
    btnCommuteWalk: document.getElementById("btn-commute-walk"),
    btnCommuteBike: document.getElementById("btn-commute-bike"),
    btnCommuteTransit: document.getElementById("btn-commute-transit"),
    btnCommuteCar: document.getElementById("btn-commute-car"),
    
    // Meals
    btnMealsVegan: document.getElementById("btn-meals-vegan"),
    btnMealsVegetarian: document.getElementById("btn-meals-vegetarian"),
    btnMealsMeatLight: document.getElementById("btn-meals-meat-light"),
    
    // Energy
    toggleEnergyEfficiency: document.getElementById("toggle-energy-efficiency"),
    toggleEnergyLights: document.getElementById("toggle-energy-lights"),
    bulletLights: document.getElementById("bullet-lights"),
    
    // Route Planner
    btnRouteCar: document.getElementById("btn-route-car"),
    btnRouteBus: document.getElementById("btn-route-bus"),
    btnRouteEbike: document.getElementById("btn-route-ebike"),
    savingsAmount: document.getElementById("savings-amount"),
    btnConfirmTrip: document.getElementById("btn-confirm-trip"),
    routeDistanceSlider: document.getElementById("route-distance-slider"),
    routeDistanceVal: document.getElementById("route-distance-val"),
    routeFillTrack: document.getElementById("route-fill-track"),
    routeHandleGlow: document.getElementById("route-handle-glow"),
    routeOriginInput: document.getElementById("route-origin-input"),
    routeDestinationInput: document.getElementById("route-destination-input"),
    routeOriginLabel: document.getElementById("route-origin-label"),
    routeDestinationLabel: document.getElementById("route-destination-label"),
    routeMapFrame: document.getElementById("route-map-frame"),
    
    // Eco Arena elements
    leaderboardSearch: document.getElementById("leaderboard-search"),
    btnLeaderboardAllTime: document.getElementById("btn-leaderboard-alltime"),
    btnLeaderboardMonth: document.getElementById("btn-leaderboard-month"),
    leaderboardBody: document.getElementById("leaderboard-body"),
    leagueProgressPct: document.getElementById("league-progress-pct"),
    leagueProgressFill: document.getElementById("league-progress-fill"),
    familyAlexVal: document.getElementById("family-alex-val"),
    familyAlexFill: document.getElementById("family-alex-fill"),
    leaderboardAlexCo2: document.getElementById("leaderboard-alex-co2"),
    
    // Profile Stat Display
    profileStatCo2: document.getElementById("profile-stat-co2"),
    profileStatTrees: document.getElementById("profile-stat-trees"),
    
    // Modal & Toast
    btnLogImpactSidebar: document.getElementById("btn-log-impact-sidebar"),
    logImpactModal: document.getElementById("log-impact-modal"),
    btnCloseModal: document.getElementById("btn-close-modal"),
    btnCancelLog: document.getElementById("btn-cancel-log"),
    btnConfirmLog: document.getElementById("btn-confirm-log"),
    customImpactSelect: document.getElementById("custom-impact-select"),
    toastContainer: document.getElementById("toast-container"),
    canvas: document.getElementById("live-map-canvas")
  };
}

// --------------------------------------------------------------------------
// 3. App Router / Tabs switcher
// --------------------------------------------------------------------------
function setupRouter() {
  const navItems = [
    DOM.navBtnCommandCenter,
    DOM.navBtnEcoArena,
    DOM.navBtnNotifications,
    DOM.navBtnProfile
  ];
  
  const views = [
    DOM.viewCommandCenter,
    DOM.viewEcoArena,
    DOM.viewNotifications,
    DOM.viewProfile
  ];

  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const targetId = item.getAttribute("data-target");
      
      DOM.sidebar.classList.remove("menu-open");
      
      navItems.forEach(nav => nav.classList.remove("active"));
      item.classList.add("active");
      
      views.forEach(view => {
        if (view.id === targetId) {
          view.style.display = "block";
          void view.offsetWidth; 
          view.classList.add("active");
        } else {
          view.classList.remove("active");
          view.style.display = "none";
        }
      });
      
      state.currentTab = targetId;
      
      triggerCanvasWave(window.innerWidth / 2, window.innerHeight / 2, "#3b82f6");
    });
  });

  DOM.mobileMenuToggle.addEventListener("click", () => {
    DOM.sidebar.classList.add("menu-open");
  });

  DOM.mobileMenuClose.addEventListener("click", () => {
    DOM.sidebar.classList.remove("menu-open");
  });
}

// --------------------------------------------------------------------------
// 4. Live Map Canvas Animation
// --------------------------------------------------------------------------
let canvasContext = null;
let mapNodes = [];
let mapParticles = [];
let canvasWaves = [];

function setupCanvasMap() {
  const canvas = DOM.canvas;
  canvasContext = canvas.getContext("2d");
  
  const resizeCanvas = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    generateNodes();
  };
  
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();
  
  function animate() {
    drawMap();
    requestAnimationFrame(animate);
  }
  animate();
  
  setInterval(() => {
    if (mapNodes.length > 0) {
      const randomNode = mapNodes[Math.floor(Math.random() * mapNodes.length)];
      triggerCanvasWave(randomNode.x, randomNode.y, "#10b981", 120);
    }
  }, 4000);
}

function generateNodes() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const numNodes = Math.floor((width * height) / 45000) + 10;
  
  mapNodes = [];
  mapParticles = [];
  
  for (let i = 0; i < numNodes; i++) {
    mapNodes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 3 + 2,
      baseRadius: Math.random() * 2 + 1.5,
      pulseSpeed: Math.random() * 0.05 + 0.02,
      pulseValue: Math.random() * Math.PI,
      brightness: Math.random() * 0.4 + 0.4
    });
  }

  for (let i = 0; i < mapNodes.length; i++) {
    const nodeA = mapNodes[i];
    let connectionsCount = 0;
    
    const targets = mapNodes
      .map((n, idx) => ({ idx, dist: Math.hypot(n.x - nodeA.x, n.y - nodeA.y) }))
      .filter(t => t.idx !== i)
      .sort((a, b) => a.dist - b.dist);
      
    for (let j = 0; j < Math.min(2, targets.length); j++) {
      const target = mapNodes[targets[j].idx];
      if (targets[j].dist < 280) {
        mapParticles.push({
          startNode: nodeA,
          endNode: target,
          progress: Math.random(),
          speed: (Math.random() * 0.002 + 0.001),
          size: Math.random() * 2 + 1
        });
      }
    }
  }
}

function triggerCanvasWave(x, y, color = "#4edea3", maxRadius = 180) {
  canvasWaves.push({
    x,
    y,
    radius: 0,
    maxRadius,
    speed: 3,
    color,
    opacity: 0.8
  });
}

function drawMap() {
  const ctx = canvasContext;
  if (!ctx) return;
  
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  
  const width = ctx.canvas.width;
  const height = ctx.canvas.height;
  
  ctx.strokeStyle = "rgba(255, 255, 255, 0.012)";
  ctx.lineWidth = 1;
  const gridSize = 40;
  for (let x = 0; x < width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  
  ctx.strokeStyle = "rgba(173, 198, 255, 0.03)";
  ctx.lineWidth = 1;
  for (let i = 0; i < mapParticles.length; i++) {
    const p = mapParticles[i];
    ctx.beginPath();
    ctx.moveTo(p.startNode.x, p.startNode.y);
    ctx.lineTo(p.endNode.x, p.endNode.y);
    ctx.stroke();
  }
  
  for (let i = 0; i < mapParticles.length; i++) {
    const p = mapParticles[i];
    p.progress += p.speed;
    if (p.progress >= 1) {
      p.progress = 0;
      const temp = p.startNode;
      p.startNode = p.endNode;
      p.endNode = temp;
    }
    
    const px = p.startNode.x + (p.endNode.x - p.startNode.x) * p.progress;
    const py = p.startNode.y + (p.endNode.y - p.startNode.y) * p.progress;
    
    ctx.fillStyle = "rgba(78, 222, 163, 0.4)";
    ctx.beginPath();
    ctx.circle = ctx.arc(px, py, p.size, 0, Math.PI * 2);
    ctx.fill();
  }
  
  for (let i = 0; i < mapNodes.length; i++) {
    const n = mapNodes[i];
    n.pulseValue += n.pulseSpeed;
    n.radius = n.baseRadius + Math.sin(n.pulseValue) * 1.5;
    
    const glowGradient = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.radius * 3);
    glowGradient.addColorStop(0, `rgba(78, 222, 163, ${n.brightness * 0.3})`);
    glowGradient.addColorStop(1, "rgba(78, 222, 163, 0)");
    
    ctx.fillStyle = glowGradient;
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius * 3, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.fillStyle = `rgba(173, 198, 255, ${n.brightness})`;
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
    ctx.fill();
  }
  
  for (let i = canvasWaves.length - 1; i >= 0; i--) {
    const w = canvasWaves[i];
    w.radius += w.speed;
    w.opacity = 1 - (w.radius / w.maxRadius);
    
    if (w.opacity <= 0) {
      canvasWaves.splice(i, 1);
      continue;
    }
    
    ctx.strokeStyle = w.color;
    ctx.lineWidth = 2;
    ctx.globalAlpha = w.opacity;
    
    ctx.beginPath();
    ctx.arc(w.x, w.y, w.radius, 0, Math.PI * 2);
    ctx.stroke();
    
    if (w.radius > 30) {
      ctx.beginPath();
      ctx.arc(w.x, w.y, w.radius - 30, 0, Math.PI * 2);
      ctx.stroke();
    }
    
    ctx.globalAlpha = 1.0;
  }
}

// --------------------------------------------------------------------------
// 5. Activity Log & Toggles Calculations
// --------------------------------------------------------------------------
function calculateDailySummary() {
  const commuteSaving = SAVINGS_VALUES.commute[state.commuteMode];
  const mealSaving = SAVINGS_VALUES.meals[state.mealsMode];
  const efficiencySaving = state.energyEfficiency ? SAVINGS_VALUES.energy.efficiency : 0;
  const lightsSaving = state.energyLights ? SAVINGS_VALUES.energy.lights : 0;
  
  const totalDailySaved = commuteSaving + mealSaving + efficiencySaving + lightsSaving;
  
  const treesCount = 10 + Math.floor(totalDailySaved / 1.5);
  
  const currentCount = parseInt(DOM.treesCounter.textContent);
  animateCounter(DOM.treesCounter, currentCount, treesCount);
  DOM.summaryTreesText.textContent = treesCount;
  
  updateDynamicInsights();
}

function updateDynamicInsights() {
  const insights = [];
  
  if (state.commuteMode === "car") {
    insights.push("Commute Alert: Switching to Transit or Biking could reduce your transit emissions by up to 4.6kg CO2 today.");
  } else if (state.commuteMode === "transit") {
    insights.push("Commute Tip: Choosing a standard Bike or walking for this trip saves an extra 1.6kg CO2.");
  }
  
  if (state.mealsMode === "meat-light") {
    insights.push("Diet Tip: Swapping a meat-light meal for a Vegan option saves 3.6kg CO2 daily.");
  } else if (state.mealsMode === "vegetarian") {
    insights.push("Diet Tip: Going fully Vegan today will reduce your food carbon footprint by an additional 1.6kg CO2.");
  }
  
  if (!state.energyEfficiency) {
    insights.push("Energy Saving: Activating High Efficiency systems will automatically shave 2.4kg CO2 off your daily output.");
  }
  if (!state.energyLights) {
    insights.push("Efficiency Hack: Turning off unused lights saves 1.2kg CO2 and prolongs bulb lifespan.");
  }
  
  if (state.routeMode === "car") {
    insights.push(`Route Advisor: Swapping your simulated ${state.routeDistance.toFixed(1)}km car drive for an E-bike saves ${(state.routeDistance * (ROUTE_FACTORS.ebike - ROUTE_FACTORS.car)).toFixed(1)}kg CO2!`);
  } else if (state.routeMode === "bus") {
    insights.push(`Route Advisor: Biking this simulated ${state.routeDistance.toFixed(1)}km commute instead of taking the bus shaves off an extra ${(state.routeDistance * (ROUTE_FACTORS.ebike - ROUTE_FACTORS.bus)).toFixed(1)}kg CO2.`);
  }

  if (insights.length === 0) {
    insights.push("Optimal Level Reached! All systems running on green energy. Try logging custom impacts!");
    insights.push("Did you know? Planting one young tree neutralizes 15kg of carbon emissions over its growth period.");
    insights.push("Tip: Switch to LED bulbs around your home to save up to 1.2kg CO2 every day.");
  }

  const element = document.getElementById("live-insight-text");
  if (element) {
    element.textContent = insights[Math.floor(Math.random() * insights.length)];
  }
}

function animateCounter(element, start, end) {
  if (start === end) return;
  const duration = 400; // ms
  const startTime = performance.now();
  
  function update(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const val = Math.floor(progress * (end - start) + start);
    element.textContent = val;
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = end;
    }
  }
  requestAnimationFrame(update);
}

function setupActivityListeners() {
  const commuteBtns = [
    { el: DOM.btnCommuteWalk, value: "walk" },
    { el: DOM.btnCommuteBike, value: "bike" },
    { el: DOM.btnCommuteTransit, value: "transit" },
    { el: DOM.btnCommuteCar, value: "car" }
  ];

  commuteBtns.forEach(item => {
    item.el.addEventListener("click", () => {
      commuteBtns.forEach(btn => btn.el.classList.remove("active"));
      item.el.classList.add("active");
      state.commuteMode = item.value;
      calculateDailySummary();
      
      const rect = item.el.getBoundingClientRect();
      triggerCanvasWave(rect.left + rect.width/2, rect.top + rect.height/2, "#4edea3", 120);
    });
  });

  const mealBtns = [
    { el: DOM.btnMealsVegan, value: "vegan" },
    { el: DOM.btnMealsVegetarian, value: "vegetarian" },
    { el: DOM.btnMealsMeatLight, value: "meat-light" }
  ];

  mealBtns.forEach(item => {
    item.el.addEventListener("click", () => {
      mealBtns.forEach(btn => btn.el.classList.remove("active"));
      item.el.classList.add("active");
      state.mealsMode = item.value;
      calculateDailySummary();
      
      const rect = item.el.getBoundingClientRect();
      triggerCanvasWave(rect.left + rect.width/2, rect.top + rect.height/2, "#4edea3", 100);
      
      const card = document.getElementById("card-meals");
      triggerSuccessPulseOnCard(card);
    });
  });

  DOM.toggleEnergyEfficiency.addEventListener("change", (e) => {
    state.energyEfficiency = e.target.checked;
    calculateDailySummary();
    
    const card = document.getElementById("card-energy");
    triggerSuccessPulseOnCard(card);
  });

  DOM.toggleEnergyLights.addEventListener("change", (e) => {
    state.energyLights = e.target.checked;
    
    if (state.energyLights) {
      DOM.bulletLights.className = "bullet-green";
    } else {
      DOM.bulletLights.className = "bullet-inactive";
    }
    
    calculateDailySummary();
    
    const card = document.getElementById("card-energy");
    triggerSuccessPulseOnCard(card);
  });

  DOM.btnToggleToday.addEventListener("click", () => {
    DOM.btnToggleToday.classList.add("active");
    DOM.btnToggleWeek.classList.remove("active");
    calculateDailySummary();
  });

  DOM.btnToggleWeek.addEventListener("click", () => {
    DOM.btnToggleWeek.classList.add("active");
    DOM.btnToggleToday.classList.remove("active");
    
    const currentCount = parseInt(DOM.treesCounter.textContent);
    animateCounter(DOM.treesCounter, currentCount, currentCount * 7 - 5);
    DOM.summaryTreesText.textContent = currentCount * 7 - 5;
  });
}

function triggerSuccessPulseOnCard(cardElement) {
  cardElement.classList.add("card-active-pulse");
  setTimeout(() => {
    cardElement.classList.remove("card-active-pulse");
  }, 2000);
}

// --------------------------------------------------------------------------
// 6. Route Planner Logic & Calculations
// --------------------------------------------------------------------------

function hideStaticOverlays() {
  const elementsToHide = [
    ".route-visual-overlay", ".static-route", ".map-overlay-line", 
    ".map-marker-start", ".map-marker-end", ".route-overlay",
    "[class*='route-line']", "[class*='map-marker']", "[class*='static-line']"
  ];
  elementsToHide.forEach(selector => {
    document.querySelectorAll(selector).forEach(el => {
      el.style.display = "none";
    });
  });
}

// Drops a clear, visible pinpoint needle directly on your stop destination on the OpenStreetMap
function routeMapUrlDynamic(startCoords, endCoords) {
  const minLng = Math.min(startCoords.lng, endCoords.lng);
  const maxLng = Math.max(startCoords.lng, endCoords.lng);
  const minLat = Math.min(startCoords.lat, endCoords.lat);
  const maxLat = Math.max(startCoords.lat, endCoords.lat);
  
  const diffLat = Math.max(0.003, maxLat - minLat);
  const diffLng = Math.max(0.003, maxLng - minLng);
  
  const bbox = [
    minLng - diffLng * 0.25,
    minLat - diffLat * 0.25,
    maxLng + diffLng * 0.25,
    maxLat + diffLat * 0.25
  ].map(value => value.toFixed(5)).join("%2C");
  
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${endCoords.lat}%2C${endCoords.lng}`;
}

function routeMapUrl() {
  const centerLng = -0.1278;
  const centerLat = 51.5074;
  const width = 0.12;
  const height = 0.08;
  const bbox = [
    centerLng - width / 2,
    centerLat - height / 2,
    centerLng + width / 2,
    centerLat + height / 2
  ].map(value => value.toFixed(5)).join("%2C");
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik`;
}

function updateRouteMap() {
  if (DOM.routeOriginLabel) {
    DOM.routeOriginLabel.textContent = state.routeOrigin === "home" ? "Home" : state.routeOrigin === "office" ? "Office" : "Visiting Place";
  }
  if (DOM.routeDestinationLabel) {
    DOM.routeDestinationLabel.textContent = state.routeDestination === "home" ? "Home" : state.routeDestination === "office" ? "Office" : "Visiting Place";
  }
  
  if (DOM.routeMapFrame) {
    if (state.routeStartCoords && state.routeEndCoords) {
      DOM.routeMapFrame.src = routeMapUrlDynamic(state.routeStartCoords, state.routeEndCoords);
    } else {
      DOM.routeMapFrame.src = routeMapUrl();
    }
  }
}

function updateRoutePlanner() {
  const mode = state.routeMode;
  const distance = state.routeDistance;
  const factor = ROUTE_FACTORS[mode];
  
  const totalSaved = distance * factor;
  DOM.savingsAmount.textContent = `${totalSaved.toFixed(1)}kg CO2`;
  DOM.routeDistanceVal.textContent = `${distance.toFixed(1)} km`;
  
  if (DOM.routeFillTrack && DOM.routeHandleGlow) {
    const percent = ((distance - 1) / 49) * 100;
    DOM.routeFillTrack.style.width = `${percent}%`;
    DOM.routeHandleGlow.style.left = `${percent}%`;
  }
  updateRouteMap();
  
  updateDynamicInsights();
}

function setupRoutePlanner() {
  const modes = [
    { el: DOM.btnRouteCar, mode: "car" },
    { el: DOM.btnRouteBus, mode: "bus" },
    { el: DOM.btnRouteEbike, mode: "ebike" }
  ];

  modes.forEach(item => {
    item.el.addEventListener("click", () => {
      modes.forEach(m => m.el.classList.remove("active"));
      item.el.classList.add("active");
      state.routeMode = item.mode;
      updateRoutePlanner();
    });
  });

  if (DOM.routeDistanceSlider) {
    DOM.routeDistanceSlider.addEventListener("input", (e) => {
      const sliderVal = parseFloat(e.target.value);
      state.routeDistance = 1 + (sliderVal - 1) * 0.49;
      updateRoutePlanner();
    });
  }

  // Auto-queries the backend simulation endpoint on dropdown changes to update distance, calculations, and pins in real-time
  const updateRouteEndpoints = async () => {
    const originSelect = DOM.routeOriginInput;
    const destSelect = DOM.routeDestinationInput;
    
    state.routeOrigin = originSelect.value;
    state.routeDestination = destSelect.value;
    
    if (DOM.routeOriginLabel) {
      DOM.routeOriginLabel.textContent = originSelect.options[originSelect.selectedIndex].text.split(" (")[0];
    }
    if (DOM.routeDestinationLabel) {
      DOM.routeDestinationLabel.textContent = destSelect.options[destSelect.selectedIndex].text.split(" (")[0];
    }
    
    try {
      // Calls the non-logging simulation API to calculate distance and pin coordinates
      const route = await apiRequest("/api/route/plan", {
        method: "POST",
        body: JSON.stringify({
          user_id: CURRENT_USER_ID,
          origin: state.routeOrigin,
          destination: state.routeDestination,
          chosen_mode: state.routeMode,
          baseline_mode: "car"
        })
      });
      
      state.routeDistance = route.distance_km;
      state.routeStartCoords = route.start_coords;
      state.routeEndCoords = route.end_coords;
      
      updateRoutePlanner();
    } catch (e) {
      console.error("Auto-routing simulation update failed:", e);
    }
  };

  if (DOM.routeOriginInput) DOM.routeOriginInput.addEventListener("change", updateRouteEndpoints);
  if (DOM.routeDestinationInput) DOM.routeDestinationInput.addEventListener("change", updateRouteEndpoints);

  // Set default route calculation on first load
  setTimeout(() => {
    updateRouteEndpoints();
  }, 500);

  // Confirm Trip Button Click Action
  DOM.btnConfirmTrip.addEventListener("click", async () => {
    const factor = ROUTE_FACTORS[state.routeMode];
    let savings = state.routeDistance * factor;
    
    DOM.btnConfirmTrip.classList.add("success-ripple-active");
    setTimeout(() => {
      DOM.btnConfirmTrip.classList.remove("success-ripple-active");
    }, 800);

    DOM.btnConfirmTrip.disabled = true;

    try {
      const route = await logRoute(CURRENT_USER_ID, state.routeMode, state.routeDistance);
      savings = route.co2_saved_kg;
      
      state.routeDistance = route.distance_km;
      state.routeStartCoords = route.start_coords;
      state.routeEndCoords = route.end_coords;
      
      hideStaticOverlays();
      updateRoutePlanner();
      
      await syncLeaderboardFromBackend();
      await refreshLiveAssistant();
      showToast(`Trip logged! Saved ${savings.toFixed(1)}kg CO2 today. 🌲`);
    } catch (error) {
      console.error("Error logging route:", error);

      state.user.co2SavedAllTime += savings;
      state.user.co2SavedMonth += savings;
      state.leaderboard.forEach(entry => {
        if (entry.isUser) {
          entry.allTime = state.user.co2SavedAllTime;
          entry.month = state.user.co2SavedMonth;
        }
      });

      const increment = Math.round(savings * 1.5);
      state.user.leagueProgress = Math.min(100, state.user.leagueProgress + increment);
      updateEcoArenaView();
      updateProfileStats();
      showToast(`Trip saved locally. Backend unavailable: ${error.message}`);
    } finally {
      DOM.btnConfirmTrip.disabled = false;
    }
    
    const rect = DOM.btnConfirmTrip.getBoundingClientRect();
    triggerCanvasWave(rect.left + rect.width/2, rect.top + rect.height/2, "#4edea3", 350);
  });
}

// --------------------------------------------------------------------------
// 7. Eco Arena View Logic (Leaderboard + Search + Tabs)
// --------------------------------------------------------------------------
function renderLeaderboard() {
  const searchKey = state.searchQuery.toLowerCase().trim();
  const activeTab = state.leaderboardTab;
  
  const sorted = [...state.leaderboard].sort((a, b) => {
    return activeTab === "alltime" ? b.allTime - a.allTime : b.month - a.month;
  });

  DOM.leaderboardBody.innerHTML = "";
  
  let rank = 1;
  sorted.forEach((entry, index) => {
    if (entry.name.toLowerCase().includes(searchKey)) {
      const isUser = entry.isUser;
      const displayRank = index + 1;
      
      if (isUser) {
        state.user.rank = displayRank;
      }

      let badgeHtml = `<span class="badge-dash">-</span>`;
      if (entry.badge === "⭐") {
        badgeHtml = `<span class="badge-icon gold-star" title="Guardian Star">⭐</span>`;
      } else if (entry.badge === "🛡️") {
        badgeHtml = `<span class="badge-icon shield-badge" title="Warrior Shield">🛡️</span>`;
      }

      let rankClass = "general";
      if (displayRank === 1) rankClass = "gold";
      else if (displayRank === 2) rankClass = "silver";
      else if (displayRank === 3) rankClass = "bronze";
      
      if (isUser && displayRank > 3) {
        rankClass = "general highlight";
      }

      const score = activeTab === "alltime" ? entry.allTime : entry.month;

      const tr = document.createElement("tr");
      if (isUser) {
        tr.className = "leaderboard-highlight-row";
      }
      
      tr.innerHTML = `
        <td>
          <span class="rank-badge ${rankClass}">${displayRank}</span>
        </td>
        <td>
          <div class="table-user">
            <div class="user-avatar">
              <svg width="32" height="32" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="48" fill="${entry.avatarColor}" stroke="#adc6ff" stroke-width="2"/>
                <circle cx="50" cy="38" r="16" fill="${isUser ? '#0f172a' : '#1e293b'}" />
                <path d="M22 75C22 62 33 58 50 58C67 58 78 62 78 75C78 82 72 84 50 84C28 84 22 82 22 75Z" fill="${isUser ? '#0f172a' : '#10b981'}" />
              </svg>
            </div>
            <div class="user-details">
              <span class="user-name ${isUser ? 'font-bold' : ''}">${escapeHtml(entry.name)} ${isUser ? '(You)' : ''}</span>
              <span class="user-location">${escapeHtml(entry.location)}</span>
            </div>
          </div>
        </td>
        <td class="text-center">
          <span class="tier-badge ${entry.class}">${entry.tier}</span>
        </td>
        <td class="text-right label-mono highlight-green font-bold">${score.toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1})} kg</td>
        <td class="text-center">
          ${badgeHtml}
        </td>
      `;
      
      DOM.leaderboardBody.appendChild(tr);
    }
  });

  DOM.leaderboardAlexCo2.textContent = `${state.user.co2SavedAllTime.toFixed(1)} kg`;
}

function updateEcoArenaView() {
  const fillPct = state.user.leagueProgress;
  DOM.leagueProgressFill.style.width = `${fillPct}%`;
  DOM.leagueProgressPct.textContent = `${fillPct}%`;
  
  DOM.familyAlexFill.style.width = `${(12.4 + (fillPct - 85)*0.1).toFixed(1)}%`;
  DOM.familyAlexVal.textContent = `${(12.4 + (fillPct - 85)*0.1).toFixed(1)}% Reduction`;
  
  renderLeaderboard();
}

function setupEcoArenaListeners() {
  DOM.leaderboardSearch.addEventListener("input", (e) => {
    state.searchQuery = e.target.value;
    renderLeaderboard();
  });

  DOM.btnLeaderboardAllTime.addEventListener("click", () => {
    DOM.btnLeaderboardAllTime.classList.add("active");
    DOM.btnLeaderboardMonth.classList.remove("active");
    state.leaderboardTab = "alltime";
    renderLeaderboard();
  });

  DOM.btnLeaderboardMonth.addEventListener("click", () => {
    DOM.btnLeaderboardMonth.classList.add("active");
    DOM.btnLeaderboardAllTime.classList.remove("active");
    state.leaderboardTab = "month";
    renderLeaderboard();
  });
}

// --------------------------------------------------------------------------
// 8. Custom Impact Dialog Modal
// --------------------------------------------------------------------------
function setupModal() {
  DOM.btnLogImpactSidebar.addEventListener("click", () => {
    DOM.logImpactModal.showModal();
    triggerCanvasWave(window.innerWidth / 2, window.innerHeight / 2, "#4edea3", 200);
  });

  const closeModal = () => {
    DOM.logImpactModal.close();
  };

  DOM.btnCloseModal.addEventListener("click", closeModal);
  DOM.btnCancelLog.addEventListener("click", closeModal);

  DOM.logImpactModal.addEventListener("click", (e) => {
    const dialogRect = DOM.logImpactModal.getBoundingClientRect();
    if (
      e.clientX < dialogRect.left ||
      e.clientX > dialogRect.right ||
      e.clientY < dialogRect.top ||
      e.clientY > dialogRect.bottom
    ) {
      closeModal();
    }
  });

  DOM.btnConfirmLog.addEventListener("click", async () => {
    const select = DOM.customImpactSelect;
    const option = select.options[select.selectedIndex];
    let co2Saved = parseFloat(option.getAttribute("data-co2"));
    const actionKey = option.value;
    const label = option.text.split(" (+")[0];

    DOM.btnConfirmLog.disabled = true;

    try {
      const result = await logCustomImpact(CURRENT_USER_ID, actionKey, label);
      co2Saved = result.co2_saved_kg;
      await syncLeaderboardFromBackend();
      await refreshLiveAssistant();
      closeModal();
      showToast(`Logged: "${label}"! Saved ${co2Saved}kg CO2 🌿`);
    } catch (error) {
      console.error("Error logging custom impact:", error);

      state.user.co2SavedAllTime += co2Saved;
      state.user.co2SavedMonth += co2Saved;
      state.leaderboard.forEach(entry => {
        if (entry.isUser) {
          entry.allTime = state.user.co2SavedAllTime;
          entry.month = state.user.co2SavedMonth;
        }
      });

      const increment = Math.round(co2Saved * 1.5);
      state.user.leagueProgress = Math.min(100, state.user.leagueProgress + increment);
      updateEcoArenaView();
      updateProfileStats();
      closeModal();
      showToast(`Logged locally. Backend unavailable: ${error.message}`);
    } finally {
      DOM.btnConfirmLog.disabled = false;
    }
    
    triggerCanvasWave(window.innerWidth / 2, window.innerHeight / 2, "#10b981", 300);
  });
}

// --------------------------------------------------------------------------
// 9. Toast System
// --------------------------------------------------------------------------
// Toast notifications (safe rendering)
// --------------------------------------------------------------------------
function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";

  const svg = document.createElement("svg");
  svg.setAttribute("width", "18");
  svg.setAttribute("height", "18");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2.5");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.style.color = "var(--primary)";
  svg.innerHTML = `<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>`;

  const span = document.createElement("span");
  span.className = "toast-message";
  span.textContent = message;

  toast.appendChild(svg);
  toast.appendChild(span);
  DOM.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("show");
  }, 50);

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}

// --------------------------------------------------------------------------
// 10. Sync Profile view values
// --------------------------------------------------------------------------
function updateProfileStats() {
  if (DOM.profileStatCo2 && DOM.profileStatTrees) {
    DOM.profileStatCo2.textContent = `${state.user.co2SavedAllTime.toFixed(1)} kg`;
    const equivTrees = state.user.co2SavedAllTime / 20;
    DOM.profileStatTrees.textContent = equivTrees.toFixed(1);
  }
}

async function hydrateFromBackend() {
  try {
    await syncLeaderboardFromBackend();
  } catch (error) {
    console.error("Error loading leaderboard:", error);
    showToast(`Using demo leaderboard. Backend unavailable: ${error.message}`);
  }

  try {
    const insight = await fetchAIPersonalInsights(CURRENT_USER_ID);
    const insightElement = document.getElementById("live-insight-text");
    if (insight && insightElement) {
      insightElement.textContent = insight;
    }
  } catch (error) {
    console.error("Error loading AI insight:", error);
  }
}

// --------------------------------------------------------------------------
// 11. Initialization
// --------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initDOM();
  setupRouter();
  setupCanvasMap();
  setupActivityListeners();
  setupRoutePlanner();
  setupEcoArenaListeners();
  setupModal();
  setupKeyboardNavigation();

  // Add ARIA labels to range slider
  if (DOM.routeDistanceSlider) {
    DOM.routeDistanceSlider.setAttribute('aria-label', 'Route distance in kilometers');
    DOM.routeDistanceSlider.setAttribute('aria-valuemin', '1');
    DOM.routeDistanceSlider.setAttribute('aria-valuemax', '50');
    DOM.routeDistanceSlider.setAttribute('role', 'slider');
  }

  // Enhance modal accessibility
  enhanceModalAccessibility(DOM.logImpactModal);

  // Add ARIA labels to key buttons
  enhanceButtonAccessibility(DOM.btnConfirmLog, 'Confirm log impact');
  enhanceButtonAccessibility(DOM.btnCancelLog, 'Cancel log impact');
  enhanceButtonAccessibility(DOM.btnConfirmTrip, 'Confirm trip');

  calculateDailySummary();
  updateRoutePlanner();
  updateEcoArenaView();
  updateProfileStats();
  hydrateFromBackend();
  
  const style = document.createElement("style");
  style.innerHTML = `
    .route-visual-overlay, 
    .static-route, 
    .map-overlay-line, 
    .map-marker-start, 
    .map-marker-end, 
    .route-overlay,
    .slider-track-glow,
    [class*="route-line"], 
    [class*="map-marker"], 
    [class*="static-line"], 
    [class*="overlay-line"] {
      display: none !important;
    }
  `;
  document.head.appendChild(style);

  setTimeout(() => {
    showToast("Carbon Guardian system online. Optimal efficiency active. 🛡️");
  }, 1000);
});