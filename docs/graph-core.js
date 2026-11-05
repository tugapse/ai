window.Graph = null;
window.graphDataGlobal = null;
window.focusedNode = null;
window.highlightNodes = new Set();
window.highlightLinks = new Set();
window.searchMatchingNodes = new Set();
window.clusterGroups = {};

window.selectionIntensity = 0.0;
window.animFrameId = null;

function easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
}

function getNodeBaseColor(node) {
    if (node.group === 'module') return { r: 0, g: 240, b: 255 };
    if (node.group === 'Class') return { r: 168, g: 85, b: 247 };
    if (node.group === 'Function') return { r: 0, g: 255, b: 170 };
    if (node.group === 'Service') return { r: 255, g: 170, b: 0 };
    return { r: 100, g: 116, b: 139 };
}

function getLinkBaseColor(link) {
    const rel = (link.relation || '').toLowerCase();
    if (rel === 'imports') return { r: 168, g: 85, b: 247 };
    if (rel === 'calls') return { r: 0, g: 255, b: 170 };
    if (rel === 'inherits') return { r: 255, g: 170, b: 0 };
    return { r: 0, g: 240, b: 255 };
}

function buildClusterGroups(nodes) {
    window.clusterGroups = {};
    nodes.forEach(node => {
        if (node.group === 'External/Dependency') {
            node.subsystem = 'EXTERNAL';
        } else if (!node.subsystem) {
            node.subsystem = 'CORE';
        }

        const groupName = node.subsystem;
        if (!window.clusterGroups[groupName]) {
            window.clusterGroups[groupName] = [];
        }
        window.clusterGroups[groupName].push(node);
    });

    Object.keys(window.clusterGroups).forEach(k => {
        if (window.clusterGroups[k].length < 4) delete window.clusterGroups[k];
    });

    const groupKeys = Object.keys(window.clusterGroups);
    const radius = 600;
    groupKeys.forEach((key, idx) => {
        const angle = (2 * Math.PI * idx) / groupKeys.length;
        window.clusterGroups[key].targetCenter = {
            x: radius * Math.cos(angle),
            y: (idx % 2 === 0 ? 1 : -1) * 120,
            z: radius * Math.sin(angle)
        };
    });
}

function applyGraphPhysicsState() {
    if (!window.Graph || !window.graphDataGlobal) return;

    const hasSelection = !!window.focusedNode || window.selectionIntensity > 0.2 || window.searchMatchingNodes.size > 0;
    const clusterAlpha = hasSelection ? 0.008 : 0.08;
    const stopRadius = hasSelection ? 450 : 350;

    window.Graph.d3Force('cluster', () => {
        window.graphDataGlobal.nodes.forEach(node => {
            const grp = window.clusterGroups[node.subsystem];
            if (grp && grp.targetCenter) {
                const dx = grp.targetCenter.x - node.x;
                const dy = grp.targetCenter.y - node.y;
                const dz = grp.targetCenter.z - node.z;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

                if (dist > stopRadius) {
                    const factor = ((dist - stopRadius) / dist) * clusterAlpha * (hasSelection ? 0.4 : 1.0);
                    node.vx += dx * factor;
                    node.vy += dy * factor;
                    node.vz += dz * factor;
                }
            }
        });
    });

    window.Graph.d3Force('link')
        .distance(link => {
            const sSub = link.source.subsystem;
            const tSub = link.target.subsystem;
            return (sSub && tSub && sSub === tSub) ? (hasSelection ? 90 : 60) : (hasSelection ? 360 : 250);
        })
        .strength(link => {
            const sSub = link.source.subsystem;
            const tSub = link.target.subsystem;
            return (sSub && tSub && sSub === tSub) ? (hasSelection ? 0.12 : 0.6) : (hasSelection ? 0.02 : 0.1);
        });

    window.Graph.d3Force('charge').strength(hasSelection ? -150 : -280);
}

function animateToSelection(targetValue) {
    if (window.animFrameId) cancelAnimationFrame(window.animFrameId);
    const startVal = window.selectionIntensity;
    const delta = targetValue - startVal;
    const startTime = performance.now();
    const duration = 400;

    function step(now) {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / duration);
        const eased = easeOutCubic(progress);

        window.selectionIntensity = startVal + delta * eased;
        applyGraphPhysicsState();

        window.Graph.nodeColor(window.Graph.nodeColor())
            .linkColor(window.Graph.linkColor())
            .linkWidth(window.Graph.linkWidth());

        if (progress < 1) {
            window.animFrameId = requestAnimationFrame(step);
        } else {
            window.selectionIntensity = targetValue;
            applyGraphPhysicsState();
        }
    }
    window.animFrameId = requestAnimationFrame(step);
}

