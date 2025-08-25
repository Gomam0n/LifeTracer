// LifeTracer 前端应用主要逻辑
// 自动获取当前主机地址，支持前后端一体化部署
const API_BASE_URL = window.location.origin;

/**
 * 获取人物生平轨迹数据
 */
async function getLifeTrajectory() {
    const personName = document.getElementById('personName').value.trim();
    
    if (!personName) {
        showError(i18n.t('error.invalidInput'));
        return;
    }
    
    // 隐藏上一次的搜索结果和地图
    hideError();
    hideResult();
    hideMapSection();
    
    // 显示动态加载效果
    showDynamicLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/biography`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: personName
            })
        });
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('NOT_FOUND');
            } else if (response.status === 400) {
                throw new Error('VALIDATION_ERROR');
            } else if (response.status >= 500) {
                throw new Error('SERVER_ERROR');
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        }
        
        const data = await response.json();
        displayLifeTrajectoryData(data);
        
    } catch (error) {
        console.error('Error:', error);
        
        let errorMessage;
        switch (error.message) {
            case 'NOT_FOUND':
                errorMessage = i18n.t('error.notFound');
                break;
            case 'VALIDATION_ERROR':
                errorMessage = i18n.t('error.validation');
                break;
            case 'SERVER_ERROR':
                errorMessage = i18n.t('error.server');
                break;
            default:
                if (error.name === 'TypeError') {
                    errorMessage = i18n.t('error.network');
                } else {
                    errorMessage = i18n.t('error.unknown');
                }
        }
        
        showError(errorMessage);
    } finally {
        showDynamicLoading(false);
    }
}

/**
 * 显示生平轨迹数据
 * @param {Object} data - API返回的数据
 */
function displayLifeTrajectoryData(data) {
    if (data.success && data.data) {
        const biography = data.data;
        
        // 直接显示地图区域，不显示结果文本
        showMapSection();
        
        // 初始化地图（如果还未初始化）并显示轨迹
        if (biography.coordinates && biography.coordinates.length > 0) {
            // 确保地图容器可见后再初始化
            setTimeout(() => {
                if (!mapInitialized) {
                    const success = initLifeTracerMap('map');
                    if (success) {
                        mapInitialized = true;
                        // 再次延迟以确保地图完全初始化
                        setTimeout(() => {
                            showTrajectoryOnMap(biography);
                        }, 200);
                    }
                } else {
                    showTrajectoryOnMap(biography);
                }
            }, 100);
        }
    } else {
        showError(data.message || i18n.t('error.unknown'));
    }
}


/**
 * 显示/隐藏动态加载效果
 * @param {boolean} show - 是否显示动态加载效果
 */
function showDynamicLoading(show) {
    const loadingContainer = document.getElementById('loading-container');
    if (loadingContainer) {
        loadingContainer.style.display = show ? 'block' : 'none';
    }
}

/**
 * 显示错误信息
 * @param {string} message - 错误信息
 */
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.querySelector('span').textContent = message;
    errorDiv.style.display = 'block';
}

/**
 * 隐藏错误信息
 */
function hideError() {
    document.getElementById('error').style.display = 'none';
}

/**
 * 显示结果区域
 */
function showResult() {
    document.getElementById('result').style.display = 'block';
}

/**
 * 隐藏结果区域
 */
function hideResult() {
    document.getElementById('result').style.display = 'none';
}

/**
 * 显示地图区域
 */
function showMapSection() {
    document.getElementById('mapSection').style.display = 'block';
}

/**
 * 隐藏地图区域
 */
function hideMapSection() {
    document.getElementById('mapSection').style.display = 'none';
}

/**
 * 语言切换回调函数
 * @param {Object} detail - 语言切换事件详情
 */
window.onLanguageChanged = function(detail) {
    console.log('应用收到语言切换事件:', detail.language);
    
    // 更新输入框占位符
    const personNameInput = document.getElementById('personName');
    personNameInput.placeholder = i18n.t('input.placeholder');
    
    // 如果有错误信息显示，更新错误信息
    const errorDiv = document.getElementById('error');
    if (errorDiv.style.display !== 'none') {
        // 保持当前错误状态，但不更新文本，因为具体错误信息需要重新获取
    }
    
    // 如果地图已初始化，更新地图相关文本
    if (mapInitialized && window.lifeTracerMap) {
        // 地图文本更新将由map.js处理
    }
};

/**
 * 初始化事件监听器
 */
function initEventListeners() {
    // 支持回车键提交
    document.getElementById('personName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            getLifeTrajectory();
        }
    });
}

// DOM加载完成后初始化
window.addEventListener('load', function () {
    initEventListeners();
    // 地图将在显示结果时初始化，而不是在页面加载时
});

// 地图初始化标志
let mapInitialized = false;

// 切换坐标点详细信息显示/隐藏
function toggleStats() {
    const statsDiv = document.getElementById('mapStats');
    const toggleBtn = document.getElementById('statsToggleBtn');
    
    if (statsDiv.style.display === 'none' || statsDiv.style.display === '') {
        // 显示坐标点详细信息
        displayCoordinateDetails();
        statsDiv.style.display = 'block';
        toggleBtn.classList.add('active');
        toggleBtn.setAttribute('data-i18n', 'map.hide_stats');
        // 更新按钮文本
        const hideText = i18n.t('map.hide_stats');
        toggleBtn.textContent = hideText;
    } else {
        statsDiv.style.display = 'none';
        toggleBtn.classList.remove('active');
        toggleBtn.setAttribute('data-i18n', 'map.toggle_stats');
        // 更新按钮文本
        const showText = i18n.t('map.toggle_stats');
        toggleBtn.textContent = showText;
    }
}

// 计算两点间距离（单位：公里）
function calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // 地球半径（公里）
    const dLat = deg2rad(lat2 - lat1);
    const dLng = deg2rad(lng2 - lng1);
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// 角度转弧度
function deg2rad(deg) {
    return deg * (Math.PI/180);
}

// 显示坐标点详细信息
function displayCoordinateDetails() {
    const statsContainer = document.getElementById('statsContent');
    if (!statsContainer || !lifeTracerMap || !lifeTracerMap.currentData) {
        return;
    }
    
    const data = lifeTracerMap.currentData;
    const coordinates = data.coordinates;
    const descriptions = data.descriptions;
    
    // 计算总距离
    let totalDistance = 0;
    for (let i = 0; i < coordinates.length - 1; i++) {
        const [lng1, lat1] = coordinates[i];
        const [lng2, lat2] = coordinates[i + 1];
        totalDistance += calculateDistance(lat1, lng1, lat2, lng2);
    }
    
    const title = i18n.t('map.coordinate_details');
    const totalPointsLabel = i18n.t('map.total_points');
    const totalDistanceLabel = i18n.t('map.total_distance');
    
    let html = `<h4>${title}</h4>`;
    
    // 添加统计信息
    html += `
        <div class="trajectory-stats">
            <div class="stats-item">
                <span class="stats-label">${totalPointsLabel}:</span>
                <span class="stats-value">${coordinates.length}</span>
            </div>
            <div class="stats-item">
                <span class="stats-label">${totalDistanceLabel}:</span>
                <span class="stats-value">${totalDistance.toFixed(2)} km</span>
            </div>
        </div>
    `;
    
    html += '<div class="coordinate-list">';
    
    coordinates.forEach((coord, index) => {
        const [lng, lat] = coord;
        const description = descriptions[index] || `位置 ${index + 1}`;
        const isStart = index === 0;
        const isEnd = index === coordinates.length - 1;
        
        let typeLabel = '';
        if (isStart) {
            typeLabel = i18n.t('map.start_point');
        } else if (isEnd) {
            typeLabel = i18n.t('map.end_point');
        } else {
            typeLabel = i18n.t('map.via_point');
        }
        
        html += `
            <div class="coordinate-item ${isStart ? 'start' : ''} ${isEnd ? 'end' : ''}">
                <div class="coordinate-header">
                    <span class="coordinate-number">${index + 1}</span>
                    <span class="coordinate-type">${typeLabel}</span>
                </div>
                <div class="coordinate-description">${description}</div>
                <div class="coordinate-position">
                    <span class="coordinate-label">${i18n.currentLang === 'zh-CN' ? '坐标' : 'Coordinates'}:</span>
                    <span class="coordinate-value">[${lat.toFixed(4)}, ${lng.toFixed(4)}]</span>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    statsContainer.innerHTML = html;
}