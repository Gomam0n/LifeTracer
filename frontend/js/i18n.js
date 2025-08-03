// LifeTracer 国际化模块
// 支持中英文切换功能

class I18n {
    constructor() {
        this.currentLang = 'zh-CN'; // 默认中文
        this.translations = {};
        this.supportedLangs = ['zh-CN', 'en-US'];
        
        // 从本地存储获取用户语言偏好
        this.loadLanguagePreference();
    }

    /**
     * 加载语言偏好
     */
    loadLanguagePreference() {
        const savedLang = localStorage.getItem('lifetracer-lang');
        if (savedLang && this.supportedLangs.includes(savedLang)) {
            this.currentLang = savedLang;
        } else {
            // 检测浏览器语言
            const browserLang = navigator.language || navigator.userLanguage;
            if (browserLang.startsWith('en')) {
                console.log("deafult lang is english")
                this.currentLang = 'en-US';
            }
        }
    }

    /**
     * 保存语言偏好
     */
    saveLanguagePreference() {
        localStorage.setItem('lifetracer-lang', this.currentLang);
    }

    /**
     * 加载语言包
     * @param {string} lang - 语言代码
     */
    async loadLanguage(lang) {
        if (!this.supportedLangs.includes(lang)) {
            console.warn(`不支持的语言: ${lang}`);
            return false;
        }

        try {
            // 动态加载语言包
            const response = await fetch(`lang/${lang}.js`);
            const text = await response.text();
            
            // 执行语言包脚本
            const script = document.createElement('script');
            script.textContent = text;
            document.head.appendChild(script);
            
            // 获取语言包数据
            if (window.LANG_DATA) {
                this.translations[lang] = window.LANG_DATA;
                delete window.LANG_DATA; // 清理全局变量
                document.head.removeChild(script);
                return true;
            }
        } catch (error) {
            console.error(`加载语言包失败: ${lang}`, error);
        }
        
        return false;
    }

    /**
     * 切换语言
     * @param {string} lang - 目标语言
     */
    async switchLanguage(lang) {
        if (lang === this.currentLang) return;

        // 加载语言包
        const loaded = await this.loadLanguage(lang);
        if (!loaded) return;

        this.currentLang = lang;
        this.saveLanguagePreference();
        
        // 更新页面文本
        this.updatePageTexts();
        
        // 触发语言切换事件
        this.dispatchLanguageChangeEvent();
    }

    /**
     * 获取翻译文本
     * @param {string} key - 翻译键
     * @param {Object} params - 参数对象
     */
    t(key, params = {}) {
        const langData = this.translations[this.currentLang];
        if (!langData) {
            console.warn(`语言包未加载: ${this.currentLang}`);
            return key;
        }

        let text = this.getNestedValue(langData, key);
        if (!text) {
            console.warn(`翻译键不存在: ${key}`);
            return key;
        }

        // 替换参数
        Object.keys(params).forEach(param => {
            text = text.replace(new RegExp(`\\{${param}\\}`, 'g'), params[param]);
        });

        return text;
    }

    /**
     * 获取嵌套对象的值
     * @param {Object} obj - 对象
     * @param {string} path - 路径，如 'common.loading'
     */
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : null;
        }, obj);
    }

    /**
     * 更新页面所有文本
     */
    updatePageTexts() {
        // 更新带有 data-i18n 属性的元素
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const text = this.t(key);
            
            if (element.tagName === 'INPUT' && element.type === 'text') {
                element.placeholder = text;
            } else {
                element.textContent = text;
            }
        });

        // 更新页面标题
        const titleKey = document.documentElement.getAttribute('data-i18n-title');
        if (titleKey) {
            document.title = this.t(titleKey);
        }

        // 更新HTML lang属性
        document.documentElement.lang = this.currentLang;
    }

    /**
     * 触发语言切换事件
     */
    dispatchLanguageChangeEvent() {
        const event = new CustomEvent('languageChanged', {
            detail: { 
                language: this.currentLang,
                translations: this.translations[this.currentLang]
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * 初始化国际化
     */
    async init() {
        // 加载当前语言包
        await this.loadLanguage(this.currentLang);
        
        // 更新页面文本
        this.updatePageTexts();
        
        // 创建语言切换按钮
        this.createLanguageSwitcher();
        
        console.log(`国际化初始化完成，当前语言: ${this.currentLang}`);
    }

    /**
     * 创建语言切换按钮
     */
    createLanguageSwitcher() {
        const container = document.querySelector('.container');
        if (!container) return;

        const switcher = document.createElement('div');
        switcher.className = 'language-switcher';
        switcher.innerHTML = `
            <button class="lang-btn ${this.currentLang === 'zh-CN' ? 'active' : ''}" 
                    onclick="i18n.switchLanguage('zh-CN')">中文</button>
            <button class="lang-btn ${this.currentLang === 'en-US' ? 'active' : ''}" 
                    onclick="i18n.switchLanguage('en-US')">English</button>
        `;

        // 插入到标题后面
        const title = container.querySelector('h1');
        if (title && title.nextSibling) {
            container.insertBefore(switcher, title.nextSibling);
        } else {
            container.insertBefore(switcher, container.firstChild.nextSibling);
        }
    }

    /**
     * 更新语言切换按钮状态
     */
    updateLanguageSwitcher() {
        const buttons = document.querySelectorAll('.lang-btn');
        buttons.forEach(btn => {
            btn.classList.remove('active');
            if ((btn.textContent === '中文' && this.currentLang === 'zh-CN') ||
                (btn.textContent === 'English' && this.currentLang === 'en-US')) {
                btn.classList.add('active');
            }
        });
    }

    /**
     * 获取当前语言
     */
    getCurrentLanguage() {
        return this.currentLang;
    }

    /**
     * 检查是否为中文
     */
    isChinese() {
        return this.currentLang === 'zh-CN';
    }

    /**
     * 检查是否为英文
     */
    isEnglish() {
        return this.currentLang === 'en-US';
    }
}

// 创建全局实例
const i18n = new I18n();

// 监听语言切换事件
document.addEventListener('languageChanged', (event) => {
    console.log('语言已切换到:', event.detail.language);
    
    // 更新语言切换按钮状态
    i18n.updateLanguageSwitcher();
    
    // 通知其他模块语言已切换
    if (typeof window.onLanguageChanged === 'function') {
        window.onLanguageChanged(event.detail);
    }
});