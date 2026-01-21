// js/market.js
// Handles the market data display and order-entry table for Bloomberg-style terminal

import { byId } from "./ui.js";
import { ASSETS } from "./constants.js";

// Store previous prices for change detection
const previousPrices = {};
const priceHistory = {}; // For sparklines

// Initialize price history
ASSETS.forEach(asset => {
  priceHistory[asset] = [];
});

/**
 * Initializes the market data table with live prices and sparklines
 */
export function initMarketData() {
  const marketTbody = byId("market_rows");
  if (!marketTbody) return;

  marketTbody.innerHTML = "";

  ASSETS.forEach((asset) => {
    const tr = document.createElement("tr");
    tr.id = `market_row_${asset}`;

    tr.innerHTML = `
      <td><strong>${asset}</strong></td>
      <td id="mp_${asset}" class="price-cell">-</td>
      <td id="mchg_${asset}" class="price-change">-</td>
      <td id="mchgp_${asset}" class="price-change">-</td>
      <td><canvas id="spark_${asset}" class="sparkline" width="60" height="20"></canvas></td>
    `;

    marketTbody.appendChild(tr);
  });
}

/**
 * Initializes the order entry table:
 *  - builds one row per asset with BUY/SELL buttons
 *  - wires buttons to the provided onOrder callback
 *
 * @param {(order: {asset:string, qty:number, side:string}) => void} onOrder
 */
export function initMarket(onOrder) {
  const rowsTbody = byId("rows");
  if (!rowsTbody) return;

  rowsTbody.innerHTML = "";

  ASSETS.forEach((asset) => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td><strong>${asset}</strong></td>
      <td id="p_${asset}" class="price-cell">-</td>
      <td>
        <input
          id="q_${asset}"
          type="number"
          min="1"
          value="10"
        />
      </td>
      <td>
        <button id="btn_buy_${asset}" class="btn-buy" title="Buy ${asset}">BUY</button>
        <button id="btn_sell_${asset}" class="btn-sell" title="Sell ${asset}">SELL</button>
      </td>
    `;

    rowsTbody.appendChild(tr);

    // Wire BUY button
    const btnBuy = byId(`btn_buy_${asset}`);
    const qtyI = byId(`q_${asset}`);

    if (btnBuy && qtyI && typeof onOrder === "function") {
      btnBuy.onclick = () => {
        const qty = parseInt(qtyI.value, 10) || 0;
        onOrder({ asset, qty, side: "BUY" });
      };
    }

    // Wire SELL button
    const btnSell = byId(`btn_sell_${asset}`);
    if (btnSell && qtyI && typeof onOrder === "function") {
      btnSell.onclick = () => {
        const qty = parseInt(qtyI.value, 10) || 0;
        onOrder({ asset, qty, side: "SELL" });
      };
    }
  });

  // Initialize market data table
  initMarketData();
}

/**
 * Updates live prices with flash animations and change indicators
 * Called on every TICK from the backend
 *
 * @param {Object<string, number>} priceMap - asset -> latest price
 */
export function updatePrices(priceMap) {
  if (!priceMap) return;

  ASSETS.forEach((asset) => {
    const newPrice = priceMap[asset];
    if (newPrice === undefined || newPrice === null) return;

    const prevPrice = previousPrices[asset];
    const priceValue = Number(newPrice);

    // Update order panel price
    const orderCell = byId(`p_${asset}`);
    if (orderCell) {
      orderCell.textContent = priceValue.toFixed(2);
    }

    // Update market data panel
    const marketCell = byId(`mp_${asset}`);
    const changeCell = byId(`mchg_${asset}`);
    const changePctCell = byId(`mchgp_${asset}`);
    const marketRow = byId(`market_row_${asset}`);

    if (marketCell) {
      marketCell.textContent = priceValue.toFixed(2);

      // Calculate change if we have previous price
      if (prevPrice !== undefined) {
        const change = priceValue - prevPrice;
        const changePct = (change / prevPrice) * 100;

        // Update change cells
        if (changeCell) {
          const changeStr = (change >= 0 ? '+' : '') + change.toFixed(2);
          changeCell.textContent = changeStr;
          changeCell.className = change > 0 ? 'price-change up' : change < 0 ? 'price-change down' : 'price-change';
        }

        if (changePctCell) {
          const pctStr = (changePct >= 0 ? '+' : '') + changePct.toFixed(2) + '%';
          changePctCell.textContent = pctStr;
          changePctCell.className = changePct > 0 ? 'price-change up' : changePct < 0 ? 'price-change down' : 'price-change';
        }

        // Trigger flash animation
        if (marketRow) {
          marketRow.classList.remove('flash-green', 'flash-red');
          
          if (change > 0) {
            void marketRow.offsetWidth; // Force reflow
            marketRow.classList.add('flash-green');
          } else if (change < 0) {
            void marketRow.offsetWidth; // Force reflow
            marketRow.classList.add('flash-red');
          }
        }
      } else {
        // First price, no change
        if (changeCell) changeCell.textContent = '-';
        if (changePctCell) changePctCell.textContent = '-';
      }
    }

    // Update sparkline history
    if (!priceHistory[asset]) priceHistory[asset] = [];
    priceHistory[asset].push(priceValue);
    
    // Keep only last 20 points for sparklines
    if (priceHistory[asset].length > 20) {
      priceHistory[asset].shift();
    }

    // Draw sparkline
    drawSparkline(asset);

    // Store current price for next comparison
    previousPrices[asset] = priceValue;
  });
}

/**
 * Draws a mini sparkline chart for an asset
 * 
 * @param {string} asset - The asset symbol
 */
function drawSparkline(asset) {
  const canvas = byId(`spark_${asset}`);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const data = priceHistory[asset] || [];
  
  if (data.length < 2) return;

  const width = canvas.width;
  const height = canvas.height;
  const padding = 2;

  // Clear canvas
  ctx.clearRect(0, 0, width, height);

  // Find min/max for scaling
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  // Draw line
  ctx.beginPath();
  ctx.strokeStyle = '#007aff';
  ctx.lineWidth = 1.5;

  data.forEach((price, i) => {
    const x = (i / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((price - min) / range) * (height - padding * 2);
    
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });

  ctx.stroke();

  // Determine if overall trend is up or down
  const firstPrice = data[0];
  const lastPrice = data[data.length - 1];
  
  if (lastPrice > firstPrice) {
    ctx.strokeStyle = '#00c853'; // Green for uptrend
  } else if (lastPrice < firstPrice) {
    ctx.strokeStyle = '#ff3b30'; // Red for downtrend
  }
  
  // Redraw with color
  ctx.beginPath();
  data.forEach((price, i) => {
    const x = (i / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((price - min) / range) * (height - padding * 2);
    
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}
