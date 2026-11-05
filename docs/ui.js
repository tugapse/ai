function switchTab(tabId, el) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');

    if (el) {
        el.classList.add('active');
    } else {
        document.querySelector('.tab-btn').classList.add('active');
    }
    document.getElementById('tab-' + tabId).style.display = 'block';
}

function resetCamera() {
    if (window.Graph) {
        window.Graph.cameraPosition({ x: 0, y: 0, z: 900 }, { x: 0, y: 0, z: 0 }, 1500);
    }
}

function setInspectorCollapsed(collapsed) {
    const panel = document.getElementById('info-panel');
    const toggle = document.getElementById('inspector-toggle-btn');
    if (!panel || !toggle) return;

    panel.classList.toggle('is-collapsed', collapsed);
    if (!collapsed) {
        panel.scrollTop = 0;
    }
    toggle.textContent = collapsed ? 'SHOW' : 'HIDE';
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.setAttribute('aria-label', collapsed ? 'Show component inspector' : 'Hide component inspector');
}

function hideInspectorAndSelection() {
    clearSelection();
    setInspectorCollapsed(true);
}

function toggleInspectorPanel() {
    const panel = document.getElementById('info-panel');
    if (!panel) return;
    setInspectorCollapsed(!panel.classList.contains('is-collapsed'));
}

function focusNodeById(id) {
    const targetNode = window.graphDataGlobal.nodes.find(n => n.id === id);
    if (targetNode && window.Graph) {
        window.Graph.onNodeClick()(targetNode);
    }
}

