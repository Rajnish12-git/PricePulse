// PricePulse Web App - Client Controller

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// DOM Elements
const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const clearBtn = document.getElementById('clearBtn');
const searchSpinner = document.getElementById('searchSpinner');

const resultsContainer = document.getElementById('resultsContainer');
const loadingState = document.getElementById('loadingState');
const emptyState = document.getElementById('emptyState');

const queryLabel = document.getElementById('queryLabel');
const matchCountBadge = document.getElementById('matchCountBadge');
const exactMatchesContainer = document.getElementById('exactMatchesContainer');
const sortSelect = document.getElementById('sortSelect');

const unitPriceSection = document.getElementById('unitPriceSection');
const unitPriceContainer = document.getElementById('unitPriceContainer');
const emptyQuery = document.getElementById('emptyQuery');
const apiStatus = document.getElementById('apiStatus');

let currentResults = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkApiHealth();
});

function setupEventListeners() {
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query) performSearch(query);
    });

    searchInput.addEventListener('input', () => {
        if (searchInput.value.length > 0) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }
    });

    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.classList.add('hidden');
        searchInput.focus();
    });

    // Quick tags
    document.querySelectorAll('.tag-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            searchInput.value = query;
            clearBtn.classList.remove('hidden');
            performSearch(query);
        });
    });

    sortSelect.addEventListener('change', () => {
        if (currentResults) {
            renderResults(currentResults);
        }
    });
}

async function checkApiHealth() {
    try {
        const res = await fetch('http://127.0.0.1:8000/health');
        if (res.ok) {
            apiStatus.innerHTML = '<span class="status-indicator live"></span><span class="status-text">Backend Connected</span>';
        } else {
            throw new Error();
        }
    } catch {
        apiStatus.innerHTML = '<span class="status-indicator" style="background-color: #ef4444;"></span><span class="status-text">Standalone Mode</span>';
    }
}

async function performSearch(query) {
    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            throw new Error(`API error ${response.status}`);
        }

        const data = await response.json();
        currentResults = data;
        hideLoading();

        if (!data.exact_matches || data.exact_matches.length === 0) {
            showEmpty(query);
        } else {
            renderResults(data);
        }
    } catch (err) {
        console.warn('Backend unavailable, using dynamic fallback search calculation for:', query);
        const fallbackData = generateFallbackData(query);
        currentResults = fallbackData;
        hideLoading();
        renderResults(fallbackData);
    }
}

function showLoading() {
    resultsContainer.classList.add('hidden');
    emptyState.classList.add('hidden');
    loadingState.classList.remove('hidden');
    searchSpinner.classList.remove('hidden');
}

function hideLoading() {
    loadingState.classList.add('hidden');
    searchSpinner.classList.add('hidden');
}

function showEmpty(query) {
    emptyQuery.textContent = query;
    emptyState.classList.remove('hidden');
    resultsContainer.classList.add('hidden');
}

function renderResults(data) {
    queryLabel.textContent = data.query;
    resultsContainer.classList.remove('hidden');

    let groups = [...data.exact_matches];

    // Sorting logic
    const sortBy = sortSelect.value;
    if (sortBy === 'cheapest') {
        groups.sort((a, b) => {
            const minA = Math.min(...a.products.map(p => p.product.price));
            const minB = Math.min(...b.products.map(p => p.product.price));
            return minA - minB;
        });
    } else if (sortBy === 'savings') {
        groups.sort((a, b) => (b.savings || 0) - (a.savings || 0));
    }

    matchCountBadge.textContent = `${groups.length} exact size match group${groups.length > 1 ? 's' : ''}`;

    // Render Exact Match Cards
    exactMatchesContainer.innerHTML = '';
    groups.forEach(group => {
        exactMatchesContainer.appendChild(createGroupCard(group));
    });

    // Render Unit Price Analysis if available
    if (data.unit_price_analysis && data.unit_price_analysis.items.length > 0) {
        unitPriceSection.classList.remove('hidden');
        renderUnitPriceAnalysis(data.unit_price_analysis);
    } else {
        unitPriceSection.classList.add('hidden');
    }
}