function clearSelection() {
    if (window.highlightNodes.size === 0 && window.selectionIntensity === 0.0 && window.searchMatchingNodes.size === 0) {
        setInspectorCollapsed(true);
        return;
    }

    window.focusedNode = null;
    window.highlightNodes.clear();
    window.highlightLinks.clear();
    window.searchMatchingNodes.clear();
    animateToSelection(0.0);
    applyGraphPhysicsState();

    const container = document.getElementById('hud-labels-layer');
    container.querySelectorAll('.hud-floating-pill').forEach(el => el.remove());

    document.getElementById('panel-title').innerText = 'COMPONENT INSPECTOR';
    document.getElementById('node-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">Select a node in the graph to view technical specifications and memory context.</p>';
    document.getElementById('doc-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">No architectural documentation found for this node.</p>';
    document.getElementById('raw-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">Documentation stream unavailable.</p>';
    setInspectorCollapsed(true);
}

function syncFloatingLabels() {
    const container = document.getElementById('hud-labels-layer');
    if (!window.Graph || !window.graphDataGlobal) {
        requestAnimationFrame(syncFloatingLabels);
        return;
    }

    const showClusters = (window.selectionIntensity < 0.6 && window.searchMatchingNodes.size === 0);
    const clusterOpacity = Math.max(0, 1 - window.selectionIntensity * 1.8);

    Object.entries(window.clusterGroups).forEach(([name, grp]) => {
        const nodes = Array.isArray(grp) ? grp : grp;
        let validCount = 0;
        let sumX = 0, sumY = 0, sumZ = 0;

        nodes.forEach(n => {
            if (typeof n.x === 'number') {
                sumX += n.x; sumY += n.y; sumZ += n.z;
                validCount++;
            }
        });

        if (validCount === 0) return;
        const avgX = sumX / validCount;
        const avgY = sumY / validCount;
        const avgZ = sumZ / validCount;

        const screenPos = window.Graph.graph2ScreenCoords(avgX, avgY, avgZ);
        const safeKey = 'cluster-' + btoa(name).replace(/=/g, '');
        let badge = document.getElementById(safeKey);

        if (!badge) {
            badge = document.createElement('div');
            badge.id = safeKey;
            badge.className = 'hud-cluster-badge';
            badge.innerHTML = `${name} <span>[${validCount}]</span>`;
            badge.addEventListener('click', (event) => {
                event.stopPropagation();
                focusCluster(name);
            });
            container.appendChild(badge);
        }

        badge.style.left = `${screenPos.x}px`;
        badge.style.top = `${screenPos.y}px`;
        badge.style.opacity = showClusters ? clusterOpacity.toFixed(2) : '0';
        badge.style.pointerEvents = showClusters ? 'auto' : 'none';
    });

    const activeNodeSet = window.highlightNodes.size > 0 ? window.highlightNodes : (window.searchMatchingNodes.size > 0 ? window.searchMatchingNodes : null);

    const existingPills = container.querySelectorAll('.hud-floating-pill');
    existingPills.forEach(pill => {
        const nodeId = pill.dataset.nodeId;
        if (!activeNodeSet || !activeNodeSet.has(nodeId)) {
            pill.remove();
        }
    });

    if (activeNodeSet) {
        activeNodeSet.forEach(nodeId => {
            const node = window.graphDataGlobal.nodes.find(n => n.id === nodeId);
            if (!node || typeof node.x !== 'number') return;

            const screenPos = window.Graph.graph2ScreenCoords(node.x, node.y, node.z);
            const pillId = 'pill-' + btoa(node.id).replace(/=/g, '');
            let pill = document.getElementById(pillId);

            if (!pill) {
                pill = document.createElement('div');
                pill.id = pillId;
                pill.dataset.nodeId = node.id;
                pill.className = 'hud-floating-pill' + (window.focusedNode && window.focusedNode.id === node.id ? ' is-target' : '');
                pill.innerText = node.name || node.id.split('/').pop().split('#').pop();
                container.appendChild(pill);
            } else {
                const isTarget = (window.focusedNode && window.focusedNode.id === node.id);
                pill.classList.toggle('is-target', isTarget);
            }

            pill.style.left = `${screenPos.x}px`;
            pill.style.top = `${screenPos.y - 14}px`;
            pill.style.opacity = (0.2 + 0.8 * window.selectionIntensity).toFixed(2);
        });
    }

    requestAnimationFrame(syncFloatingLabels);
}
