// PricePulse Web App - UI controller. API payloads and calculations stay server-owned.
const API_BASE_URL = '/api/v1';

const searchForm = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const clearBtn = document.getElementById('clearBtn');
const searchSpinner = document.getElementById('searchSpinner');
const resultsContainer = document.getElementById('resultsContainer');
const loadingState = document.getElementById('loadingState');
const introState = document.getElementById('introState');
const emptyState = document.getElementById('emptyState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');
const queryLabel = document.getElementById('queryLabel');
const matchCountBadge = document.getElementById('matchCountBadge');
const exactMatchesContainer = document.getElementById('exactMatchesContainer');
const sortSelect = document.getElementById('sortSelect');
const unitPriceSection = document.getElementById('unitPriceSection');
const unitPriceContainer = document.getElementById('unitPriceContainer');
const availabilitySection = document.getElementById('availabilitySection');
const availabilityContainer = document.getElementById('availabilityContainer');
const exactMatchesMoreWrapper = document.getElementById('exactMatchesMoreWrapper');
const exactMatchesMoreBtn = document.getElementById('exactMatchesMoreBtn');
const singleStoreCountBadge = document.getElementById('singleStoreCountBadge');
const availabilityMoreWrapper = document.getElementById('availabilityMoreWrapper');
const availabilityMoreBtn = document.getElementById('availabilityMoreBtn');

const heroTitle = document.getElementById('heroTitle');

let currentResults = null;
let lastQuery = '';
let isExactExpanded = false;
let isAvailabilityExpanded = false;

// Rotating search input placeholder examples
const exampleQueries = [
    "Amul Gold Milk",
    "Chocolates",
    "Aashirvaad Atta",
    "Maggi Noodles",
    "Coca-Cola",
    "Surf Excel"
];
let placeholderIndex = 0;
let placeholderInterval = null;

// Rotating hero headline variations
const heroHeadlines = [
    { line1: "Compare prices.", line2: "Buy smarter." },
    { line1: "Find the best deal.", line2: "Spend less." },
    { line1: "Shop smarter.", line2: "Save more." },
    { line1: "Check the price.", line2: "Before you buy." }
];
let headlineIndex = 0;
let headlineInterval = null;

function buildHeadlineHTML(line1, line2) {
    const line1Words = line1.split(' ').map(w => `<span class="word-wrapper"><span class="hero-word">${escapeHtml(w)}</span></span>`).join(' ');
    const line2Words = line2.split(' ').map(w => `<span class="word-wrapper"><span class="hero-word">${escapeHtml(w)}</span></span>`).join(' ');
    return `<span class="hero-line">${line1Words}</span><span class="hero-line accent-line">${line2Words}</span>`;
}

function startHeadlineRotation() {
    if (!heroTitle) return;

    if (headlineInterval) clearInterval(headlineInterval);
    headlineInterval = setInterval(() => {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        headlineIndex = (headlineIndex + 1) % heroHeadlines.length;
        const nextItem = heroHeadlines[headlineIndex];

        if (prefersReducedMotion) {
            heroTitle.innerHTML = buildHeadlineHTML(nextItem.line1, nextItem.line2);
            return;
        }

        const currentWords = Array.from(heroTitle.querySelectorAll('.hero-word'));

        // 1. Stagger exit current words upward (75ms stagger)
        currentWords.forEach((word, index) => {
            setTimeout(() => {
                word.classList.add('word-exit');
            }, index * 75);
        });

        const exitDuration = (currentWords.length * 75) + 400;

        setTimeout(() => {
            // 2. Insert new headline HTML with words initialized at enter position below
            heroTitle.innerHTML = buildHeadlineHTML(nextItem.line1, nextItem.line2);
            const newWords = Array.from(heroTitle.querySelectorAll('.hero-word'));
            
            newWords.forEach(word => word.classList.add('word-enter-start'));
            void heroTitle.offsetWidth; // Force reflow

            // 3. Stagger enter new words rising up (75ms stagger)
            newWords.forEach((word, index) => {
                setTimeout(() => {
                    word.classList.remove('word-enter-start');
                }, index * 75);
            });
        }, exitDuration);

    }, 5200);
}

