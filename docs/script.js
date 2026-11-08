let Graph = null;
let graphDataGlobal = null;
let focusedNode = null;
const highlightNodes = new Set();
const highlightLinks = new Set();
const searchMatchingNodes = new Set();
let clusterGroups = {};

let selectionIntensity = 0.0;
let animFrameId = null;

function easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
}

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
    if (Graph) {
        Graph.cameraPosition({ x: 0, y: 0, z: 900 }, { x: 0, y: 0, z: 0 }, 1500);
    }
}

function focusNodeById(id) {
    const targetNode = graphDataGlobal && graphDataGlobal.nodes.find(n => n.id === id);
    if (!targetNode) return;

    if (typeof window.handleNodeSelection === 'function') {
        window.handleNodeSelection(targetNode);
        return;
    }

    if (Graph && typeof Graph.onNodeClick === 'function') {
        const onNodeClick = Graph.onNodeClick();
        if (typeof onNodeClick === 'function') {
            onNodeClick(targetNode);
            return;
        }
    }

    if (Graph && typeof Graph.onNodeClick === 'function') {
        Graph.onNodeClick()(targetNode);
    }
}

function focusCluster(clusterName) {
    const nodesInCluster = clusterGroups[clusterName];
    if (!nodesInCluster || nodesInCluster.length === 0) return;

    highlightNodes.clear();
    highlightLinks.clear();
    searchMatchingNodes.clear();
    focusedNode = null;

    let sumX = 0, sumY = 0, sumZ = 0;
    let validCount = 0;

    nodesInCluster.forEach(n => {
        searchMatchingNodes.add(n.id);
        if (typeof n.x === 'number') {
            sumX += n.x; sumY += n.y; sumZ += n.z;
            validCount++;
        }
    });

    if (validCount > 0) {
        const cx = sumX / validCount;
        const cy = sumY / validCount;
        const cz = sumZ / validCount;

        const distance = 500;
        const distRatio = 1 + distance / Math.hypot(cx, cy, cz);
        Graph.cameraPosition(
            { x: cx === 0 ? 0 : cx * distRatio, y: cy === 0 ? 0 : cy * distRatio, z: cz === 0 ? distance : cz * distRatio },
            { x: cx, y: cy, z: cz },
            1200
        );
    }

    animateToSelection(0.85);

    document.getElementById('panel-title').innerText = `CLUSTER / SUBSYSTEM`;
    document.getElementById('node-details').innerHTML = `
        <div class="property"><span class="prop-title">SUBSYSTEM DOMAIN</span><strong style="color: var(--hud-cyan); font-size: 16px;">${clusterName}</strong></div>
        <div class="property"><span class="prop-title">COMPONENTS DETECTED</span><span style="color: #fff; font-weight: 600; font-size: 14px;">${validCount}</span></div>
        <div style="margin-top: 15px; padding: 10px; border-left: 2px solid var(--hud-cyan); background: rgba(0, 240, 255, 0.05); color: #94a3b8; font-size: 12px; font-style: italic;">
            Showing all components encapsulated in this subsystem. Click any individual node to inspect its specific properties, or press ESC to view the entire universe.
        </div>
    `;
    document.getElementById('doc-details').innerHTML = `<p style="color: #64748b; font-style: italic; font-size: 13px;">No architectural documentation available for entire cluster.</p>`;
    document.getElementById('raw-details').innerHTML = `<p style="color: #64748b; font-style: italic; font-size: 13px;">N/A</p>`;
    switchTab('specs', document.querySelectorAll('.tab-btn')[0]);
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

function normalizeSubsystemName(node) {
    if (!node) return 'CORE';

    const raw = String(node.subsystem || node.group || 'CORE').trim();
    if (!raw) return 'CORE';

    const normalized = raw.toUpperCase();
    if (['CORE', 'THIS', 'INDEX', 'DOCUMENT', 'UUID', 'VEC3', 'NAVIGATOR', 'ENGINE'].includes(normalized)) {
        return 'CORE';
    }

    if (node.group === 'External/Dependency' && node.id) {
        const parts = String(node.id).split('/').filter(Boolean);
        if (parts.length > 1 && parts[0] && parts[0].toUpperCase() !== 'SRC') {
            return parts[0].toUpperCase();
        }
    }

    return normalized;
}

function buildClusterGroups(nodes) {
    clusterGroups = {};
    const grouped = {};

    nodes.forEach(node => {
        const normalizedSubsystem = normalizeSubsystemName(node);
        node.subsystem = normalizedSubsystem;

        if (!grouped[normalizedSubsystem]) {
            grouped[normalizedSubsystem] = [];
        }
        grouped[normalizedSubsystem].push(node);
    });

    const minClusterSize = 2;
    Object.entries(grouped).forEach(([name, items]) => {
        if (items.length >= minClusterSize) {
            clusterGroups[name] = items;
            return;
        }

        let bucket = 'CORE';
        const firstNodeId = items[0] && items[0].id ? String(items[0].id) : '';
        const parts = firstNodeId.split('/').filter(Boolean);
        if (parts.length > 1 && parts[0] && parts[0].toUpperCase() !== 'SRC') {
            bucket = parts[0].toUpperCase();
        }

        if (!clusterGroups[bucket]) {
            clusterGroups[bucket] = [];
        }
        clusterGroups[bucket].push(...items);
    });

    const groupKeys = Object.keys(clusterGroups);
    const radius = 600;
    groupKeys.forEach((key, idx) => {
        const angle = (2 * Math.PI * idx) / groupKeys.length;
        clusterGroups[key].targetCenter = {
            x: radius * Math.cos(angle),
            y: (idx % 2 === 0 ? 1 : -1) * 120,
            z: radius * Math.sin(angle)
        };
    });
}

function applyGraphPhysicsState() {
    if (!Graph || !graphDataGlobal) return;

    const hasSelection = !!focusedNode || selectionIntensity > 0.2 || searchMatchingNodes.size > 0;
    const clusterAlpha = hasSelection ? 0.008 : 0.08;
    const stopRadius = hasSelection ? 450 : 350;

    Graph.d3Force('cluster', () => {
        graphDataGlobal.nodes.forEach(node => {
            const grp = clusterGroups[node.subsystem];
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

    Graph.d3Force('link')
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

    Graph.d3Force('charge').strength(hasSelection ? -150 : -280);
}

function animateToSelection(targetValue) {
    if (animFrameId) cancelAnimationFrame(animFrameId);
    const startVal = selectionIntensity;
    const delta = targetValue - startVal;
    const startTime = performance.now();
    const duration = 400;

    function step(now) {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / duration);
        const eased = easeOutCubic(progress);

        selectionIntensity = startVal + delta * eased;
        applyGraphPhysicsState();

        Graph.nodeColor(Graph.nodeColor())
            .linkColor(Graph.linkColor())
            .linkWidth(Graph.linkWidth());

        if (progress < 1) {
            animFrameId = requestAnimationFrame(step);
        } else {
            selectionIntensity = targetValue;
            applyGraphPhysicsState();
        }
    }
    animFrameId = requestAnimationFrame(step);
}

function clearSelection() {
    if (highlightNodes.size === 0 && selectionIntensity === 0.0 && searchMatchingNodes.size === 0) return;

    focusedNode = null;
    highlightNodes.clear();
    highlightLinks.clear();
    searchMatchingNodes.clear();
    animateToSelection(0.0);
    applyGraphPhysicsState();

    const container = document.getElementById('hud-labels-layer');
    container.querySelectorAll('.hud-floating-pill').forEach(el => el.remove());

    document.getElementById('panel-title').innerText = 'COMPONENT INSPECTOR';
    document.getElementById('node-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">Select a node in the graph to view technical specifications and memory context.</p>';
    document.getElementById('doc-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">No architectural documentation found for this node.</p>';
    document.getElementById('raw-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">Documentation stream unavailable.</p>';
}

function syncFloatingLabels() {
    const container = document.getElementById('hud-labels-layer');
    if (!Graph || !graphDataGlobal) {
        requestAnimationFrame(syncFloatingLabels);
        return;
    }

    const showClusters = (selectionIntensity < 0.6 && searchMatchingNodes.size === 0);
    const clusterOpacity = Math.max(0, 1 - selectionIntensity * 1.8);

    Object.entries(clusterGroups).forEach(([name, grp]) => {
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

        const screenPos = Graph.graph2ScreenCoords(avgX, avgY, avgZ);
        const safeKey = 'cluster-' + btoa(name).replace(/=/g, '');
        let badge = document.getElementById(safeKey);

        if (!badge) {
            badge = document.createElement('div');
            badge.id = safeKey;
            badge.className = 'hud-cluster-badge';
            badge.innerHTML = `${name} <span>[${validCount}]</span>`;

            badge.onclick = () => focusCluster(name);

            container.appendChild(badge);
        }

        badge.style.left = `${screenPos.x}px`;
        badge.style.top = `${screenPos.y}px`;
        badge.style.opacity = showClusters ? clusterOpacity.toFixed(2) : '0';
        badge.style.pointerEvents = showClusters ? 'auto' : 'none';
    });

    const activeNodeSet = highlightNodes.size > 0 ? highlightNodes : (searchMatchingNodes.size > 0 ? searchMatchingNodes : null);

    const existingPills = container.querySelectorAll('.hud-floating-pill');
    existingPills.forEach(pill => {
        const nodeId = pill.dataset.nodeId;
        if (!activeNodeSet || !activeNodeSet.has(nodeId)) {
            pill.remove();
        }
    });

    if (activeNodeSet) {
        activeNodeSet.forEach(nodeId => {
            const node = graphDataGlobal.nodes.find(n => n.id === nodeId);
            if (!node || typeof node.x !== 'number') return;

            const screenPos = Graph.graph2ScreenCoords(node.x, node.y, node.z);
            const pillId = 'pill-' + btoa(node.id).replace(/=/g, '');
            let pill = document.getElementById(pillId);

            if (!pill) {
                pill = document.createElement('div');
                pill.id = pillId;
                pill.dataset.nodeId = node.id;
                pill.className = 'hud-floating-pill' + (focusedNode && focusedNode.id === node.id ? ' is-target' : '');
                pill.innerText = node.name || node.id.split('/').pop().split('#').pop();
                container.appendChild(pill);
            } else {
                const isTarget = (focusedNode && focusedNode.id === node.id);
                pill.classList.toggle('is-target', isTarget);
            }

            pill.style.left = `${screenPos.x}px`;
            pill.style.top = `${screenPos.y - 14}px`;
            pill.style.opacity = (0.2 + 0.8 * selectionIntensity).toFixed(2);
        });
    }

    requestAnimationFrame(syncFloatingLabels);
}

const searchInput = document.getElementById('hud-search-input');
const searchResults = document.getElementById('hud-search-results');

function setupSearchSystem() {
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (!query) {
            searchResults.style.display = 'none';
            searchMatchingNodes.clear();
            if (highlightNodes.size === 0) {
                animateToSelection(0.0);
            }
            return;
        }

        const matches = graphDataGlobal.nodes.filter(n => {
            const idMatch = (n.id || '').toLowerCase().includes(query);
            const nameMatch = (n.name || '').toLowerCase().includes(query);
            const groupMatch = (n.group || '').toLowerCase().includes(query);
            const subMatch = (n.subsystem || '').toLowerCase().includes(query);
            const summaryMatch = (n.semantic_summary || '').toLowerCase().includes(query);
            const keywordMatch = (n.keywords || []).some(k => k.toLowerCase().includes(query));
            return idMatch || nameMatch || groupMatch || subMatch || summaryMatch || keywordMatch;
        });

        searchMatchingNodes.clear();
        matches.forEach(m => searchMatchingNodes.add(m.id));
        if (highlightNodes.size === 0) {
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
                clearSelection();
            }
        }
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
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
            searchMatchingNodes.clear();
            focusNodeById(node.id);
        });

        searchResults.appendChild(item);
    });

    searchResults.style.display = 'flex';
}

const isStaticHost = window.location.pathname.endsWith('.html') || window.location.protocol === 'file:';
const primaryUrl = isStaticHost ? './data.json' : 'data.json';

fetch(primaryUrl)
    .then(res => {
        if (!res.ok) throw new Error('data.json not found, falling back to /api/data');
        return res.json();
    })
    .catch(() => fetch('/api/data').then(res => res.json()))
    .then(data => {
        graphDataGlobal = data;

        document.getElementById('stat-nodes').innerText = data.nodes.length;
        document.getElementById('stat-edges').innerText = data.links.length;

        buildClusterGroups(data.nodes);
        setupSearchSystem();

        const elem = document.getElementById('3d-graph');
        Graph = ForceGraph3D()(elem)
            .graphData(data)
            .backgroundColor('#030a13')
            .warmupTicks(0)
            .cooldownTime(18000)
            .d3VelocityDecay(0.85)
            .d3AlphaDecay(0.005)
            .nodeLabel(node => `
                <div style="background: rgba(2, 16, 32, 0.95); border: 1px solid #00f0ff; border-left: 3px solid #00f0ff; padding: 8px 12px; font-family: 'Inter', sans-serif; box-shadow: 0 0 15px rgba(0, 240, 255, 0.4);">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; color: #00f0ff; letter-spacing: 0.5px;">${node.name || node.id}</div>
                    <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin-top: 3px;">SUBSYSTEM: <span style="color: #fff; font-weight: 600;">${node.subsystem}</span> // TYPE: <span style="color: var(--hud-cyan); font-weight: 600;">${node.group}</span></div>
                </div>
            `)
            .nodeColor(node => {
                const base = getNodeBaseColor(node);
                if (selectionIntensity === 0.0) {
                    return `rgb(${base.r}, ${base.g}, ${base.b})`;
                }

                if (searchMatchingNodes.size > 0) {
                    if (searchMatchingNodes.has(node.id)) {
                        return '#00f0ff';
                    }
                    const dimAlpha = 1.0 - (1.0 - 0.15) * selectionIntensity;
                    return `rgba(${base.r}, ${base.g}, ${base.b}, ${dimAlpha.toFixed(3)})`;
                }

                if (highlightNodes.has(node.id)) {
                    return `rgb(${base.r}, ${base.g}, ${base.b})`;
                }
                const dimAlpha = 1.0 - (1.0 - 0.22) * selectionIntensity;
                return `rgba(${base.r}, ${base.g}, ${base.b}, ${dimAlpha.toFixed(3)})`;
            })
            .nodeVal(node => {
                if (searchMatchingNodes.size > 0 && searchMatchingNodes.has(node.id)) {
                    return 12;
                }
                return node.group === 'module' ? 8 : 3.8;
            })
            .nodeResolution(18)
            .linkColor(link => {
                const base = getLinkBaseColor(link);

                if (selectionIntensity === 0.0) {
                    return `rgba(${base.r}, ${base.g}, ${base.b}, 0.25)`;
                }
                if (highlightLinks.has(link)) {
                    const alpha = 0.25 + (0.9 - 0.25) * selectionIntensity;
                    return `rgba(${base.r}, ${base.g}, ${base.b}, ${alpha.toFixed(3)})`;
                }
                const alpha = 0.25 - (0.25 - 0.04) * selectionIntensity;
                return `rgba(30, 41, 59, ${alpha.toFixed(3)})`;
            })
            .linkWidth(link => {
                if (selectionIntensity > 0 && highlightLinks.has(link)) {
                    return 0.8 + (2.0 - 0.8) * selectionIntensity;
                }
                return 0.8;
            })
            .linkDirectionalParticles(link => {
                if (selectionIntensity === 0.0) return 2;
                return highlightLinks.has(link) ? 4 : 0;
            })
            .linkDirectionalParticleColor(link => {
                const base = getLinkBaseColor(link);
                return `rgb(${base.r}, ${base.g}, ${base.b})`;
            })
            .linkDirectionalParticleWidth(link => highlightLinks.has(link) ? 2.5 : 1.5)
            .linkDirectionalParticleSpeed(link => {
                const baseSpeed = highlightLinks.has(link) ? 0.012 : 0.005;
                const rel = (link.relation || '').toLowerCase();

                if (rel === 'imports') {
                    return -baseSpeed;
                }
                return baseSpeed;
            })
            .onNodeClick(node => {
                highlightNodes.clear();
                highlightLinks.clear();
                searchMatchingNodes.clear();

                const container = document.getElementById('hud-labels-layer');
                container.querySelectorAll('.hud-floating-pill').forEach(el => el.remove());

                const neighborPills = [];

                if (node) {
                    focusedNode = node;
                    highlightNodes.add(node.id);
                    applyGraphPhysicsState();

                    graphDataGlobal.links.forEach(link => {
                        const sId = typeof link.source === 'object' ? link.source.id : link.source;
                        const tId = typeof link.target === 'object' ? link.target.id : link.target;
                        if (sId === node.id || tId === node.id) {
                            highlightLinks.add(link);
                            highlightNodes.add(sId);
                            highlightNodes.add(tId);

                            const isOut = (sId === node.id);
                            const otherId = isOut ? tId : sId;
                            const otherName = otherId.split('#').pop().split('/').pop();
                            const rel = link.relation || (isOut ? 'targets' : 'source');
                            neighborPills.push({ id: otherId, name: otherName, relation: rel, dir: isOut ? '→' : '←' });
                        }
                    });

                    const distance = 320;
                    const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
                    Graph.cameraPosition(
                        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                        node,
                        1200
                    );

                    animateToSelection(1.0);
                }

                document.getElementById('panel-title').innerText = node.name || 'COMPONENT';

                let specsHtml = `<div class="property"><span class="prop-title">IDENTIFIER / PATH</span><strong style="color: #fff; word-break: break-all; font-family: 'JetBrains Mono', monospace; font-size: 11px;">${node.id}</strong></div>`;
                specsHtml += `<div class="property"><span class="prop-title">SUBSYSTEM CLUSTER</span><span style="color: var(--hud-cyan); font-weight: 600;">${node.subsystem}</span></div>`;
                specsHtml += `<div class="property"><span class="prop-title">COMPONENT TYPE</span><span style="color: #93c5fd; font-weight: 600;">${node.group}</span></div>`;

                if (node.signature) {
                    specsHtml += `<div class="property"><span class="prop-title">SIGNATURE</span><div class="signature-box">${node.signature}</div></div>`;
                }

                if (node.semantic_summary) {
                    specsHtml += `<div class="property"><span class="prop-title">SEMANTIC SUMMARY</span><div class="value-box">${node.semantic_summary}</div></div>`;
                }

                if (neighborPills.length > 0) {
                    specsHtml += `<div class="property"><span class="prop-title">CONNECTED GRAPH RELATIONS (${neighborPills.length})</span>`;
                    specsHtml += `<div class="pill-list">`;
                    neighborPills.forEach(p => {
                        specsHtml += `
                            <div class="pill-item" onclick="focusNodeById('${p.id}')">
                                <span style="color: #e2e8f0;">${p.dir} ${p.name}</span>
                                <span class="pill-relation">${p.relation}</span>
                            </div>
                        `;
                    });
                    specsHtml += `</div></div>`;
                }

                if (node.keywords && node.keywords.length > 0) {
                    specsHtml += `<div class="property"><span class="prop-title">KEYWORDS</span><div class="tag-container">${node.keywords.map(kw => `<span class="tag">${kw}</span>`).join('')}</div></div>`;
                }

                document.getElementById('node-details').innerHTML = specsHtml;

                let docHtml = '';
                if (node.human_overview) {
                    docHtml += `<div class="property"><span class="prop-title">OVERVIEW & PURPOSE</span><div class="value-box" style="border-left: 2px solid var(--hud-cyan);">${node.human_overview}</div></div>`;
                }
                if (node.side_effects) {
                    docHtml += `<div class="property"><span class="prop-title">SIDE EFFECTS & BEHAVIOR</span><div class="value-box" style="border-left: 2px solid var(--hud-red); color: #fca5a5;">${node.side_effects}</div></div>`;
                }
                if (!node.human_overview && !node.side_effects) {
                    docHtml = `<p style="color: #64748b; font-style: italic; font-size: 13px;">No architectural documentation found for this component.</p>`;
                }
                document.getElementById('doc-details').innerHTML = docHtml;

                if (node.raw_markdown && typeof marked !== 'undefined') {
                    document.getElementById('raw-details').innerHTML = `<div class="markdown-rendered">${marked.parse(node.raw_markdown)}</div>`;
                } else if (node.raw_markdown) {
                    document.getElementById('raw-details').innerText = node.raw_markdown;
                } else {
                    document.getElementById('raw-details').innerHTML = `<p style="color: #64748b; font-style: italic; font-size: 13px;">No documentation file linked to this component.</p>`;
                }
            })
            .onBackgroundClick(() => {
                clearSelection();
            });

        applyGraphPhysicsState();

        resetCamera();
        syncFloatingLabels();
    });
