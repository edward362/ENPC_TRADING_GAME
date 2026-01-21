// js/ticker.js
// Bloomberg-style scrolling news ticker with fake market headlines

import { byId } from "./ui.js";

// Market news headlines (fake but realistic)
const NEWS_HEADLINES = [
  "BREAKING: Oil prices surge 3.2% on OPEC production cuts",
  "GOLD reaches new 6-month high amid inflation concerns",
  "ELECTRONICS sector rallies on strong Q4 earnings",
  "RICE futures decline as harvest season approaches peak",
  "PLUMBER stocks steady despite industry headwinds",
  "Central bank signals potential rate adjustment next quarter",
  "Asian markets open higher following overnight gains",
  "Commodities trading volume hits record levels",
  "Tech sector shows resilience amid volatility",
  "Energy stocks outperform broader market indices",
  "Agricultural commodities see mixed performance",
  "Currency markets react to latest economic data",
  "Industrial metals show strength in morning trading",
  "Precious metals gain as safe-haven demand increases",
  "Market analysts predict continued volatility ahead",
  "Trading volumes exceed daily averages by 25%",
  "Futures market shows strong institutional interest",
  "Emerging markets attract renewed investor attention",
  "Sector rotation continues as traders rebalance portfolios",
  "Algorithmic trading accounts for 60% of daily volume"
];

let currentIndex = 0;
let tickerInterval = null;

/**
 * Initialize the news ticker with rotating headlines
 */
export function initTicker() {
  const tickerElement = byId("tickerText");
  if (!tickerElement) return;

  // Build initial ticker content
  updateTickerContent();

  // Rotate headlines every 8 seconds
  tickerInterval = setInterval(() => {
    updateTickerContent();
  }, 8000);
}

/**
 * Update ticker content with new headlines
 */
function updateTickerContent() {
  const tickerElement = byId("tickerText");
  if (!tickerElement) return;

  // Get 5 headlines starting from current index
  const headlines = [];
  for (let i = 0; i < 5; i++) {
    const idx = (currentIndex + i) % NEWS_HEADLINES.length;
    headlines.push(NEWS_HEADLINES[idx]);
  }

  // Build ticker HTML
  const tickerHTML = headlines.map(headline => {
    return `<span class="ticker-item">${headline}</span>`;
  }).join('');

  tickerElement.innerHTML = tickerHTML;

  // Move to next set of headlines
  currentIndex = (currentIndex + 1) % NEWS_HEADLINES.length;
}

/**
 * Add a custom headline to the ticker (for game events)
 * @param {string} headline - The headline to add
 */
export function addTickerHeadline(headline) {
  NEWS_HEADLINES.unshift(`ALERT: ${headline}`);
  
  // Keep the array from growing too large
  if (NEWS_HEADLINES.length > 30) {
    NEWS_HEADLINES.pop();
  }
  
  updateTickerContent();
}

/**
 * Stop the ticker
 */
export function stopTicker() {
  if (tickerInterval) {
    clearInterval(tickerInterval);
    tickerInterval = null;
  }
}