function startPlaceholderRotation() {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    if (placeholderInterval) clearInterval(placeholderInterval);
    placeholderInterval = setInterval(() => {
        if (!searchInput.value && document.activeElement !== searchInput) {
            placeholderIndex = (placeholderIndex + 1) % exampleQueries.length;
            searchInput.placeholder = `Search for a product or brand (e.g. ${exampleQueries[placeholderIndex]})`;
        }
    }, 3200);
}

function stopPlaceholderRotation() {
    if (placeholderInterval) {
        clearInterval(placeholderInterval);
        placeholderInterval = null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    searchForm.addEventListener('submit', event => {
        event.preventDefault();
        const query = searchInput.value.trim();
        if (query) performSearch(query);
    });

    searchInput.addEventListener('input', () => {
        clearBtn.classList.toggle('hidden', !searchInput.value);
        if (searchInput.value) stopPlaceholderRotation();
    });

    searchInput.addEventListener('focus', () => {
        stopPlaceholderRotation();
    });

    searchInput.addEventListener('blur', () => {
        if (!searchInput.value) {
            startPlaceholderRotation();
        }
    });

    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.classList.add('hidden');
        searchInput.focus();
    });

    document.querySelectorAll('.tag-btn').forEach(button => button.addEventListener('click', () => {
        searchInput.value = button.dataset.query;
        clearBtn.classList.remove('hidden');
        performSearch(button.dataset.query);
    }));

    sortSelect.addEventListener('change', () => currentResults && renderResults(currentResults));
    retryBtn.addEventListener('click', () => lastQuery && performSearch(lastQuery));

    exactMatchesMoreBtn.addEventListener('click', () => {
        isExactExpanded = !isExactExpanded;
        if (currentResults) renderResults(currentResults);
    });

    availabilityMoreBtn.addEventListener('click', () => {
        isAvailabilityExpanded = !isAvailabilityExpanded;
        if (currentResults) renderResults(currentResults);
    });

    checkApiHealth();
    startPlaceholderRotation();
    startHeadlineRotation();
});

async function checkApiHealth() {
    try {
        await fetch('http://127.0.0.1:8000/health');
    } catch {
        // Silently preserve backend API health check without UI indicator
    }
}

async function performSearch(query) {
    lastQuery = query;
    isExactExpanded = false;
    isAvailabilityExpanded = false;
    showLoading();
    try {
        const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error(`The server returned ${response.status}.`);
        const data = await response.json();
        currentResults = data;
        hideLoading();
        if (!hasSearchContent(data)) showEmpty(query);
        else renderResults(data);
    } catch (error) {
        hideLoading();
        showError(error.message);
    }
}

function hasSearchContent(data) {
    const hasRawProducts = Object.values(data.all_raw_matches || {}).some(products => products.length > 0);
    return (data.exact_matches || []).length > 0 || (data.unit_price_analysis?.items || []).length > 0 || hasRawProducts;
}

function showLoading() {
    [resultsContainer, introState, emptyState, errorState].forEach(element => element.classList.add('hidden'));
    loadingState.classList.remove('hidden');
    searchSpinner.classList.remove('hidden');
    searchBtn.disabled = true;
}

function hideLoading() {
    loadingState.classList.add('hidden');
    searchSpinner.classList.add('hidden');
    searchBtn.disabled = false;
}

function showEmpty(query) {
    emptyQuery.textContent = query;
    emptyState.classList.remove('hidden');
    introState.classList.add('hidden');
    resultsContainer.classList.add('hidden');
}

function showError() {
    errorMessage.textContent = 'Unable to compare prices right now. Please try again.';
    errorState.classList.remove('hidden');
    introState.classList.add('hidden');
    resultsContainer.classList.add('hidden');
}

