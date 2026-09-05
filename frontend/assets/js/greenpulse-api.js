/**
 * GreenPulse API Integration
 * ---------------------------------------------------
 * FastAPI Backend:
 *
 *   GET  /api/health
 *   GET  /api/regions
 *   GET  /api/electricity/carbon/latest?zone=DE
 *   GET  /api/electricity/carbon/forecast?zone=DE&horizon_hours=24
 *   POST /api/decision
 *
 * Frontend:
 *   window.GREENPULSE_API_BASE = 'http://localhost:8000';
 * ---------------------------------------------------
 */

(function () {
    'use strict';

    // ---------------------------------------------------
    // Configuration
    // ---------------------------------------------------

    const API_BASE_URL =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://localhost:8000"
        : "https://trinitywehack-production.up.railway.app";

    const DEFAULT_ZONE = 'DE';
    const FORECAST_HORIZON_HOURS = 24;
    const POLL_INTERVAL_MS = 60000;

    let forecastChart = null;
    let currentZone = DEFAULT_ZONE;
    let allRegions = [];
    let pollTimer = null;

    // ---------------------------------------------------
    // Service health
    // ---------------------------------------------------

    const serviceHealth = {
        api: 'unknown',
        regions: 'unknown',
        electricity: 'unknown',
        decision: 'ready'
    };

    // ---------------------------------------------------
    // Fetch helper
    // ---------------------------------------------------

    async function apiRequest(path, options = {}) {
        const url = `${API_BASE_URL}${path}`;

        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json'
            },
            ...options
        });

        if (!response.ok) {
            let detail = '';

            try {
                const body = await response.json();

                if (body.detail) {
                    detail = ` - ${body.detail}`;
                }
            } catch {
                // Ignore non-JSON response
            }

            throw new Error(
                `Request to ${path} failed (${response.status})${detail}`
            );
        }

        return response.json();
    }

    // ---------------------------------------------------
    // Backend health
    // ---------------------------------------------------

    async function refreshHealth() {
        try {
            const health = await apiRequest('/api/health');

            serviceHealth.api =
                health.status === 'healthy'
                    ? 'ok'
                    : 'degraded';

        } catch (err) {
            console.error(
                '[GreenPulse] Health check failed:',
                err
            );

            serviceHealth.api = 'down';
        }

        updateHealthDisplay();
    }

    function updateHealthDisplay() {
        const badge =
            document.getElementById('backend-status');

        const dot =
            document.getElementById('backend-status-dot');

        setHealthRow(
            'health-api',
            serviceHealth.api
        );

        setHealthRow(
            'health-regions',
            serviceHealth.regions
        );

        setHealthRow(
            'health-electricity',
            serviceHealth.electricity
        );

        setHealthRow(
            'health-decision',
            serviceHealth.decision
        );

        const allOk =
            Object.values(serviceHealth).every(
                status =>
                    status === 'ok' ||
                    status === 'ready'
            );

        const anyDown =
            Object.values(serviceHealth).some(
                status => status === 'down'
            );

        if (badge) {
            if (allOk) {
                badge.textContent = 'Backend Online';
                badge.className = 'badge bg-success';
            } else if (anyDown) {
                badge.textContent = 'Backend Offline';
                badge.className = 'badge bg-danger';
            } else {
                badge.textContent = 'Backend Degraded';
                badge.className =
                    'badge bg-warning text-dark';
            }
        }

        if (dot) {
            dot.classList.toggle(
                'status-dot-online',
                allOk
            );

            dot.classList.toggle(
                'status-dot-offline',
                !allOk
            );
        }
    }

    function setHealthRow(elementId, status) {
        const el =
            document.getElementById(elementId);

        if (!el) return;

        const labels = {
            ok: 'Operational',
            ready: 'Ready',
            degraded: 'Degraded',
            down: 'Offline',
            unknown: 'Checking...'
        };

        el.textContent =
            labels[status] || 'Unknown';

        el.classList.remove(
            'text-success',
            'text-warning',
            'text-danger',
            'text-muted'
        );

        if (
            status === 'ok' ||
            status === 'ready'
        ) {
            el.classList.add('text-success');
        } else if (status === 'degraded') {
            el.classList.add('text-warning');
        } else if (status === 'down') {
            el.classList.add('text-danger');
        } else {
            el.classList.add('text-muted');
        }
    }

    // ---------------------------------------------------
    // Live Carbon Intensity
    // ---------------------------------------------------

    async function refreshCarbonIntensity(
        zone = currentZone
    ) {
        const valueEl =
            document.getElementById(
                'stat-carbon-value'
            );

        const zoneEl =
            document.getElementById(
                'stat-carbon-zone'
            );

        if (valueEl) {
            valueEl.textContent = 'Loading...';
        }

        try {
            const response = await apiRequest(
                `/api/electricity/carbon/latest?zone=${encodeURIComponent(zone)}`
            );

            const data = response.data || {};

            const intensity =
                data.carbonIntensity ??
                data.carbon_intensity;

            if (valueEl) {
                valueEl.textContent =
                    intensity != null
                        ? `${Math.round(intensity)} gCO₂/kWh`
                        : 'Unavailable';
            }

            if (zoneEl) {
                zoneEl.innerHTML = `
                    <i class="bi bi-geo-alt"></i>
                    <span>
                        Zone: ${escapeHtml(data.zone || zone)}
                    </span>
                `;
            }

            serviceHealth.electricity = 'ok';

        } catch (err) {
            console.error(
                '[GreenPulse] Carbon intensity fetch failed:',
                err
            );

            if (valueEl) {
                valueEl.textContent = 'Unavailable';
            }

            serviceHealth.electricity = 'down';
        }

        updateHealthDisplay();
    }

    // ---------------------------------------------------
    // Regions
    // ---------------------------------------------------

    async function refreshRegions() {
        const listEl =
            document.getElementById('regions-list');

        if (!listEl) return;

        try {
            const response =
                await apiRequest('/api/regions');

            allRegions =
                Array.isArray(response.regions)
                    ? response.regions
                    : [];

            renderRegions(allRegions);

            serviceHealth.regions = 'ok';

        } catch (err) {
            console.error(
                '[GreenPulse] Regions fetch failed:',
                err
            );

            allRegions = [];

            listEl.innerHTML =
                renderEmptyState(
                    'bi-exclamation-triangle',
                    'Could not load regions',
                    'Check the backend connection and try again.'
                );

            serviceHealth.regions = 'down';
        }

        updateHealthDisplay();
    }

    function renderRegions(regions) {
        const listEl =
            document.getElementById(
                'regions-list'
            );

        if (!listEl) return;

        if (!regions.length) {
            listEl.innerHTML =
                renderEmptyState(
                    'bi-inbox',
                    'No regions found',
                    'No matching regions are currently available.'
                );

            return;
        }

        listEl.innerHTML = regions
            .map(region => {
                const grid =
                    String(
                        region.grid_status || ''
                    ).toUpperCase();

                const level =
                    gridLevel(
                        grid,
                        region.gpu_available
                    );

                const details = [
                    region.latency_ms != null
                        ? `${region.latency_ms}ms latency`
                        : null,

                    region.cost_index != null
                        ? `cost ${region.cost_index}`
                        : null,

                    region.gpu_available === false
                        ? 'no GPU'
                        : null
                ]
                    .filter(Boolean)
                    .join(' · ');

                return `
                    <div class="transaction-item">

                        <div class="transaction-icon
                            ${level.bgClass}
                            ${level.textClass}">
                            <i class="bi ${level.icon}"></i>
                        </div>

                        <div class="transaction-info">

                            <div class="transaction-name">
                                ${escapeHtml(
                                    region.name ||
                                    region.id ||
                                    'Unknown region'
                                )}
                            </div>

                            <div class="transaction-date">
                                Zone ${escapeHtml(
                                    region.id || '—'
                                )}
                                ${details
                                    ? ` · ${escapeHtml(details)}`
                                    : ''}
                            </div>

                        </div>

                        <div class="transaction-amount
                            ${level.textClass}">

                            ${escapeHtml(
                                grid || 'UNKNOWN'
                            )}

                        </div>

                    </div>
                `;
            })
            .join('');
    }

    function gridLevel(
        gridStatus,
        gpuAvailable
    ) {
        if (gpuAvailable === false) {
            return {
                icon: 'bi-cpu',
                bgClass: 'bg-danger-subtle',
                textClass: 'text-danger'
            };
        }

        if (gridStatus === 'NORMAL') {
            return {
                icon: 'bi-leaf',
                bgClass: 'bg-forest-light',
                textClass: 'text-lime'
            };
        }

        if (
            gridStatus === 'STRAINED' ||
            gridStatus === 'WARNING'
        ) {
            return {
                icon: 'bi-cloud-sun',
                bgClass: 'bg-warning-subtle',
                textClass: 'text-warning'
            };
        }

        return {
            icon: 'bi-question-circle',
            bgClass: 'bg-secondary-subtle',
            textClass: 'text-secondary'
        };
    }

    function filterRegions(query) {
        const q =
            query.trim().toLowerCase();

        if (!q) {
            renderRegions(allRegions);
            return;
        }

        const filtered =
            allRegions.filter(region => {
                const haystack =
                    `${region.name || ''} ${region.id || ''}`
                        .toLowerCase();

                return haystack.includes(q);
            });

        renderRegions(filtered);
    }

    // ---------------------------------------------------
    // Carbon Forecast
    // ---------------------------------------------------

    async function refreshForecast(
        zone = currentZone
    ) {
        const chartEl =
            document.getElementById(
                'carbon-forecast-chart'
            );

        const zoneBadge =
            document.getElementById(
                'forecast-zone'
            );

        if (zoneBadge) {
            zoneBadge.textContent =
                `Zone: ${zone}`;
        }

        if (!chartEl) return;

        try {
            /*
             * Directly call the working FastAPI
             * forecast endpoint.
             *
             * GET:
             * /api/electricity/carbon/forecast
             *
             * Example:
             * ?zone=DE&horizon_hours=24
             */

            const response =
                await apiRequest(
                    `/api/electricity/carbon/forecast?zone=${encodeURIComponent(zone)}&horizon_hours=${FORECAST_HORIZON_HOURS}`
                );

            /*
             * Your FastAPI returns:
             *
             * {
             *   success: true,
             *   source: "Electricity Maps",
             *   data: {
             *       zone: "DE",
             *       forecast: [...]
             *   }
             * }
             */

            const forecastData =
                response.data?.forecast;

            if (
                !Array.isArray(forecastData) ||
                forecastData.length === 0
            ) {
                throw new Error(
                    'Forecast data unavailable'
                );
            }

            renderForecastChart(
                forecastData
            );

            serviceHealth.electricity = 'ok';
            updateHealthDisplay();

        } catch (err) {
            console.error(
                '[GreenPulse] Forecast fetch failed:',
                err
            );

            if (forecastChart) {
                forecastChart.destroy();
                forecastChart = null;
            }

            chartEl.innerHTML =
                renderEmptyState(
                    'bi-graph-down',
                    'Forecast unavailable',
                    'Could not load the carbon intensity forecast.'
                );
        }
    }

    // ---------------------------------------------------
    // Render Forecast Chart
    // ---------------------------------------------------

    function renderForecastChart(data) {
        const chartEl =
            document.getElementById(
                'carbon-forecast-chart'
            );

        if (!chartEl) return;

        if (typeof ApexCharts === 'undefined') {
            console.error(
                '[GreenPulse] ApexCharts is not loaded.'
            );

            chartEl.innerHTML =
                renderEmptyState(
                    'bi-bar-chart',
                    'Chart unavailable',
                    'ApexCharts could not be loaded.'
                );

            return;
        }

        chartEl.innerHTML = '';

        const categories =
            data.map(point =>
                formatHour(
                    point.datetime ||
                    point.time
                )
            );

        const values =
            data.map(point =>
                Math.round(
                    point.carbonIntensity ??
                    point.carbon_intensity ??
                    0
                )
            );

        const options = {
            chart: {
                type: 'area',
                height: 300,
                toolbar: {
                    show: false
                },
                fontFamily: 'inherit'
            },

            series: [
                {
                    name:
                        'Carbon Intensity (gCO₂/kWh)',
                    data: values
                }
            ],

            xaxis: {
                categories: categories,
                labels: {
                    rotate: -45
                }
            },

            yaxis: {
                title: {
                    text: 'gCO₂eq/kWh'
                },

                labels: {
                    formatter: value =>
                        `${Math.round(value)}`
                }
            },

            colors: ['#B4F105'],

            fill: {
                type: 'gradient',

                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.4,
                    opacityTo: 0.05,
                    stops: [
                        0,
                        90,
                        100
                    ]
                }
            },

            stroke: {
                curve: 'smooth',
                width: 2
            },

            dataLabels: {
                enabled: false
            },

            tooltip: {
                y: {
                    formatter: value =>
                        `${value} gCO₂/kWh`
                }
            },

            grid: {
                borderColor:
                    'rgba(0,0,0,0.06)'
            }
        };

        if (forecastChart) {
            forecastChart.updateOptions(
                options
            );
        } else {
            forecastChart =
                new ApexCharts(
                    chartEl,
                    options
                );

            forecastChart.render();
        }
    }

    // ---------------------------------------------------
    // Format Time
    // ---------------------------------------------------

    function formatHour(isoString) {
        if (!isoString) return '';

        try {
            const date =
                new Date(isoString);

            return date.toLocaleTimeString(
                [],
                {
                    hour: '2-digit',
                    minute: '2-digit'
                }
            );

        } catch {
            return isoString;
        }
    }

    // ---------------------------------------------------
    // Decision Engine
    // ---------------------------------------------------

    async function runDecision() {
        const badge =
            document.getElementById(
                'decision-status-badge'
            );

        const dateEl =
            document.getElementById(
                'decision-status-date'
            );

        const textEl =
            document.getElementById(
                'decision-status-text'
            );

        const regionEl =
            document.getElementById(
                'stat-best-region'
            );

        const regionDetailEl =
            document.getElementById(
                'stat-best-region-detail'
            );

        setDecisionButtonsDisabled(true);

        if (badge) {
            badge.textContent = 'Running...';
        }

        if (textEl) {
            textEl.textContent =
                'Evaluating regions against live carbon intensity data...';
        }

        try {
            const response =
                await apiRequest(
                    '/api/decision',
                    {
                        method: 'POST'
                    }
                );

            const result =
                response.result || {};

            const isRun =
                result.decision === 'RUN';

            if (badge) {
                badge.textContent =
                    isRun
                        ? 'Decision Ready'
                        : 'No Feasible Plan';

                badge.classList.toggle(
                    'alert-green-badge',
                    true
                );
            }

            if (dateEl) {
                dateEl.textContent =
                    'Just now';
            }

            if (textEl) {
                textEl.textContent =
                    result.reason ||
                    'The decision engine did not return a reason.';
            }

            if (regionEl) {
                regionEl.textContent =
                    result.region ||
                    'No region selected';
            }

            if (regionDetailEl) {
                if (isRun) {
                    const carbonG =
                        result.estimated_carbon_g != null
                            ? `${Math.round(result.estimated_carbon_g)} g CO₂ estimated`
                            : null;

                    const budget =
                        result.carbon_budget_met
                            ? 'budget met'
                            : 'over budget';

                    const deadline =
                        result.deadline_met
                            ? 'deadline met'
                            : 'deadline at risk';

                    regionDetailEl.textContent =
                        [
                            carbonG,
                            budget,
                            deadline
                        ]
                            .filter(Boolean)
                            .join(' · ');

                } else {
                    regionDetailEl.textContent =
                        result.reason ||
                        'No region satisfied the constraints.';
                }
            }

        } catch (err) {
            console.error(
                '[GreenPulse] Decision run failed:',
                err
            );

            if (badge) {
                badge.textContent =
                    'Decision Failed';
            }

            if (textEl) {
                textEl.textContent =
                    'Could not reach the decision engine. Please try again.';
            }

        } finally {
            setDecisionButtonsDisabled(
                false
            );
        }
    }

    function setDecisionButtonsDisabled(
        disabled
    ) {
        [
            'btn-run-decision',
            'btn-run-decision-alert',
            'btn-run-decision-menu',
            'btn-run-decision-bottom'
        ].forEach(id => {
            const btn =
                document.getElementById(id);

            if (btn) {
                btn.disabled = disabled;
            }
        });
    }

    // ---------------------------------------------------
    // Shared Helpers
    // ---------------------------------------------------

    function renderEmptyState(
        icon,
        title,
        subtitle
    ) {
        return `
            <div class="transaction-item">

                <div class="transaction-icon
                    bg-forest-light
                    text-lime">

                    <i class="bi ${icon}"></i>

                </div>

                <div class="transaction-info">

                    <div class="transaction-name">
                        ${escapeHtml(title)}
                    </div>

                    <div class="transaction-date">
                        ${escapeHtml(subtitle)}
                    </div>

                </div>

            </div>
        `;
    }

    function escapeHtml(str) {
        const div =
            document.createElement('div');

        div.textContent =
            str == null
                ? ''
                : String(str);

        return div.innerHTML;
    }

    // ---------------------------------------------------
    // Refresh All
    // ---------------------------------------------------

    function refreshAll() {
        refreshHealth();
        refreshCarbonIntensity();
        refreshRegions();
        refreshForecast();
    }

    // ---------------------------------------------------
    // Polling
    // ---------------------------------------------------

    function startPolling() {
        stopPolling();

        pollTimer =
            window.setInterval(
                refreshAll,
                POLL_INTERVAL_MS
            );
    }

    function stopPolling() {
        if (pollTimer) {
            window.clearInterval(
                pollTimer
            );

            pollTimer = null;
        }
    }

    // ---------------------------------------------------
    // Event Wiring
    // ---------------------------------------------------

    function bindEvents() {

        [
            'btn-run-decision',
            'btn-run-decision-alert',
            'btn-run-decision-menu',
            'btn-run-decision-bottom'
        ].forEach(id => {

            const btn =
                document.getElementById(id);

            if (btn) {
                btn.addEventListener(
                    'click',
                    runDecision
                );
            }

        });

        const refreshCarbonBtn =
            document.getElementById(
                'btn-refresh-carbon'
            );

        if (refreshCarbonBtn) {
            refreshCarbonBtn.addEventListener(
                'click',
                () => refreshCarbonIntensity()
            );
        }

        const refreshRegionsBtn =
            document.getElementById(
                'btn-refresh-regions'
            );

        if (refreshRegionsBtn) {
            refreshRegionsBtn.addEventListener(
                'click',
                refreshRegions
            );
        }

        const refreshForecastBtn =
            document.getElementById(
                'btn-refresh-forecast'
            );

        if (refreshForecastBtn) {
            refreshForecastBtn.addEventListener(
                'click',
                () => refreshForecast()
            );
        }

        const refreshAllBtn =
            document.getElementById(
                'btn-refresh-all'
            );

        if (refreshAllBtn) {
            refreshAllBtn.addEventListener(
                'click',
                refreshAll
            );
        }

        const searchInput =
            document.getElementById(
                'main-search'
            );

        if (searchInput) {
            let debounceTimer;

            searchInput.addEventListener(
                'input',
                event => {

                    clearTimeout(
                        debounceTimer
                    );

                    const value =
                        event.target.value;

                    debounceTimer =
                        setTimeout(
                            () =>
                                filterRegions(
                                    value
                                ),
                            200
                        );
                }
            );
        }

        const fullscreenBtn =
            document.getElementById(
                'btn-fullscreen'
            );

        if (fullscreenBtn) {
            fullscreenBtn.addEventListener(
                'click',
                () => {

                    if (
                        !document.fullscreenElement
                    ) {
                        document.documentElement
                            .requestFullscreen?.();

                    } else {
                        document
                            .exitFullscreen?.();
                    }

                }
            );
        }
    }

    // ---------------------------------------------------
    // Initialize
    // ---------------------------------------------------

    function init() {
        bindEvents();
        refreshAll();
        startPolling();
    }

    if (
        document.readyState ===
        'loading'
    ) {
        document.addEventListener(
            'DOMContentLoaded',
            init
        );
    } else {
        init();
    }

    window.addEventListener(
        'beforeunload',
        stopPolling
    );

    // ---------------------------------------------------
    // Browser Console Debugging
    // ---------------------------------------------------

    window.GreenPulseAPI = {
        refreshAll,
        refreshHealth,
        refreshRegions,
        refreshCarbonIntensity,
        refreshForecast,
        runDecision
    };

})();