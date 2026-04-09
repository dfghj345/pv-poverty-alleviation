import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

// 引入 Tailwind CSS 及全局自定义样式
// 确保你在 src/assets/styles/main.css 中写入了 @tailwind 指令
import './style.css';

const app = createApp(App);
const pinia = createPinia();

// 按顺序挂载核心插件
app.use(pinia);
app.use(router);

// 挂载到 index.html 的 #app 节点
app.mount('#app');