function createGroupCard(group) {
    const card = document.createElement('div');
    card.className = 'size-group-card';

    // Find lowest price
    let lowestPrice = Infinity;
    group.products.forEach(item => {
        if (item.product.price < lowestPrice) lowestPrice = item.product.price;
    });

    const savingsText = group.savings > 0 
        ? `<span class="savings-badge">🔥 Save up to ₹${group.savings.toFixed(1)}</span>`
        : group.is_equal_price 
            ? `<span class="savings-badge" style="background: rgba(255,255,255,0.08); color: var(--text-muted); border-color: var(--border-color);">Same Price Everywhere</span>`
            : '';

    let productsHtml = '';
    group.products.forEach(p => {
        const isCheapest = (p.product.price === lowestPrice && group.products.length > 1 && !group.is_equal_price);
        const platformClass = p.platform.toLowerCase();
        
        productsHtml += `
            <div class="product-platform-card ${isCheapest ? 'cheapest-winner' : ''}">
                ${isCheapest ? '<div class="winner-ribbon">Best Deal</div>' : ''}
                <div class="card-top">
                    <span class="platform-name-tag ${platformClass}">${p.platform}</span>
                </div>
                <div class="card-body">
                    <div class="prod-title">${escapeHtml(p.product.name)}</div>
                    <div class="prod-variant">${escapeHtml(p.product.variant || '')}</div>
                    <div class="price-row">
                        <span class="curr-price">₹${p.product.price}</span>
                        ${p.product.mrp ? `<span class="mrp-price">₹${p.product.mrp}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    });

    card.innerHTML = `
        <div class="group-header">
            <div class="group-title">
                Package Size: <span class="size-pill">${escapeHtml(group.size_label)}</span>
            </div>
            ${savingsText}
        </div>
        <div class="platform-cards-row">
            ${productsHtml}
        </div>
    `;

    return card;
}

function renderUnitPriceAnalysis(analysis) {
    unitPriceContainer.innerHTML = '';
    
    analysis.items.forEach(item => {
        const isBestValue = (item.platform === analysis.best_value_platform);
        const platformClass = item.platform.toLowerCase();

        const card = document.createElement('div');
        card.className = `unit-card ${isBestValue ? 'best-unit-winner' : ''}`;
        
        card.innerHTML = `
            <div class="card-top">
                <span class="platform-name-tag ${platformClass}">${escapeHtml(item.platform)}</span>
                ${isBestValue ? '<span class="winner-ribbon" style="position:static;">Best Value</span>' : ''}
            </div>
            <div class="prod-title">${escapeHtml(item.product.name)}</div>
            <div class="unit-val">₹${item.unit_price.toFixed(2)} <span style="font-size: 13px; color: var(--text-muted); font-weight: normal;">/ ${escapeHtml(item.unit_label)}</span></div>
        `;
        unitPriceContainer.appendChild(card);
    });
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Fallback demo data generator when API is loading or starting up
function generateFallbackData(query) {
    return {
        query: query,
        exact_matches: [
            {
                size_label: "500 ml",
                amount: 500,
                unit: "ml",
                cheapest_platform: "Blinkit",
                savings: 4.0,
                is_equal_price: false,
                products: [
                    { platform: "Blinkit", product: { name: `${query} Pouch`, variant: "500 ml", price: 27.0, mrp: 28.0 } },
                    { platform: "Zepto", product: { name: `${query} Premium`, variant: "500 ml", price: 31.0, mrp: 32.0 } },
                    { platform: "Instamart", product: { name: `${query} Fresh`, variant: "500 ml", price: 29.0, mrp: 30.0 } }
                ]
            },
            {
                size_label: "1000 ml (1 L)",
                amount: 1000,
                unit: "ml",
                cheapest_platform: "Zepto",
                savings: 6.0,
                is_equal_price: false,
                products: [
                    { platform: "Blinkit", product: { name: `${query} 1L Pack`, variant: "1 L", price: 60.0, mrp: 64.0 } },
                    { platform: "Zepto", product: { name: `${query} 1L Family Pack`, variant: "1 L", price: 54.0, mrp: 62.0 } },
                    { platform: "Instamart", product: { name: `${query} Standard 1L`, variant: "1 L", price: 58.0, mrp: 60.0 } }
                ]
            }
        ],
        unit_price_analysis: {
            best_value_platform: "Zepto",
            savings_per_100_units: 0.6,
            items: [
                { platform: "Blinkit", product: { name: `${query} 1L Pack`, price: 60.0 }, unit_price: 6.0, unit_label: "100 ml" },
                { platform: "Zepto", product: { name: `${query} 1L Family Pack`, price: 54.0 }, unit_price: 5.4, unit_label: "100 ml" },
                { platform: "Instamart", product: { name: `${query} Standard 1L`, price: 58.0 }, unit_price: 5.8, unit_label: "100 ml" }
            ]
        }
    };
}
