// Global data storage
let allStats = [];
let allProducts = [];

// Helper to escape HTML characters and prevent XSS
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

// Utility to fetch data with cache busting
async function fetchData(url) {
    try {
        const response = await fetch(url + '?t=' + Date.now());
        if (!response.ok) return null;
        return await response.json();
    } catch (e) {
        console.warn("Fetch error: " + url, e);
        alert("Error cargando " + url + ": " + e.message + "\nAsegúrate de estar ejecutando el servidor desde la carpeta raíz del proyecto.");
        return null;
    }
}

async function initDashboard() {
    // Check for file:// protocol (CORS issues)
    if (window.location.protocol === 'file:') {
        console.error("CORS Error: The dashboard must be served via HTTP (e.g., http://localhost:8000) to load data.");
        const warning = document.createElement('div');
        warning.style = "position: fixed; top: 0; left: 0; width: 100%; background: #ef4444; color: white; text-align: center; padding: 15px; z-index: 9999; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.3);";
        warning.textContent = '⚠️ Error de Seguridad: Abre el dashboard usando ';
        const link = document.createElement('a');
        link.href = 'http://localhost:8000/dashboard/index.html';
        link.style.color = 'white';
        link.style.textDecoration = 'underline';
        link.textContent = 'http://localhost:8000/dashboard/index.html';
        warning.appendChild(link);
        document.body.prepend(warning);
        return;
    }

    // Set Current Date
    const now = new Date();
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    document.getElementById('currentTime').innerText = now.toLocaleDateString('en-US', options).toUpperCase();

    // 1. Fetch Data
    allStats = await fetchData('../data_activa/historico_stats.json') || [];
    const productsObj = await fetchData('../data_activa/estado_productos_dashboard.json') || {};
    allProducts = Object.values(productsObj);
    const allActivities = await fetchData('../data_activa/actividades.json') || [];

    if (allStats.length > 0) {
        const latest = allStats[allStats.length - 1];
        
        // HH Saved KPI
        document.getElementById('kpi-hh').innerText = Math.round(latest.hh_ahorradas);
        
        // HH Today & Velocity (New)
        if (document.getElementById('kpi-hh-today')) {
            document.getElementById('kpi-hh-today').innerText = latest.hh_ganadas_hoy || '0';
        }
        
        if (document.getElementById('kpi-velocity')) {
            const vel = latest.velocidad || 0;
            document.getElementById('kpi-velocity').innerText = vel > 0 ? vel + 'x' : '--';
            
            // Animación de la barra de velocidad
            const fill = document.getElementById('velocity-fill');
            if (fill) {
                // Mapeo: 1x = 10%, 10x = 100%
                const percentage = Math.min(100, Math.max(0, (vel / 10) * 100));
                setTimeout(() => { fill.style.width = percentage + '%'; }, 500);
            }
        }
        
        // Calculate Trend
        if (allStats.length > 1) {
            const prev = allStats[allStats.length - 2];
            const diff = prev.hh_ahorradas > 0 
                ? ((latest.hh_ahorradas - prev.hh_ahorradas) / prev.hh_ahorradas * 100).toFixed(1)
                : 0;
            const trendBadge = document.querySelector('.trend-badge span');
            if (trendBadge) trendBadge.innerText = (diff >= 0 ? '+' : '') + diff + '%';
        }

        // Overview Charts
        initBarChart(allStats);
        
        const stockHealth = latest.total_productos > 0 
            ? ((latest.total_productos - latest.agotados) / latest.total_productos * 100).toFixed(1)
            : 0;
        initGaugeChart(stockHealth);

        updateBotStatus(latest);
    }

    initActivities(allActivities);
    initNavigation();
    
    // Initial content render
    renderViewContent('view-overview');
}

