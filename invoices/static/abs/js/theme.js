// ABS Theme Handler
const currentTheme = localStorage.getItem('abs-theme') || 'light';
document.documentElement.setAttribute('data-theme', currentTheme);
