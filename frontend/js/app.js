// LifeTracer 前端应用主要逻辑
// 自动获取当前主机地址，支持前后端一体化部署
const API_BASE_URL = window.location.origin;

/**
 * 获取人物生平轨迹数据
 */
async function getBiography() {
    const personName = document.getElementById('personName').value.trim();
    
    if (!personName) {
        showError('请输入人物姓名');
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
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayBiographyData(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError('获取数据失败，请检查网络连接或稍后重试');
    } finally {
        showLoading(false);
    }
}

/**
 * 显示生平轨迹数据
 * @param {Object} data - API返回的数据
 */
function displayBiographyData(data) {
    const biographyDataDiv = document.getElementById('biographyData');
    
    if (data.success && data.data) {
        const biography = data.data;
        let html = `<div class="success">成功获取 ${biography.name} 的生平轨迹数据</div>`;
        
        if (biography.coordinates && biography.descriptions) {
            html += '<h4>轨迹点详情：</h4>';
            
            for (let i = 0; i < biography.coordinates.length; i++) {
                const coord = biography.coordinates[i];
                const desc = biography.descriptions[i];
                
                html += `
                    <div class="coordinate-item">
                        <div class="coordinate">坐标 ${i + 1}: [${coord[0]}, ${coord[1]}]</div>
                        <div class="description">${desc}</div>
                    </div>
                `;
            }
        } else {
            html += '<p>暂无轨迹数据</p>';
        }
        
        biographyDataDiv.innerHTML = html;
        showResult();
        
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
        showError(data.message || '获取数据失败');
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
    errorDiv.textContent = message;
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
 * 初始化事件监听器
 */
function initEventListeners() {
    // 支持回车键提交
    document.getElementById('personName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            getBiography();
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