function updateBotStatus(latest) {
    const statusText = document.getElementById('bot-status-info');
    if (latest.duracion_segundos) {
        const mins = Math.floor(latest.duracion_segundos / 60);
        const secs = Math.round(latest.duracion_segundos % 60);
        statusText.innerText = `Last run: ${mins}m ${secs}s`;
    } else {
        statusText.innerText = "Bot Ready";
    }
}

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item[id^="nav-"]');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const viewId = item.id.replace('nav-', 'view-');
            switchView(viewId, item);
        });
    });

    // Search input listener
    const searchInput = document.getElementById('productSearch');
    if (searchInput) {
        searchInput.addEventListener('input', () => renderProductsTable(searchInput.value));
    }

    // Programmatically attach hover and click listeners to activities card
    const activitiesCard = document.getElementById('activities-card');
    if (activitiesCard) {
        activitiesCard.addEventListener('click', () => {
            const navLogs = document.getElementById('nav-logs');
            if (navLogs) navLogs.click();
        });
        activitiesCard.addEventListener('mouseover', () => {
            activitiesCard.style.transform = 'scale(1.02)';
        });
        activitiesCard.addEventListener('mouseout', () => {
            activitiesCard.style.transform = 'scale(1)';
        });
    }
}

function switchView(viewId, navItem) {
    document.querySelectorAll('.view-section').forEach(view => view.classList.add('hidden'));
    document.getElementById(viewId).classList.remove('hidden');

    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    navItem.classList.add('active');

    renderViewContent(viewId);
}

function renderViewContent(viewId) {
    if (viewId === 'view-products') {
        renderProductsTable();
    } else if (viewId === 'view-analytics') {
        renderAnalyticsCharts();
    }
}

// --- PRODUCTS VIEW ---
function renderProductsTable(filter = '') {
    const tbody = document.getElementById('productsTableBody');
    if (!tbody) return;

    tbody.innerHTML = '';
    const searchTerm = filter.toLowerCase();

    const filtered = allProducts.filter(p => 
        p.sku.toLowerCase().includes(searchTerm) || 
        p.nombre.toLowerCase().includes(searchTerm)
    ).slice(0, 50); // Limit to 50 for performance

    filtered.forEach(p => {
        const row = document.createElement('tr');
        
        // SKU cell
        const tdSku = document.createElement('td');
        tdSku.style.fontWeight = "600";
        tdSku.style.color = "var(--accent-blue)";
        tdSku.textContent = p.sku;

        // Name cell
        const tdName = document.createElement('td');
        const truncatedName = p.nombre.length > 50 ? p.nombre.substring(0, 50) + '...' : p.nombre;
        tdName.textContent = truncatedName;

        // Price cell
        const tdPrice = document.createElement('td');
        const price = p.sale_price !== undefined ? p.sale_price : (p.precio_original || 0);
        tdPrice.textContent = `$${price}`;

        // Stock cell
        const tdStock = document.createElement('td');
        const stockSpan = document.createElement('span');
        stockSpan.style.color = p.stock > 0 ? '#10b981' : '#ef4444';
        stockSpan.textContent = p.stock;
        tdStock.appendChild(stockSpan);

        // Status badges cell
        const tdStatus = document.createElement('td');
        const badgeContainer = document.createElement('div');
        badgeContainer.className = 'status-badges';

        const createBadge = (isActive, iconClass, title) => {
            const badge = document.createElement('div');
            badge.className = `status-badge ${isActive}`;
            badge.title = title;
            const icon = document.createElement('i');
            icon.className = `fas ${iconClass}`;
            badge.appendChild(icon);
            return badge;
        };

        const wooBadge = createBadge(p.subido_a_woo ? 'active-woo' : '', 'fa-shopping-cart', 'WooCommerce');
        const iaBadge = createBadge(p.ia_mejorado ? 'active-ia' : '', 'fa-magic', 'IA Improved');
        const imgBadge = createBadge(p.tiene_imagen ? 'active-img' : '', 'fa-image', 'Has Image');

        badgeContainer.appendChild(wooBadge);
        badgeContainer.appendChild(iaBadge);
        badgeContainer.appendChild(imgBadge);
        tdStatus.appendChild(badgeContainer);

        row.appendChild(tdSku);
        row.appendChild(tdName);
        row.appendChild(tdPrice);
        row.appendChild(tdStock);
        row.appendChild(tdStatus);

        tbody.appendChild(row);
    });

    document.getElementById('pagination-info').innerText = `Mostrando ${filtered.length} de ${allProducts.length} productos`;
}