function renderResults(data) {
    queryLabel.textContent = data.query || lastQuery;
    resultsContainer.classList.remove('hidden');
    introState.classList.add('hidden');

    const exactMatches = data.exact_matches || [];
    matchCountBadge.textContent = `${exactMatches.length} exact size ${exactMatches.length === 1 ? 'group' : 'groups'}`;

    const sortedExact = sortExactMatches(exactMatches, sortSelect.value);

    // Limit initial display to 6 exact matches
    const visibleExact = isExactExpanded ? sortedExact : sortedExact.slice(0, 6);
    exactMatchesContainer.innerHTML = visibleExact.length > 0
        ? visibleExact.map(renderExactMatchCard).join('')
        : '<p class="subtle-note">No identical sizes across multiple stores for this query.</p>';

    if (sortedExact.length > 6) {
        exactMatchesMoreWrapper.classList.remove('hidden');
        exactMatchesMoreBtn.textContent = isExactExpanded ? 'Show less' : `Show more comparisons (${sortedExact.length - 6} more)`;
    } else {
        exactMatchesMoreWrapper.classList.add('hidden');
    }

    const unitItems = data.unit_price_analysis?.items || [];
    if (unitItems.length > 0) {
        unitPriceSection.classList.remove('hidden');
        unitPriceContainer.innerHTML = unitItems.map(renderUnitPriceCard).join('');
    } else {
        unitPriceSection.classList.add('hidden');
    }

    renderSingleStoreAvailability(data.all_raw_matches || {}, exactMatches);
}

function sortExactMatches(matches, criterion) {
    const list = [...matches];

    // Priority rank: Multi-platform comparisons first (>=2 unique platforms available)
    list.sort((a, b) => {
        const uniquePlatsA = new Set((a.products || []).map(p => (p.platform || '').toLowerCase())).size;
        const uniquePlatsB = new Set((b.products || []).map(p => (p.platform || '').toLowerCase())).size;
        const isMultiA = uniquePlatsA >= 2 ? 1 : 0;
        const isMultiB = uniquePlatsB >= 2 ? 1 : 0;

        if (isMultiA !== isMultiB) return isMultiB - isMultiA;

        if (criterion === 'cheapest') {
            const minA = Math.min(...(a.products || []).map(p => p.product?.price || 0));
            const minB = Math.min(...(b.products || []).map(p => p.product?.price || 0));
            return minA - minB;
        } else if (criterion === 'savings') {
            return (b.savings || 0) - (a.savings || 0);
        } else if (criterion === 'size') {
            return (a.amount || 0) - (b.amount || 0);
        }
        return 0;
    });

    return list;
}

