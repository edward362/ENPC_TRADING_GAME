// constants.js
// Global static configuration used across the entire frontend.

// --- Game default rules ---
export const DEFAULTS = {
  startingCapital: 10000,
  tickSeconds: 2,
  durationSec: 15 * 60,   // 15 minutes
};

// --- Tradable assets ---
export const ASSETS = [
  "OIL",
  "GOLD",
  "ELECTRONICS",
  "RICE",
  "PLUMBER"
];

// --- Chart configuration ---
export const MAX_POINTS = 300;

export const HISTORY = {
  OIL: [],
  GOLD: [],
  ELECTRONICS: [],
  RICE: [],
  PLUMBER: []
};

export const LABELS = [];   // Timestamps for the price chart
