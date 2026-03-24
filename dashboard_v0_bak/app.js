// Función para cargar JSONs con manejo de errores
async function fetchData(url) {
    try {
        const response = await fetch(url + '?t=' + Date.now()); // Evitar cache
        if (!response.ok) return null;
        return await response.json();
    } catch (e) {
        console.warn("No se pudo cargar: " + url);
        return null;
    }
}

async function initDashboard() {
    // 1. Cargar Datos
    const stats = await fetchData('../data_activa/historico_stats.json');
    const health = await fetchData('../data_activa/health_status.json');

    if (!stats || stats.length === 0) {
        document.getElementById('lastUpdate').innerText = "Sin datos históricos.";
        return;
    }

    const latest = stats[stats.length - 1];

    // 2. Actualizar KPIs
    document.getElementById('kpi-hh').innerText = latest.hh_ahorradas;
    document.getElementById('kpi-total').innerText = latest.total_productos;
    document.getElementById('kpi-ia').innerText = latest.con_ia;

    const iaPercent = ((latest.con_ia / latest.total_productos) * 100).toFixed(1);
    document.getElementById('kpi-percent').innerText = iaPercent + "%";
    document.getElementById('lastUpdate').innerText = "Última actualización: " + latest.timestamp;

    // 3. Sistema de Salud
    const healthContainer = document.getElementById('health-container');
    if (health) {
        healthContainer.innerHTML = "";
        for (const [service, ok] of Object.entries(health.services)) {
            const name = service.replace(/_/g, ' ').toUpperCase();
            healthContainer.innerHTML += `
                <div class="health-item">
                    <span>${name}</span>
                    <div class="status-dot ${ok ? 'dot-ok' : 'dot-err'}"></div>
                </div>
            `;
        }
    }

    // 4. Gráfico de Evolución (Líneas)
    const ctxHistory = document.getElementById('historyChart').getContext('2d');
    new Chart(ctxHistory, {
        type: 'line',
        data: {
            labels: stats.map(s => s.fecha),
            datasets: [
                {
                    label: 'Productos en Catálogo',
                    data: stats.map(s => s.total_productos),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Enriquecidos IA',
                    data: stats.map(s => s.con_ia),
                    borderColor: '#10b981',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#94a3b8' } } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            }
        }
    });

    // 5. Gráfico de Distribución (Rosca)
    const ctxDist = document.getElementById('distributionChart').getContext('2d');
    new Chart(ctxDist, {
        type: 'doughnut',
        data: {
            labels: ['En WooCommerce', 'Pendientes'],
            datasets: [{
                data: [latest.en_woo, latest.total_productos - latest.en_woo],
                backgroundColor: ['#3b82f6', '#1e293b'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '70%',
            plugins: { legend: { display: false } }
        }
    });

    // 6. Logs de ejecución (Simulados del histórico por ahora)
    const logsBody = document.getElementById('logs-body');
    stats.slice(-5).reverse().forEach(s => {
        logsBody.innerHTML += `
            <tr>
                <td>${s.timestamp}</td>
                <td><span class="badge">orchestrator</span></td>
                <td>Refresco automático de stats</td>
            </tr>
        `;
    });
}

document.addEventListener('DOMContentLoaded', initDashboard);