// --- ANALYTICS VIEW ---
function renderAnalyticsCharts() {
    const ctx = document.getElementById('analyticsLineChart').getContext('2d');
    if (!ctx) return;

    const labels = allStats.map(s => s.fecha);
    const iaData = allStats.map(s => s.total_productos > 0 ? (s.con_ia / s.total_productos * 100).toFixed(1) : 0);
    const wooData = allStats.map(s => s.total_productos > 0 ? (s.en_woo / s.total_productos * 100).toFixed(1) : 0);

    if (window.analyticsChart) window.analyticsChart.destroy();

    window.analyticsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '% Mejora IA',
                    data: iaData,
                    borderColor: '#9d50bb',
                    backgroundColor: 'rgba(157, 80, 187, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: '% WooCommerce',
                    data: wooData,
                    borderColor: '#00d2ff',
                    backgroundColor: 'rgba(0, 210, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: true,
                    labels: { color: '#8b949e' }
                }
            },
            scales: {
                y: { 
                    max: 100,
                    beginAtZero: true,
                    ticks: { color: '#8b949e' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                x: { 
                    ticks: { color: '#8b949e' },
                    grid: { display: false }
                }
            }
        }
    });

    // Summary Boxes
    const summary = document.getElementById('analytics-summary');
    const latest = allStats[allStats.length - 1];
    
    summary.innerHTML = '';
    const createStatBox = (title, value, color) => {
        const box = document.createElement('div');
        box.className = 'stat-box';
        const h4 = document.createElement('h4');
        h4.textContent = title;
        const valDiv = document.createElement('div');
        valDiv.className = 'val';
        if (color) valDiv.style.color = color;
        valDiv.textContent = value;
        box.appendChild(h4);
        box.appendChild(valDiv);
        return box;
    };
    summary.appendChild(createStatBox('Eficiencia IA', `${iaData[iaData.length-1]}%`, 'var(--accent-purple)'));
    summary.appendChild(createStatBox('Sincronización', `${wooData[wooData.length-1]}%`, 'var(--accent-blue)'));
    summary.appendChild(createStatBox('Catálogo', latest.total_productos));
}

// --- OVERVIEW HELPERS ---
function initBarChart(stats) {
    const ctx = document.getElementById('barChart').getContext('2d');
    const last7 = stats.slice(-7);
    const labels = last7.map(s => s.fecha.split('-').slice(1).join('/')); 
    const data = last7.map(s => s.nuevos_productos || 0);

    const gradient = ctx.createLinearGradient(0, 0, 0, 180);
    gradient.addColorStop(0, '#00d2ff');
    gradient.addColorStop(1, '#9d50bb');

    if (window.myBarChart) window.myBarChart.destroy();
    window.myBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{ backgroundColor: gradient, data: data, borderRadius: 8, barThickness: 15 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { display: false }, y: { display: false, beginAtZero: true } }
        }
    });
}

function initGaugeChart(value) {
    const circle = document.getElementById('gaugeCircle');
    const text = document.getElementById('kpi-gauge-value');
    circle.style.background = `conic-gradient(#00d2ff ${value}%, rgba(255,255,255,0.05) 0)`;
    text.innerText = value + '%';
}

