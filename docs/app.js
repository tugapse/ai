const isStaticHost = window.location.pathname.endsWith('.html') || window.location.protocol === 'file:';
const primaryUrl = isStaticHost ? './data.json' : 'data.json';

function canonicalizeNodeReference(value) {
    if (!value) return '';
    let clean = String(value).split('#')[0].split('::')[0].trim();
    clean = clean.replace(/\\/g, '/');
    clean = clean.replace(/^https?:\/\/[^/]+/i, '');
    clean = clean.replace(/^\/+/, '');
    clean = clean.replace(/^\.?\.?\//, '');
    clean = clean.replace(/\.(py|json|md)$/i, '');
    clean = clean.replace(/\/index$/, '');
    if (clean.startsWith('src/')) clean = clean.slice(4);
    if (clean.startsWith('AgentDocs/')) clean = clean.slice('AgentDocs/'.length);
    if (clean.startsWith('KnowledgeGraph/')) clean = clean.slice('KnowledgeGraph/'.length);
    clean = clean.replace(/\.(?=[A-Za-z0-9])/g, '/');
    clean = clean.replace(/\s+/g, '');
    clean = clean.replace(/(^|\/)(__init__|index)$/, '$1');
    clean = clean.replace(/\/+/g, '/');
    return clean.replace(/^\//, '').replace(/\/$/, '');
}

function resolveMarkdownLinkTarget(href, text) {
    if (!window.graphDataGlobal || !Array.isArray(window.graphDataGlobal.nodes)) return null;

    const refs = [];
    if (href) refs.push(href);
    if (text) refs.push(text);

    const normalizedRefs = refs
        .map(value => canonicalizeNodeReference(value))
        .filter(Boolean)
        .map(value => value.toLowerCase());

    const anchorText = (text || '').trim();
    const anchorWordSet = anchorText
        ? anchorText.toLowerCase().replace(/[_\-\s]+/g, '').split(/[^A-Za-z0-9]+/).filter(Boolean)
        : [];

    for (const node of window.graphDataGlobal.nodes) {
        const nodeId = String(node.id || '').toLowerCase();
        const nodeName = String(node.name || node.id || '').toLowerCase();
        const idBasename = nodeId.split('/').pop();
        const nameBasename = nodeName.split('/').pop();

        const matches = normalizedRefs.some(ref => {
            if (!ref) return false;
            if (ref === nodeId || ref === nodeName) return true;
            if (ref === idBasename || ref === nameBasename) return true;
            if (ref.endsWith('/' + nodeId) || ref.endsWith('/' + idBasename)) return true;
            if (nodeId.includes(ref) || nodeName.includes(ref)) return true;
            return false;
        });

        if (matches) return node;

        const nameMatchesText = anchorText && (
            nodeName.includes(anchorText.toLowerCase()) ||
            nodeId.includes(anchorText.toLowerCase()) ||
            anchorWordSet.some(word => nodeName.includes(word) || idBasename.includes(word))
        );
        if (nameMatchesText) return node;
    }

    return null;
}

function bindMarkdownLinkHandlers(container) {
    if (!container) return;

    container.querySelectorAll('a').forEach(anchor => {
        anchor.setAttribute('target', '_self');
        anchor.addEventListener('click', (event) => {
            const href = anchor.getAttribute('href') || '';
            const text = anchor.textContent || '';
            const match = resolveMarkdownLinkTarget(href, text);

            if (match) {
                event.preventDefault();
                event.stopPropagation();
                focusNodeById(match.id);
            }
        });
    });
}

function resetInspectorScroll() {
    const panel = document.getElementById('info-panel');
    if (panel) panel.scrollTop = 0;
}

function cameraPositionForInspector(node, distance) {
    if (!node || !window.Graph) return;

    const panel = document.getElementById('info-panel');
    const inspectorOpen = panel && !panel.classList.contains('is-collapsed');
    const panelWidth = inspectorOpen ? Math.min(panel.offsetWidth || 420, 560) : 0;
    const horizontalShift = inspectorOpen ? -(panelWidth * 1.35) : 0;
    const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
    const cameraPos = {
        x: node.x * distRatio + horizontalShift,
        y: node.y * distRatio,
        z: node.z * distRatio
    };
    const targetPos = {
        x: node.x + horizontalShift * 0.15,
        y: node.y,
        z: node.z
    };

    window.Graph.cameraPosition(cameraPos, targetPos, 1200);
}

fetch(primaryUrl)
    .then(res => {
        if (!res.ok) throw new Error('data.json not found, falling back to /api/data');
        return res.json();
    })
    .catch(() => fetch('/api/data').then(res => res.json()))
    .then(data => {
        window.graphDataGlobal = data;

        document.getElementById('stat-nodes').innerText = data.nodes.length;
        document.getElementById('stat-edges').innerText = data.links.length;

        buildClusterGroups(data.nodes);
        setupSearchSystem();
        setInspectorCollapsed(true);

        const elem = document.getElementById('3d-graph');
        const updateGraphViewport = () => {
            if (!window.Graph) return;

            const width = window.innerWidth;
            const height = window.innerHeight;

            window.Graph.width(width).height(height);

            const renderer = window.Graph.renderer && window.Graph.renderer();
            if (renderer && typeof renderer.setSize === 'function') {
                renderer.setSize(width, height);
            }

            const camera = window.Graph.camera();
            if (camera && typeof camera.aspect === 'number') {
                camera.aspect = width / height;
                camera.updateProjectionMatrix();
            }
        };

        let resizeFrameId = null;
        const scheduleGraphViewportUpdate = () => {
            if (resizeFrameId) cancelAnimationFrame(resizeFrameId);
            resizeFrameId = requestAnimationFrame(updateGraphViewport);
        };

        window.handleNodeSelection = (node, options = {}) => {
            recordInspectorSelection(node, options);

            window.highlightNodes.clear();
            window.highlightLinks.clear();
            window.searchMatchingNodes.clear();
            resetInspectorScroll();

            const container = document.getElementById('hud-labels-layer');
            container.querySelectorAll('.hud-floating-pill').forEach(el => el.remove());

            const neighborPills = [];

            if (node) {
                window.focusedNode = node;
                window.highlightNodes.add(node.id);
                applyGraphPhysicsState();

                window.graphDataGlobal.links.forEach(link => {
                    const sId = typeof link.source === 'object' ? link.source.id : link.source;
                    const tId = typeof link.target === 'object' ? link.target.id : link.target;
                    if (sId === node.id || tId === node.id) {
                        window.highlightLinks.add(link);
                        window.highlightNodes.add(sId);
                        window.highlightNodes.add(tId);

                        const isOut = (sId === node.id);
                        const otherId = isOut ? tId : sId;
                        const otherName = otherId.split('#').pop().split('/').pop();
                        const rel = link.relation || (isOut ? 'targets' : 'source');
                        neighborPills.push({ id: otherId, name: otherName, relation: rel, dir: isOut ? '→' : '←' });
                    }
                });

                const distance = 320;
                cameraPositionForInspector(node, distance);
                animateToSelection(1.0);
            }

            setInspectorCollapsed(false);
            resetInspectorScroll();
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
                specsHtml += '<div class="pill-list">';
                neighborPills.forEach(p => {
                    specsHtml += `
                        <div class="pill-item" data-node-id="${String(p.id).replace(/"/g, '&quot;')}">
                            <span style="color: #e2e8f0;">${p.dir} ${p.name}</span>
                            <span class="pill-relation">${p.relation}</span>
                        </div>
                    `;
                });
                specsHtml += '</div></div>';
            }

            if (node.keywords && node.keywords.length > 0) {
                specsHtml += `<div class="property"><span class="prop-title">KEYWORDS</span><div class="tag-container">${node.keywords.map(kw => `<span class="tag">${kw}</span>`).join('')}</div></div>`;
            }

            document.getElementById('node-details').innerHTML = specsHtml;
            document.querySelectorAll('.pill-item[data-node-id]').forEach((pill) => {
                pill.addEventListener('click', (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    const nodeId = pill.getAttribute('data-node-id');
                    if (nodeId) {
                        focusNodeById(nodeId);
                    }
                });
            });

            let docHtml = '';
            if (node.human_overview) {
                docHtml += `<div class="property"><span class="prop-title">OVERVIEW & PURPOSE</span><div class="value-box" style="border-left: 2px solid var(--hud-cyan);">${node.human_overview}</div></div>`;
            }
            if (node.side_effects) {
                docHtml += `<div class="property"><span class="prop-title">SIDE EFFECTS & BEHAVIOR</span><div class="value-box" style="border-left: 2px solid var(--hud-red); color: #fca5a5;">${node.side_effects}</div></div>`;
            }
            if (!node.human_overview && !node.side_effects) {
                docHtml = '<p style="color: #64748b; font-style: italic; font-size: 13px;">No architectural documentation found for this component.</p>';
            }
            document.getElementById('doc-details').innerHTML = docHtml;

            if (node.raw_markdown && typeof marked !== 'undefined') {
                const rawDetails = document.getElementById('raw-details');
                rawDetails.innerHTML = `<div class="markdown-rendered">${marked.parse(node.raw_markdown)}</div>`;
                bindMarkdownLinkHandlers(rawDetails);
            } else if (node.raw_markdown) {
                const rawDetails = document.getElementById('raw-details');
                rawDetails.innerText = node.raw_markdown;
                bindMarkdownLinkHandlers(rawDetails);
            } else {
                document.getElementById('raw-details').innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 13px;">No documentation file linked to this component.</p>';
            }
        };

        window.Graph = ForceGraph3D()(elem)
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
                if (window.selectionIntensity === 0.0) {
                    return `rgb(${base.r}, ${base.g}, ${base.b})`;
                }

                if (window.searchMatchingNodes.size > 0) {
                    if (window.searchMatchingNodes.has(node.id)) {
                        return '#00f0ff';
                    }
                    const dimAlpha = 1.0 - (1.0 - 0.15) * window.selectionIntensity;
                    return `rgba(${base.r}, ${base.g}, ${base.b}, ${dimAlpha.toFixed(3)})`;
                }

                if (window.highlightNodes.has(node.id)) {
                    return `rgb(${base.r}, ${base.g}, ${base.b})`;
                }
                const dimAlpha = 1.0 - (1.0 - 0.22) * window.selectionIntensity;
                return `rgba(${base.r}, ${base.g}, ${base.b}, ${dimAlpha.toFixed(3)})`;
            })
            .nodeVal(node => {
                if (window.searchMatchingNodes.size > 0 && window.searchMatchingNodes.has(node.id)) {
                    return 12;
                }
                return node.group === 'module' ? 8 : 3.8;
            })
            .nodeResolution(18)
            .linkColor(link => {
                const base = getLinkBaseColor(link);

                if (window.selectionIntensity === 0.0) {
                    return `rgba(${base.r}, ${base.g}, ${base.b}, 0.25)`;
                }
                if (window.highlightLinks.has(link)) {
                    const alpha = 0.25 + (0.9 - 0.25) * window.selectionIntensity;
                    return `rgba(${base.r}, ${base.g}, ${base.b}, ${alpha.toFixed(3)})`;
                }
                const alpha = 0.25 - (0.25 - 0.04) * window.selectionIntensity;
                return `rgba(30, 41, 59, ${alpha.toFixed(3)})`;
            })
            .linkWidth(link => {
                if (window.selectionIntensity > 0 && window.highlightLinks.has(link)) {
                    return 0.8 + (2.0 - 0.8) * window.selectionIntensity;
                }
                return 0.8;
            })
            .linkDirectionalParticles(link => {
                if (window.selectionIntensity === 0.0) return 2;
                return window.highlightLinks.has(link) ? 4 : 0;
            })
            .linkDirectionalParticleColor(link => {
                const base = getLinkBaseColor(link);
                return `rgb(${base.r}, ${base.g}, ${base.b})`;
            })
            .linkDirectionalParticleWidth(link => window.highlightLinks.has(link) ? 2.5 : 1.5)
            .linkDirectionalParticleSpeed(link => {
                const baseSpeed = window.highlightLinks.has(link) ? 0.012 : 0.005;
                const rel = (link.relation || '').toLowerCase();
                if (rel === 'imports') {
                    return -baseSpeed;
                }
                return baseSpeed;
            })
            .onNodeClick(window.handleNodeSelection)
            .onBackgroundClick(() => {
                hideInspectorAndSelection();
            });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                hideInspectorAndSelection();
            }
        });

        document.addEventListener('click', (event) => {
            const target = event.target;
            if (!target) return;

            const clickedInsidePanel = target.closest('#info-panel');
            const clickedInsideGraph = target.closest('[id="3d-graph"]');
            const clickedOnSearchField = target.closest('#hud-search-input') || target.closest('#hud-search-results');
            const clickedOnClusterBadge = target.closest('.hud-cluster-badge');
            const clickedOnFloatingLabel = target.closest('.hud-floating-pill');
            const clickedOnNodeLabel = target.closest('.node-label');
            const clickedOnLabelLayer = target.closest('#hud-labels-layer');
            const clickedOnGraphLabel = target.closest('.label') || target.closest('[class*="label"]');
            const clickedOnCanvasText = target.closest('canvas') === null && clickedOnGraphLabel;

            if (!clickedInsidePanel && !clickedInsideGraph && !clickedOnSearchField && !clickedOnClusterBadge && !clickedOnFloatingLabel && !clickedOnNodeLabel && !clickedOnLabelLayer && !clickedOnCanvasText) {
                hideInspectorAndSelection();
            }
        });

        window.addEventListener('resize', scheduleGraphViewportUpdate);
        window.onresize = scheduleGraphViewportUpdate;
        updateGraphViewport();

        applyGraphPhysicsState();
        resetCamera();
        syncFloatingLabels();
    });
