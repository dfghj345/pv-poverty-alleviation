import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Dashboard',
    // 主看板通常需要极速呈现，可以直接引入或保留懒加载
    component: () => import('@/views/Dashboard.vue'),
    meta: {
      title: '光伏扶贫大数据看板 - 全局视图'
    }
  },
  {
    path: '/report',
    name: 'Report',
    // 详情报告页，懒加载分离打包
    component: () => import('@/views/Report/index.vue'),
    meta: {
      title: '投资收益评估报告'
    }
  },
  {
    // 捕获所有未匹配的路由，重定向到首页
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  // 切换路由时自动滚动到顶部
  scrollBehavior() {
    return { top: 0 };
  }
});

// 全局路由守卫：动态修改页面标题
router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = to.meta.title as string;
  }
  next();
});

export default router;