// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#10B981', // 绿色主色调
        secondary: '#06B6D4', // 辅助色
        neutral: '#F3F4F6', // 中性色
        dark: {
          bg: '#1F2937',
          card: '#374151',
          text: '#F9FAFB'
        }
      },
      fontFamily: {
        inter: ['Inter', 'sans-serif'],
      },
    }
  },
  plugins: [],
}