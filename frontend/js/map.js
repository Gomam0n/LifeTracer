// LifeTracer 地图轨迹可视化模块
// 使用 Leaflet.js 显示历史名人的移动轨迹

class LifeTracerMap {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.markers = [];
        this.polyline = null;
        this.currentData = null;
    }

    /**
     * 初始化地图
     */
    initMap() {
        // 创建地图容器
        const mapContainer = document.getElementById(this.containerId);
        if (!mapContainer) {
            console.error(`地图容器 ${this.containerId} 不存在`);
            return false;
        }

        // 初始化地图，默认中心为中国
        this.map = L.map(this.containerId).setView([35.0, 105.0], 5);
        
        // 确保地图容器尺寸正确
        setTimeout(() => {
            this.map.invalidateSize();
        }, 100);


        // 添加地图图层 - 使用多个备用瓦片服务
        this.addTileLayer();

        return true;
    }

    /**
     * 添加地图瓦片图层，提供多个备用选项
     */
    addTileLayer() {
        // 瓦片服务选项列表（按优先级排序）
        const tileOptions = [
            {
                name: 'GaoDe',
                url: "https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
                attribution: "© 高德地图",
                maxZoom: 18
            },
            {
                name: 'OpenStreetMap',
                url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            },
            {
                name: 'CartoDB Positron',
                url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                attribution: '© OpenStreetMap contributors © CARTO',
                maxZoom: 19
            },
            {
                name: 'OpenStreetMap DE',
                url: 'https://{s}.tile.openstreetmap.de/tiles/osmde/{z}/{x}/{y}.png',
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            },
            {
                name: 'Stamen Terrain',
                url: 'https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}{r}.png',
                attribution: 'Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors',
                maxZoom: 18
            }
        ];

        // 尝试加载第一个可用的瓦片服务
        this.loadTileLayer(tileOptions, 0);
    }

    /**
     * 递归尝试加载瓦片图层
     * @param {Array} tileOptions - 瓦片服务选项数组
     * @param {number} index - 当前尝试的索引
     */
    loadTileLayer(tileOptions, index) {
        if (index >= tileOptions.length) {
            console.error('所有瓦片服务都无法加载，使用默认配置');
            // 使用最基本的配置作为最后备选
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            }).addTo(this.map);
            return;
        }

        const option = tileOptions[index];
        console.log(`尝试加载地图图层: ${option.name}`);

        const layer = L.tileLayer(option.url, {
            attribution: option.attribution,
            maxZoom: option.maxZoom,
            errorTileUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        });

        // 监听瓦片加载事件
        let tilesLoaded = 0;
        let tilesErrored = 0;
        let checkTimeout;

        layer.on('tileload', () => {
            tilesLoaded++;
            if (tilesLoaded >= 3) { // 如果成功加载了3个瓦片，认为服务可用
                clearTimeout(checkTimeout);
                console.log(`地图图层加载成功: ${option.name}`);
            }
        });

        layer.on('tileerror', () => {
            tilesErrored++;
            if (tilesErrored >= 3) { // 如果连续3个瓦片加载失败，尝试下一个服务
                clearTimeout(checkTimeout);
                console.warn(`地图图层加载失败: ${option.name}，尝试下一个服务`);
                this.map.removeLayer(layer);
                this.loadTileLayer(tileOptions, index + 1);
            }
        });

        // 设置超时检查
        checkTimeout = setTimeout(() => {
            if (tilesLoaded < 3) {
                console.warn(`地图图层加载超时: ${option.name}，尝试下一个服务`);
                this.map.removeLayer(layer);
                this.loadTileLayer(tileOptions, index + 1);
            }
        }, 20000); // 5秒超时

        layer.addTo(this.map);
    }

    /**
     * 清除地图上的所有标记和轨迹线
     */
    clearMap() {
        // 清除所有标记
        this.markers.forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.markers = [];

        // 清除轨迹线
        if (this.polyline) {
            this.map.removeLayer(this.polyline);
            this.polyline = null;
        }
    }

    /**
     * 强制刷新地图尺寸
     */
    refreshMapSize() {
        if (this.map) {
            // 多次调用invalidateSize确保地图正确渲染
            this.map.invalidateSize();
            setTimeout(() => {
                this.map.invalidateSize();
            }, 100);
            setTimeout(() => {
                this.map.invalidateSize();
            }, 300);
        }
    }

    /**
     * 显示人物轨迹
     * @param {Object} biographyData - 包含coordinates和descriptions的数据
     */
    displayTrajectory(biographyData) {
        if (!this.map) {
            console.error('地图未初始化');
            return;
        }

        if (!biographyData || !biographyData.coordinates || !biographyData.descriptions) {
            console.error('无效的轨迹数据');
            return;
        }

        // 刷新地图尺寸
        this.refreshMapSize();
        
        this.currentData = biographyData;
        this.clearMap();
        const coordinates = biographyData.coordinates;
        const descriptions = biographyData.descriptions;


        // 创建标记点
        coordinates.forEach((coord, index) => {
            const [lng, lat] = coord;
            const description = descriptions[index] || `位置 ${index + 1}`;

            // 创建自定义图标
            const icon = this.createCustomIcon(index + 1, index === 0, index === coordinates.length - 1);

            // 创建标记
            const marker = L.marker([lat, lng], { icon: icon })
                .addTo(this.map)
                .bindPopup(this.createPopupContent(index + 1, description, coord));

            this.markers.push(marker);
        });
        

        // 创建轨迹线
        const latLngs = coordinates.map(coord => [coord[1], coord[0]]); // 注意：Leaflet使用[lat, lng]格式
        this.polyline = L.polyline(latLngs, {
            color: '#e74c3c',
            weight: 3,
            opacity: 0.8,
            dashArray: '10, 5'
        }).addTo(this.map);
        
        // 调整地图视野以包含所有点
        const group = new L.featureGroup(this.markers);
        this.map.fitBounds(group.getBounds().pad(0.1));

        // 添加轨迹动画效果
        this.animateTrajectory();
    }

    /**
     * 创建自定义图标
     * @param {number} number - 序号
     * @param {boolean} isStart - 是否为起点
     * @param {boolean} isEnd - 是否为终点
     */
    createCustomIcon(number, isStart, isEnd) {
        let color = '#3498db'; // 默认蓝色
        if (isStart) color = '#27ae60'; // 起点绿色
        if (isEnd) color = '#e74c3c'; // 终点红色

        return L.divIcon({
            className: 'custom-marker',
            html: `
                <div style="
                    background-color: ${color};
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    border: 3px solid white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                ">${number}</div>
            `,
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
    }

    /**
     * 创建弹出窗口内容
     * @param {number} index - 序号
     * @param {string} description - 描述
     * @param {Array} coord - 坐标
     */
    createPopupContent(index, description, coord) {
        const stationText = i18n ? i18n.t('map.popup.location') : `第 ${index} 站`;
        const coordinatesText = i18n ? i18n.t('map.popup.coordinates') : '坐标';
        
        return `
            <div style="min-width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50;">${stationText.replace('{location}', `第 ${index} 站`)}</h4>
                <p style="margin: 5px 0; font-size: 14px;">${description}</p>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; font-size: 12px; color: #7f8c8d;">
                    <strong>${coordinatesText}:</strong> ${coord[1].toFixed(4)}, ${coord[0].toFixed(4)}
                </div>
            </div>
        `;
    }

    /**
     * 轨迹动画效果
     */
    animateTrajectory() {
        if (!this.markers.length) return;

        // 依次显示标记点，模拟轨迹动画
        this.markers.forEach((marker, index) => {
            setTimeout(() => {
                marker.openPopup();
                setTimeout(() => {
                    marker.closePopup();
                }, 1500);
            }, index * 800);
        });
    }


    /**
     * 销毁地图实例
     */
    destroy() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
        this.markers = [];
        this.polyline = null;
        this.currentData = null;
    }
}

// 全局地图实例
let lifeTracerMap = null;

/**
 * 初始化地图模块
 * @param {string} containerId - 地图容器ID
 */
function initLifeTracerMap(containerId = 'map') {
    lifeTracerMap = new LifeTracerMap(containerId);
    return lifeTracerMap.initMap();
}

/**
 * 显示轨迹数据
 * @param {Object} biographyData - 轨迹数据
 */
function showTrajectoryOnMap(biographyData) {
    if (!lifeTracerMap) {
        console.error('地图未初始化，请先调用 initLifeTracerMap()');
        return;
    }
    
    lifeTracerMap.displayTrajectory(biographyData);
    
}