function focusCluster(clusterName) {
    const nodesInCluster = window.clusterGroups[clusterName];
    if (!nodesInCluster || nodesInCluster.length === 0) return;

    window.highlightNodes.clear();
    window.highlightLinks.clear();
    window.searchMatchingNodes.clear();
    window.focusedNode = null;

    const clusterNodeIds = new Set();
    let sumX = 0, sumY = 0, sumZ = 0;
    let validCount = 0;

    nodesInCluster.forEach(n => {
        clusterNodeIds.add(n.id);
        window.searchMatchingNodes.add(n.id);
        window.highlightNodes.add(n.id);
        if (typeof n.x === 'number') {
            sumX += n.x; sumY += n.y; sumZ += n.z;
            validCount++;
        }
    });

    window.graphDataGlobal.links.forEach(link => {
        const sId = typeof link.source === 'object' ? link.source.id : link.source;
        const tId = typeof link.target === 'object' ? link.target.id : link.target;
        if (clusterNodeIds.has(sId) && clusterNodeIds.has(tId)) {
            window.highlightLinks.add(link);
        }
    });

    if (validCount > 0) {
        const cx = sumX / validCount;
        const cy = sumY / validCount;
        const cz = sumZ / validCount;

        const distance = 500;
        const distRatio = 1 + distance / Math.hypot(cx, cy, cz);
        window.Graph.cameraPosition(
            { x: cx === 0 ? 0 : cx * distRatio, y: cy === 0 ? 0 : cy * distRatio, z: cz === 0 ? distance : cz * distRatio },
            { x: cx, y: cy, z: cz },
            1200
        );
    }

    animateToSelection(0.85);

    document.getElementById('panel-title').innerText = 'CLUSTER / SUBSYSTEM';
    document.getElementById('node-details').innerHTML = `
        <div class="property"><span class="prop-title">SUBSYSTEM DOMAIN</span><strong style="color: var(--hud-cyan); font-size: 16px;">${clusterName}</strong></div>
        <div class="property"><span class="prop-title">COMPONENTS DETECTED</span><span style="color: #fff; font-weight: 600; font-size: 14px;">${validCount}</span></div>
        <div style="margin-top: 15px; padding: 10px; border-left: 2px solid var(--hud-cyan); background: rgba(0, 240, 255, 0.05); color: #94a3b8; font-size: 12px; font-style: italic;">
            Showing all components encapsulated in this subsystem. Click any individual node to inspect its specific properties, or press ESC to view the entire universe.
        </div>
    `;
    document.getElementById('doc-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">No architectural documentation available for entire cluster.</p>';
    document.getElementById('raw-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">N/A</p>';
    switchTab('specs', document.querySelectorAll('.tab-btn')[0]);
}

const searchInput = document.getElementById('hud-search-input');
const searchResults = document.getElementById('hud-search-results');

function setupSearchSystem() {
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (!query) {
            searchResults.style.display = 'none';
            window.searchMatchingNodes.clear();
            if (window.highlightNodes.size === 0) {
                animateToSelection(0.0);
            }
            return;
        }

        const matches = window.graphDataGlobal.nodes.filter(n => {
            const idMatch = (n.id || '').toLowerCase().includes(query);
            const nameMatch = (n.name || '').toLowerCase().includes(query);
            const groupMatch = (n.group || '').toLowerCase().includes(query);
            const subMatch = (n.subsystem || '').toLowerCase().includes(query);
            const summaryMatch = (n.semantic_summary || '').toLowerCase().includes(query);
            const keywordMatch = (n.keywords || []).some(k => k.toLowerCase().includes(query));
            return idMatch || nameMatch || groupMatch || subMatch || summaryMatch || keywordMatch;
        });

        window.searchMatchingNodes.clear();
        matches.forEach(m => window.searchMatchingNodes.add(m.id));
        if (window.highlightNodes.size === 0) {
            animateToSelection(0.85);
        }

        renderSearchResults(matches.slice(0, 15), query);
    });

    window.addEventListener('keydown', (e) => {
        if (e.key === '/' && document.activeElement !== searchInput) {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        } else if (e.key === 'Escape') {
            if (searchResults.style.display === 'flex') {
                searchResults.style.display = 'none';
                searchInput.blur();
            } else {
                hideInspectorAndSelection();
            }
        }
    });

    document.addEventListener('click', (e) => {
        const panel = document.getElementById('info-panel');
        const graph = document.getElementById('3d-graph');
        const target = e.target;
        const clickedInsidePanel = panel && panel.contains(target);
        const clickedInsideGraph = graph && graph.contains(target);
        const clickedOnSearch = searchInput.contains(target) || searchResults.contains(target);
        const clickedOnLabelLayer = target.closest && target.closest('#hud-labels-layer');
        const clickedOnClusterBadge = target.closest && target.closest('.hud-cluster-badge');
        const clickedOnFloatingLabel = target.closest && target.closest('.hud-floating-pill');
        const clickedOnGraphLabel = target.closest && (target.closest('.label') || target.closest('[class*="label"]'));

        if (!searchInput.contains(target) && !searchResults.contains(target)) {
            searchResults.style.display = 'none';
        }

        if (!clickedInsidePanel && !clickedInsideGraph && !clickedOnSearch && !clickedOnLabelLayer && !clickedOnClusterBadge && !clickedOnFloatingLabel && !clickedOnGraphLabel) {
            hideInspectorAndSelection();
        }
    });
}

function renderSearchResults(items, query) {
    if (items.length === 0) {
        searchResults.innerHTML = `<div style="padding: 10px; color: #64748b; font-size: 11px; font-style: italic;">No components or keywords matching "${query}"</div>`;
        searchResults.style.display = 'flex';
        return;
    }

    searchResults.innerHTML = '';
    items.forEach(node => {
        const item = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `
            <div class="search-item-header">
                <span class="search-item-title">${node.name || node.id.split('/').pop()}</span>
                <span class="search-item-type">${node.group}</span>
            </div>
            <div class="search-item-path">${node.id}</div>
            ${node.semantic_summary ? `<div class="search-item-summary">${node.semantic_summary}</div>` : ''}
        `;

        item.addEventListener('click', () => {
            searchResults.style.display = 'none';
            searchInput.value = node.name || node.id.split('/').pop();
            window.searchMatchingNodes.clear();
            focusNodeById(node.id);
        });

        searchResults.appendChild(item);
    });

    searchResults.style.display = 'flex';
}