function renderExactMatchCard(group) {
    const products = group.products || [];
    const bestPlatform = (group.cheapest_platform || '').toLowerCase();
    
    // Representative product title
    const repProduct = products[0]?.product || {};
    const titleName = repProduct.name || 'Product';
    
    // Platform map for Blinkit, Zepto, Instamart
    const allPlatforms = ['Blinkit', 'Zepto', 'Instamart'];
    const productByPlatform = {};
    products.forEach(p => {
        if (p.platform) productByPlatform[p.platform.toLowerCase()] = p.product;
    });

    return `
        <article class="size-group-card">
            <div class="group-header">
                <div>
                    <span class="comparison-label">EXACT SIZE MATCH</span>
                    <h4 class="group-title">
                        ${escapeHtml(titleName)}
                        <span class="size-pill">${escapeHtml(group.size_label || '')}</span>
                    </h4>
                </div>
                ${group.savings > 0 ? `
                    <div class="savings-badge">
                        Save &#8377;${group.savings}
                    </div>
                ` : group.is_equal_price ? `
                    <div class="savings-badge neutral">
                        Same price
                    </div>
                ` : ''}
            </div>

            <div class="platform-cards-row">
                ${allPlatforms.map(platformName => {
                    const pKey = platformName.toLowerCase();
                    const prod = productByPlatform[pKey];
                    const isCheapest = pKey === bestPlatform && products.length > 1;

                    if (!prod) {
                        return `
                            <div class="product-platform-card unavailable">
                                <span class="platform-name-tag ${pKey}">${escapeHtml(platformName)}</span>
                                <div class="product-details">
                                    <p class="not-available-text">Not available</p>
                                </div>
                            </div>
                        `;
                    }

                    return `
                        <div class="product-platform-card ${isCheapest ? 'cheapest-winner' : ''}">
                            <div class="card-top-row">
                                <span class="platform-name-tag ${pKey}">${escapeHtml(platformName)}</span>
                                ${isCheapest ? '<span class="winner-ribbon">BEST PRICE</span>' : ''}
                            </div>
                            <div class="product-details">
                                <p class="prod-title">${escapeHtml(prod.name || '')}</p>
                                ${prod.variant ? `<span class="prod-variant">${escapeHtml(prod.variant)}</span>` : ''}
                            </div>
                            <div class="price-row">
                                <span class="curr-price">&#8377;${prod.price || 0}</span>
                                ${prod.mrp && prod.mrp > prod.price ? `<span class="mrp-price">&#8377;${prod.mrp}</span>` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </article>
    `;
}

function renderUnitPriceCard(item) {
    const prod = item.product || {};
    const pKey = (item.platform || '').toLowerCase();
    return `
        <article class="unit-card best-unit-winner">
            <div class="card-top">
                <span class="platform-name-tag ${pKey}">${escapeHtml(formatPlatformName(item.platform))}</span>
                <span class="winner-ribbon">BEST VALUE</span>
            </div>
            <p class="prod-title">${escapeHtml(prod.name || 'Item')}</p>
            <div class="unit-val">&#8377;${item.unit_price} <span class="unit-label">/ ${escapeHtml(item.unit_label || 'unit')}</span></div>
        </article>
    `;
}

function renderSingleStoreAvailability(rawMatches, exactMatches) {
    const matchedNames = new Set();
    exactMatches.forEach(group => {
        (group.products || []).forEach(match => {
            if (match.product?.name) matchedNames.add(match.product.name);
        });
    });

    const singleStoreItems = [];
    Object.entries(rawMatches).forEach(([platform, products]) => {
        (products || []).forEach(product => {
            if (!matchedNames.has(product.name)) {
                singleStoreItems.push({ ...product, platform });
            }
        });
    });

    if (singleStoreItems.length === 0) {
        availabilitySection.classList.add('hidden');
        return;
    }

    singleStoreCountBadge.textContent = `${singleStoreItems.length} products available`;
    availabilitySection.classList.remove('hidden');

    const visibleItems = isAvailabilityExpanded ? singleStoreItems : singleStoreItems.slice(0, 8);
    availabilityContainer.innerHTML = visibleItems.map(item => `
        <article class="availability-card">
            <div>
                <span class="platform-name-tag ${(item.platform || '').toLowerCase()}">${escapeHtml(formatPlatformName(item.platform))}</span>
                <h4 class="prod-title" style="margin-top: 8px;">${escapeHtml(item.name || '')}</h4>
            </div>
            <div class="availability-meta">
                <span class="availability-price">&#8377;${item.price || 0}</span>
                <span class="availability-size">${escapeHtml(item.variant || '')}</span>
            </div>
        </article>
    `).join('');

    if (singleStoreItems.length > 8) {
        availabilityMoreWrapper.classList.remove('hidden');
        availabilityMoreBtn.textContent = isAvailabilityExpanded ? 'Show less' : `Show more products (${singleStoreItems.length - 8} more)`;
    } else {
        availabilityMoreWrapper.classList.add('hidden');
    }
}

function formatPlatformName(platform) {
    if (!platform) return '';
    const lower = platform.toLowerCase();
    if (lower === 'blinkit') return 'Blinkit';
    if (lower === 'zepto') return 'Zepto';
    if (lower === 'instamart') return 'Instamart';
    return platform;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
