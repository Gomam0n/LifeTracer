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
    
    // 显示加载状态
    showLoading(true);
    hideError();
    hideResult();
    
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
        showLoading(false);
    }
}

/**
 * 显示生平轨迹数据
 * @param {Object} data - API返回的数据
 */
function displayLifeTrajectoryData(data) {
    const coordinatesDiv = document.getElementById('coordinates');
    
    if (data.success && data.data) {
        const biography = data.data;
        let html = `<div class="success">${i18n.t('status.success')}</div>`;
        
        if (biography.coordinates && biography.descriptions) {
            html += `<h4>${i18n.t('result.title')}：</h4>`;
            
            for (let i = 0; i < biography.coordinates.length; i++) {
                const coord = biography.coordinates[i];
                const desc = biography.descriptions[i];
                
                html += `
                    <div class="coordinate-item">
                        <div class="coordinate">${i18n.t('result.coordinate')} ${i + 1}: [${coord[0]}, ${coord[1]}]</div>
                        <div class="description">${desc}</div>
                    </div>
                `;
            }
        } else {
            html += `<p>${i18n.t('result.noData')}</p>`;
        }
        
        coordinatesDiv.innerHTML = html;
        showResult();
        
        // 显示地图区域
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
 * 显示/隐藏加载状态
 * @param {boolean} show - 是否显示加载状态
 */
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
    document.querySelector('button').disabled = show;
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