// Global data storage
let allStats = [];
let allProducts = [];

// Utility to fetch data with cache busting
async function fetchData(url) {
    try {
        const response = await fetch(url + '?t=' + Date.now());
        if (!response.ok) return null;
        return await response.json();
    } catch (e) {
        console.warn("Fetch error: " + url, e);
        return null;
    }
}

async function initDashboard() {
    // Check for file:// protocol (CORS issues)
    if (window.location.protocol === 'file:') {
        console.error("CORS Error: The dashboard must be served via HTTP (e.g., http://localhost:8000) to load data.");
        const warning = document.createElement('div');
        warning.style = "position: fixed; top: 0; left: 0; width: 100%; background: #ef4444; color: white; text-align: center; padding: 15px; z-index: 9999; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.3);";
        warning.innerHTML = `⚠️ Error de Seguridad: Abre el dashboard usando <a href="http://localhost:8000/dashboard/index.html" style="color: white; text-decoration: underline;">http://localhost:8000/dashboard/index.html</a>`;
        document.body.prepend(warning);
        return;
    }

    // Set Current Date
    const now = new Date();
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    document.getElementById('currentTime').innerText = now.toLocaleDateString('en-US', options).toUpperCase();

    // 1. Fetch Data
    allStats = await fetchData('../data_activa/historico_stats.json') || [];
    const productsObj = await fetchData('../data_activa/estado_productos.json') || {};
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
        row.innerHTML = `
            <td style="font-weight: 600; color: var(--accent-blue);">${p.sku}</td>
            <td>${p.nombre.substring(0, 50)}${p.nombre.length > 50 ? '...' : ''}</td>
            <td>$${p.precio_original || 0}</td>
            <td><span style="color: ${p.stock > 0 ? '#10b981' : '#ef4444'}">${p.stock}</span></td>
            <td>
                <div class="status-badges">
                    <div class="status-badge ${p.subido_a_woo ? 'active-woo' : ''}" title="WooCommerce"><i class="fas fa-shopping-cart"></i></div>
                    <div class="status-badge ${p.ia_mejorado ? 'active-ia' : ''}" title="IA Improved"><i class="fas fa-magic"></i></div>
                    <div class="status-badge ${p.tiene_imagen ? 'active-img' : ''}" title="Has Image"><i class="fas fa-image"></i></div>
                </div>
            </td>
        `;
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
    summary.innerHTML = `
        <div class="stat-box"><h4>Eficiencia IA</h4><div class="val" style="color: var(--accent-purple)">${iaData[iaData.length-1]}%</div></div>
        <div class="stat-box"><h4>Sincronización</h4><div class="val" style="color: var(--accent-blue)">${wooData[wooData.length-1]}%</div></div>
        <div class="stat-box"><h4>Catálogo</h4><div class="val">${latest.total_productos}</div></div>
    `;
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
        list.innerHTML = '<div style="color: var(--text-muted); text-align: center; margin-top: 20px;">Sin actividades recientes.</div>';
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
            tr.style = "border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s;";
            tr.onmouseover = function() { this.style.backgroundColor = "rgba(255,255,255,0.03)"; };
            tr.onmouseout = function() { this.style.backgroundColor = "transparent"; };

            const dateObj = new Date(act.timestamp);
            const timeStr = dateObj.toLocaleDateString() + ' ' + dateObj.toLocaleTimeString();
            const iconHtml = act.icon ? `<i class="fas ${act.icon}" style="margin-right:8px; color:var(--accent-blue); width: 16px; text-align: center;"></i>` : '';
            
            tr.innerHTML = `
                <td style="padding: 12px; color: var(--text-muted); font-size: 0.85rem;">${timeStr}</td>
                <td style="padding: 12px; font-weight: 600;"><span class="status-badge" style="background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.2);"><i class="fas fa-tag" style="margin-right: 5px;"></i> ${act.categoria || 'Sistema'}</span></td>
                <td style="padding: 12px; font-size: 0.95rem;">${iconHtml} ${act.message}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

function renderActivity(container, icon, msg, meta, time) {
    container.innerHTML += `
        <div class="activity-item">
            <div class="activity-icon"><i class="fas ${icon}"></i></div>
            <div class="activity-details"><p class="activity-msg">${msg}</p><p class="activity-meta">${meta}</p></div>
            <div class="activity-time">${time}</div>
        </div>
    `;
}

document.addEventListener('DOMContentLoaded', initDashboard);