function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return "Just now";
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} min ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hrs ago`;
    
    const days = Math.floor(hours / 24);
    return `${days} days ago`;
}

function initActivities(activities) {
    const list = document.getElementById('activitiesList');
    list.innerHTML = '';
    
    if (!activities || activities.length === 0) {
        const noActivities = document.createElement('div');
        noActivities.style.color = 'var(--text-muted)';
        noActivities.style.textAlign = 'center';
        noActivities.style.marginTop = '20px';
        noActivities.textContent = 'Sin actividades recientes.';
        list.appendChild(noActivities);
        return;
    }
    
    // Mostrar solo los últimos 6 eventos en la tarjeta principal
    activities.slice(0, 6).forEach(act => {
        renderActivity(list, act.icon || 'fa-info-circle', act.message, act.categoria || 'Sistema', timeAgo(act.timestamp));
    });

    // Llenar la tabla completa de la vista "Logs"
    const tbody = document.getElementById('fullLogsTableBody');
    if (tbody) {
        tbody.innerHTML = '';
        activities.forEach(act => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
            tr.style.transition = "background 0.2s";
            tr.onmouseover = function() { this.style.backgroundColor = "rgba(255,255,255,0.03)"; };
            tr.onmouseout = function() { this.style.backgroundColor = "transparent"; };

            const dateObj = new Date(act.timestamp);
            const timeStr = dateObj.toLocaleDateString() + ' ' + dateObj.toLocaleTimeString();
            
            const tdTime = document.createElement('td');
            tdTime.style.padding = "12px";
            tdTime.style.color = "var(--text-muted)";
            tdTime.style.fontSize = "0.85rem";
            tdTime.textContent = timeStr;

            const tdCategory = document.createElement('td');
            tdCategory.style.padding = "12px";
            tdCategory.style.fontWeight = "600";
            
            const catBadge = document.createElement('span');
            catBadge.className = "status-badge";
            catBadge.style.background = "rgba(255,255,255,0.1)";
            catBadge.style.borderColor = "rgba(255,255,255,0.2)";
            
            const catIcon = document.createElement('i');
            catIcon.className = "fas fa-tag";
            catIcon.style.marginRight = "5px";
            
            catBadge.appendChild(catIcon);
            catBadge.appendChild(document.createTextNode(' ' + (act.categoria || 'Sistema')));
            tdCategory.appendChild(catBadge);

            const tdMessage = document.createElement('td');
            tdMessage.style.padding = "12px";
            tdMessage.style.fontSize = "0.95rem";
            
            if (act.icon) {
                const msgIcon = document.createElement('i');
                const safeIconClass = /^[a-zA-Z0-9- ]+$/.test(act.icon) ? act.icon : 'fa-info-circle';
                msgIcon.className = `fas ${safeIconClass}`;
                msgIcon.style.marginRight = "8px";
                msgIcon.style.color = "var(--accent-blue)";
                msgIcon.style.width = "16px";
                msgIcon.style.textAlign = "center";
                tdMessage.appendChild(msgIcon);
            }
            tdMessage.appendChild(document.createTextNode(' ' + act.message));

            tr.appendChild(tdTime);
            tr.appendChild(tdCategory);
            tr.appendChild(tdMessage);
            tbody.appendChild(tr);
        });
    }
}

function renderActivity(container, icon, msg, meta, time) {
    const item = document.createElement('div');
    item.className = 'activity-item';

    const iconDiv = document.createElement('div');
    iconDiv.className = 'activity-icon';
    const iconEl = document.createElement('i');
    const safeIcon = /^[a-zA-Z0-9- ]+$/.test(icon) ? icon : 'fa-info-circle';
    safeIcon.split(' ').forEach(cls => {
        if (cls) iconEl.classList.add(cls);
    });
    iconDiv.appendChild(iconEl);

    const detailsDiv = document.createElement('div');
    detailsDiv.className = 'activity-details';
    
    const msgP = document.createElement('p');
    msgP.className = 'activity-msg';
    msgP.textContent = msg;

    const metaP = document.createElement('p');
    metaP.className = 'activity-meta';
    metaP.textContent = meta;

    detailsDiv.appendChild(msgP);
    detailsDiv.appendChild(metaP);

    const timeDiv = document.createElement('div');
    timeDiv.className = 'activity-time';
    timeDiv.textContent = time;

    item.appendChild(iconDiv);
    item.appendChild(detailsDiv);
    item.appendChild(timeDiv);

    container.appendChild(item);
}

document.addEventListener('DOMContentLoaded', initDashboard);
