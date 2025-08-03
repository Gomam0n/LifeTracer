// 中文语言包
window.LANG_DATA = {
    // 页面标题和主要内容
    page: {
        title: "LifeTracer - 人物生平轨迹追踪器",
        heading: "LifeTracer - 人物生平轨迹追踪器",
        description: "输入人物姓名，获取其生平重要地点的地理坐标信息"
    },

    // 输入区域
    input: {
        label: "请输入人物姓名：",
        placeholder: "例如：李白、鲁迅、爱因斯坦等",
        button: "获取生平轨迹"
    },

    // 状态提示
    status: {
        loading: "正在查询人物生平轨迹，请稍候...",
        success: "查询成功！",
        error: "查询失败，请重试"
    },

    // 错误信息
    error: {
        network: "网络连接失败，请检查网络设置",
        server: "服务器错误，请稍后重试",
        notFound: "未找到该人物的生平信息",
        invalidInput: "请输入有效的人物姓名",
        timeout: "请求超时，请重试",
        unknown: "未知错误，请联系管理员"
    },

    // 结果展示
    result: {
        title: "生平轨迹结果",
        noData: "暂无数据",
        coordinate: "坐标",
        description: "描述",
        location: "地点",
        time: "时间",
        event: "事件"
    },

    // 地图相关
    map: {
        title: "生平轨迹地图",
        loading: "地图加载中...",
        error: "地图加载失败",
        noData: "暂无轨迹数据",
        stats: {
            title: "轨迹统计",
            totalLocations: "总地点数：{count} 个",
            totalDistance: "总距离：约 {distance} 公里",
            timeSpan: "时间跨度：{span}",
            regions: "涉及区域：{regions}"
        },
        popup: {
            location: "地点：{location}",
            time: "时间：{time}",
            event: "事件：{event}",
            coordinates: "坐标：{lat}, {lng}"
        },
        controls: {
            zoomIn: "放大",
            zoomOut: "缩小",
            reset: "重置视图",
            fullscreen: "全屏"
        }
    },

    // 通用文本
    common: {
        loading: "加载中...",
        retry: "重试",
        close: "关闭",
        confirm: "确认",
        cancel: "取消",
        save: "保存",
        delete: "删除",
        edit: "编辑",
        view: "查看",
        back: "返回",
        next: "下一步",
        previous: "上一步",
        submit: "提交",
        reset: "重置",
        clear: "清空",
        search: "搜索",
        filter: "筛选",
        sort: "排序",
        export: "导出",
        import: "导入",
        help: "帮助",
        about: "关于",
        settings: "设置"
    },

    // 时间格式
    time: {
        year: "年",
        month: "月",
        day: "日",
        hour: "时",
        minute: "分",
        second: "秒",
        ago: "前",
        later: "后",
        now: "现在",
        today: "今天",
        yesterday: "昨天",
        tomorrow: "明天"
    },

    // 单位
    units: {
        kilometer: "公里",
        meter: "米",
        mile: "英里",
        foot: "英尺",
        degree: "度",
        percent: "百分比"
    },

    // 提示信息
    tips: {
        inputHelp: "请输入您想要查询的历史人物姓名",
        mapHelp: "点击地图上的标记可查看详细信息",
        languageSwitch: "点击右上角可切换语言",
        mobileOptimized: "本应用已针对移动设备优化"
    }
};